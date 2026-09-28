# -*- coding: utf-8 -*-
"""
分批缓存读写、manifest 与最终 SRT 写出。
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path

from .config import (
    CACHE_DIR, MANIFEST_FILE, INPUT_FILE, OUTPUT_FILE, OUTPUT_DIR,
    MAIN_COUNT, CONTEXT_BEFORE, CONTEXT_AFTER,
)
from .srt_utils import (
    SRTItem, item_hash, chunk_hash, source_hash, build_srt,
)


def cache_file(index):
    return CACHE_DIR / f"part_{index:05d}.json"


def save_cache(index, main_items, translated_items):
    data = {
        "version": 3,
        "part": index,
        "mode": "20+5+5",
        "chunk_hash": chunk_hash(main_items),
        "items": []
    }
    for original, translated in zip(main_items, translated_items):
        data["items"].append({
            "index": original.index,
            "timeline": original.timeline,
            "source": original.text,
            "source_hash": item_hash(original),
            "translation": translated.text
        })
    path = cache_file(index)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temp_path.replace(path)


def load_cache(index, main_items, log_callback=None):
    path = cache_file(index)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        if log_callback:
            log_callback(f"缓存损坏：{path.name} -> {e}", "warning")
        return None
    if data.get("version") not in (2, 3):
        if log_callback:
            log_callback(f"缓存版本不兼容：{path.name}", "warning")
        return None
    if data.get("part") != index:
        return None
    cached_items = data.get("items")
    if not isinstance(cached_items, list):
        return None
    if len(cached_items) != len(main_items):
        if log_callback:
            log_callback(f"缓存字幕数量变化：{path.name}", "warning")
        return None
    current_hash = chunk_hash(main_items)
    if data.get("chunk_hash") != current_hash:
        if log_callback:
            log_callback(f"缓存原文已经变化：{path.name}", "warning")
        return None
    translated_items = []
    for original, cached in zip(main_items, cached_items):
        if cached.get("index") != original.index:
            if log_callback:
                log_callback(f"缓存编号不一致：{path.name}", "warning")
            return None
        if cached.get("timeline") != original.timeline:
            if log_callback:
                log_callback(f"缓存时间轴发生变化：{path.name}", "warning")
            return None
        if cached.get("source") != original.text:
            if log_callback:
                log_callback(f"缓存原文发生变化：{path.name}", "warning")
            return None
        if cached.get("source_hash") != item_hash(original):
            if log_callback:
                log_callback(f"缓存字幕指纹不一致：{path.name}", "warning")
            return None
        translation = cached.get("translation")
        if not isinstance(translation, str) or not translation.strip():
            if log_callback:
                log_callback(f"缓存译文为空：{path.name}", "warning")
            return None
        translated_items.append(
            SRTItem(original.index, original.timeline, translation)
        )
    if log_callback:
        log_callback(f"缓存验证通过：{path.name}", "success")
    return translated_items


def save_manifest(items, windows):
    data = {
        "version": 3,
        "mode": "20+5+5",
        "source_file": str(INPUT_FILE.name) if INPUT_FILE else "",
        "source_hash": source_hash(items),
        "total_items": len(items),
        "total_parts": len(windows),
        "main_count": MAIN_COUNT,
        "context_before": CONTEXT_BEFORE,
        "context_after": CONTEXT_AFTER,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    MANIFEST_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def make_auto_output_path(srt_path, model_name: str, output_dir=None):
    """
    翻译结束合并时生成输出路径：
    {output_dir 或 项目 output/}/{模型名}_{原文件名}_{YYYYMMDD}_zh.srt
    模型名中的 : / \\ 等非法字符会替换为 _。
    """
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    safe_model = re.sub(r'[\\/:*?"<>|]+', "_", str(model_name)).strip("._") or "model"
    stem = Path(srt_path).stem
    filename = f"{safe_model}_{stem}_{date_str}_zh.srt"
    return out_dir / filename

def write_final_result(translated_items, output_path=None):
    """写出最终 SRT。若未指定 output_path，则使用全局 OUTPUT_FILE。"""
    from . import config as cfg

    path = output_path if output_path is not None else cfg.OUTPUT_FILE
    if path is None:
        raise RuntimeError("未指定输出文件路径。")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    result = build_srt(translated_items)
    path.write_text(result, encoding="utf-8")
    cfg.OUTPUT_FILE = path
    return path
