# -*- coding: utf-8 -*-
"""
翻译工作线程：分批调用模型、缓存、进度与停止控制。
"""
import time
import traceback
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from . import config as cfg
from .config import ensure_dirs, CACHE_DIR
from .srt_utils import (
    parse_srt, normalize_newlines, make_windows,
    build_translation_prompt, parse_translation_output, build_srt,format_items_for_prompt,
)
from .ollama_client import call_ollama
from .cache_manager import (
    load_cache, save_cache, save_manifest, write_final_result,make_auto_output_path,
)


class TranslateWorker(QThread):
    log_signal = pyqtSignal(str, str)          # text, level
    progress_signal = pyqtSignal(int, int)     # current, total
    finished_signal = pyqtSignal(bool, str)    # success, message
    status_signal = pyqtSignal(str)

    def __init__(self, srt_path: Path, output_path: Path, model_name: str,
                 ollama_url: str, main_count: int, ctx_before: int, ctx_after: int,
                 max_retries: int, retry_wait: int, keep_alive: str,
                 timeout_seconds: int,
                 clear_cache: bool, parent=None):
        super().__init__(parent)
        self.srt_path = srt_path
        # 输出目录；None 则用项目 output/。文件名在合并时自动生成。
        self.output_dir = Path(output_path) if output_path else None
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.main_count = main_count
        self.ctx_before = ctx_before
        self.ctx_after = ctx_after
        self.max_retries = max_retries
        self.retry_wait = retry_wait
        self.keep_alive = keep_alive
        self.timeout_seconds = timeout_seconds
        self.clear_cache_flag = clear_cache
        self._stop = False

    def stop(self):
        self._stop = True

    def log(self, msg, level="info"):
        self.log_signal.emit(str(msg), level)

    def run(self):
        try:
            ensure_dirs()
            cfg.INPUT_FILE = self.srt_path
             # 完整文件路径在全部批次完成后确定
            cfg.OUTPUT_FILE = None
            cfg.OLLAMA["model"] = self.model_name
            cfg.OLLAMA["url"] = self.ollama_url
            cfg.OLLAMA["keep_alive"] = self.keep_alive
            cfg.OLLAMA["timeout_seconds"] = self.timeout_seconds
            cfg.MAIN_COUNT = self.main_count
            cfg.CONTEXT_BEFORE = self.ctx_before
            cfg.CONTEXT_AFTER = self.ctx_after
            cfg.MAX_RETRIES = self.max_retries
            cfg.RETRY_WAIT = self.retry_wait

            self.log("=" * 50, "system")
            self.log("Ollama SRT 自动翻译工具 (GUI)", "system")
            self.log(f"模型：{self.model_name}", "info")
            self.log(f"接口：{self.ollama_url}", "info")
            self.log(f"输入：{cfg.INPUT_FILE}", "info")

            if self.output_dir:
                self.log(f"输出目录：{self.output_dir}（文件名结束时自动生成）", "info")
            else:
                self.log("输出目录：项目 output/（文件名：模型_原文件名_日期_zh.srt）", "info")
            self.log(
                f"主翻译条数：{cfg.MAIN_COUNT} | 前上下文：{cfg.CONTEXT_BEFORE} | 后上下文：{cfg.CONTEXT_AFTER}",
                "info",
            )
            self.log(
                f"重试：{cfg.MAX_RETRIES} 次 | 重试等待：{cfg.RETRY_WAIT}s | Keep Alive：{self.keep_alive} | 超时：{self.timeout_seconds}s",
                "info",
            )
            self.log("=" * 50, "system")

            if not cfg.INPUT_FILE.exists():
                raise RuntimeError(f"找不到 SRT 文件：{cfg.INPUT_FILE}")
            source = cfg.INPUT_FILE.read_text(encoding="utf-8-sig")
            source = normalize_newlines(source).strip()
            if not source:
                raise RuntimeError("SRT 是空文件。")
            items = parse_srt(source)
            if not items:
                raise RuntimeError("没有解析到字幕。")
            self.log(f"字幕数量：{len(items):,}", "info")
            self.log(f"原文字符数：{len(source):,}", "info")

            windows = make_windows(
                items, cfg.MAIN_COUNT, cfg.CONTEXT_BEFORE, cfg.CONTEXT_AFTER
            )
            total_parts = len(windows)
            self.log(f"预计分成：{total_parts} 批", "info")

            # 处理缓存
            if self.clear_cache_flag:
                files = list(CACHE_DIR.glob("part_*.json"))
                for p in files:
                    try:
                        p.unlink()
                    except Exception:
                        pass
                self.log(f"已清空 {len(files)} 个历史缓存。", "warning")
            else:
                files = list(CACHE_DIR.glob("part_*.json"))
                if files:
                    self.log(f"发现 {len(files)} 个历史缓存，将自动验证使用。", "info")

            save_manifest(items, windows)

            translated_all = []
            start_time = time.time()

            for window in windows:
                if self._stop:
                    self.log("用户请求停止，已保存已完成批次。", "warning")
                    self.finished_signal.emit(False, "用户中断")
                    return

                part_index = window["part"]
                main_items = window["main_items"]
                self.status_signal.emit(f"批次 {part_index}/{total_parts}")
                self.progress_signal.emit(part_index - 1, total_parts)

                self.log("-" * 40, "info")
                self.log(
                    f"[{part_index:05d}/{total_parts:05d}] 主字幕：{main_items[0].index} - {main_items[-1].index}",
                    "info",
                )
                self.log(
                    f"本批主翻译：{len(main_items)} 条 | 前上下文：{len(window['context_before'])} | 后上下文：{len(window['context_after'])}",
                    "info",
                )

                # 尝试缓存
                cached = load_cache(part_index, main_items, self.log)
                if cached:
                    self.log("状态：使用已验证缓存。", "success")
                    translated_all.extend(cached)
                    self.progress_signal.emit(part_index, total_parts)
                    continue

                previous_translation = ""
                if translated_all:
                    previous_translation = format_items_for_prompt(translated_all[-15:])
                prompt = build_translation_prompt(window, previous_translation)

                # 打印发给模型的完整 Prompt
                self.log("─" * 40, "prompt")
                self.log(f"【发给模型的 Prompt】（第 {part_index}/{total_parts} 批）", "prompt")
                self.log(prompt, "prompt")
                self.log("─" * 40, "prompt")
                self.log("模型开始生成 ↓", "stream")

                success = False
                for attempt in range(1, cfg.MAX_RETRIES + 1):
                    if self._stop:
                        self.finished_signal.emit(False, "用户中断")
                        return
                    try:
                        self.log(f"正在翻译... 第 {attempt}/{cfg.MAX_RETRIES} 次", "info")
                        output = call_ollama(prompt, self.log)
                        translated_chunk = parse_translation_output(output, main_items)
                        save_cache(part_index, main_items, translated_chunk)
                        translated_all.extend(translated_chunk)
                        self.log(f"完成：{len(translated_chunk)} 条", "success")
                        success = True
                        break
                    except Exception as e:
                        self.log(f"失败：{e}", "error")
                        if attempt < cfg.MAX_RETRIES:
                            wait = cfg.RETRY_WAIT * attempt
                            self.log(f"{wait} 秒后重试...", "warning")
                            time.sleep(wait)

                if not success:
                    self.log(f"第 {part_index} 批翻译失败。已完成批次已保存。", "error")
                    self.finished_signal.emit(False, f"第 {part_index} 批失败")
                    return

                self.progress_signal.emit(part_index, total_parts)

            # 最终检查
            if len(translated_all) != len(items):
                raise RuntimeError("最终字幕数量与原 SRT 不一致。")
            for original, translated in zip(items, translated_all):
                if original.index != translated.index:
                    raise RuntimeError("最终字幕编号发生错位。")
                if original.timeline != translated.timeline:
                    raise RuntimeError(f"字幕 [{original.index}] 时间轴发生变化。")

            # 合并写出：目录 + 自动文件名（模型_原文件_名日期_zh.srt）
            final_path = make_auto_output_path(
                self.srt_path, self.model_name, output_dir=self.output_dir
            )
            output_path = write_final_result(translated_all, final_path)
            elapsed = time.time() - start_time
            self.log("", "info")
            self.log("=" * 50, "success")
            self.log("翻译完成！", "success")
            self.log(f"输出文件：{output_path}", "success")
            self.log(
                f"字幕：{len(translated_all):,} 条 | 分块：{total_parts} | 耗时：{elapsed / 60:.1f} 分钟",
                "success",
            )
            self.log(f"缓存目录：{CACHE_DIR}", "info")
            self.log("=" * 50, "success")
            self.finished_signal.emit(True, str(output_path))

        except Exception as e:
            self.log(f"程序发生错误：\n{e}\n{traceback.format_exc()}", "error")
            self.finished_signal.emit(False, str(e))
