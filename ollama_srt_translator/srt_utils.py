# -*- coding: utf-8 -*-
"""
SRT 解析、构建、窗口切分、Prompt 构造与译文解析。
"""
import hashlib
import re

from .config import MAIN_COUNT, CONTEXT_BEFORE, CONTEXT_AFTER


class SRTItem:
    def __init__(self, index, timeline, text):
        self.index = int(index)
        self.timeline = timeline
        self.text = text


def normalize_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_srt(text):
    text = normalize_newlines(text)
    blocks = re.split(r"\n\s*\n", text.strip())
    items = []
    for block in blocks:
        lines = block.split("\n")
        if len(lines) < 2:
            continue
        index = None
        timeline = None
        timeline_pos = None
        if lines[0].strip().isdigit():
            index = int(lines[0].strip())
            start = 1
        else:
            start = 0
        for i in range(start, len(lines)):
            line = lines[i].strip()
            if "-->" in line:
                timeline = line
                timeline_pos = i
                break
        if timeline is None:
            continue
        if index is None:
            index = len(items) + 1
        text_start = timeline_pos + 1
        subtitle_text = "\n".join(lines[text_start:]).strip()
        items.append(SRTItem(index, timeline, subtitle_text))
    return items


def build_srt(items):
    blocks = []
    for item in items:
        blocks.append(
            "\n".join([
                str(item.index),
                item.timeline,
                item.text.strip()
            ])
        )
    return "\n\n".join(blocks)


def item_hash(item):
    raw = f"{item.index}\n{item.timeline}\n{item.text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def source_hash(items):
    raw_parts = [
        f"{item.index}\n{item.timeline}\n{item.text}"
        for item in items
    ]
    raw = "\n\n".join(raw_parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_windows(items, main_count=MAIN_COUNT, ctx_before=CONTEXT_BEFORE, ctx_after=CONTEXT_AFTER):
    n = len(items)
    windows = []
    part = 1
    i = 0
    while i < n:
        end = min(i + main_count, n)
        main_items = items[i:end]
        before_start = max(0, i - ctx_before)
        context_before = items[before_start:i]
        after_end = min(n, end + ctx_after)
        context_after = items[end:after_end]
        windows.append({
            "part": part,
            "main_items": main_items,
            "context_before": context_before,
            "context_after": context_after,
            "start_idx": i,
            "end_idx": end,
        })
        part += 1
        i = end
    return windows


def chunk_hash(main_items):
    raw = "\n\n".join(
        f"{item.index}\n{item.timeline}\n{item.text}"
        for item in main_items
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def format_items_for_prompt(items, label=""):
    lines = []
    for item in items:
        lines.append(f"[{item.index}] {item.text.strip()}")
    if label and lines:
        return f"{label}\n" + "\n".join(lines)
    return "\n".join(lines)


def build_translation_prompt(window, previous_translation=""):
    main_items = window["main_items"]
    ctx_before = window["context_before"]
    ctx_after = window["context_after"]
    if previous_translation:
        prev_ctx = previous_translation[-1500:]
    else:
        prev_ctx = "（第一批字幕，没有上一批译文。）"
    prompt = f"""【上一批译文末尾，仅供语气参考】
{prev_ctx}
--------------------------------------------------
【前上下文（仅供理解剧情，禁止翻译、禁止输出）】
{format_items_for_prompt(ctx_before) if ctx_before else "（无）"}
--------------------------------------------------
【后上下文（仅供理解剧情，禁止翻译、禁止输出）】
{format_items_for_prompt(ctx_after) if ctx_after else "（无）"}
--------------------------------------------------
【本次必须翻译的主字幕（共 {len(main_items)} 条）】
{format_items_for_prompt(main_items)}
--------------------------------------------------
【输出规则（必须严格遵守）】
1. 只翻译「本次必须翻译的主字幕」。
2. 每个主字幕编号必须出现且只出现一次，格式：
   [编号] 翻译结果
3. 绝对禁止输出任何前上下文或后上下文的编号与内容。
4. 不得遗漏、不得增加、不得重复任何主字幕编号。
5. 不要解释、不要标题、不要额外文字。
6. 直接输出翻译结果。
"""
    return prompt


def clean_model_output(text):
    text = text.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]).strip()
    prefixes = [
        "翻译如下：", "翻译如下:", "译文：", "译文:",
        "中文翻译：", "中文翻译:", "Translation:", "translation:"
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].lstrip()
    return text.strip()


def parse_translation_output(output, main_items):
    output = clean_model_output(output)
    if not output:
        raise RuntimeError("模型返回为空。")
    expected_ids = [item.index for item in main_items]
    expected_set = set(expected_ids)
    header_pattern = re.compile(r"(?m)^\s*\[(\d+)\]\s*")
    headers = list(header_pattern.finditer(output))
    if not headers:
        raise RuntimeError("模型没有返回任何 [编号]。")
    found_ids = [int(m.group(1)) for m in headers]
    duplicates = []
    seen = set()
    for number in found_ids:
        if number in seen:
            duplicates.append(number)
        seen.add(number)
    if duplicates:
        raise RuntimeError(
            "模型重复返回字幕编号：" + ", ".join(map(str, sorted(set(duplicates))))
        )
    if len(found_ids) != len(expected_ids):
        raise RuntimeError(
            f"模型返回字幕数量错误：预期 {len(expected_ids)} 条，实际 {len(found_ids)} 条。"
        )
    found_set = set(found_ids)
    missing = expected_set - found_set
    if missing:
        raise RuntimeError(
            "模型遗漏字幕：" + ", ".join(map(str, sorted(missing)))
        )
    extra = found_set - expected_set
    if extra:
        raise RuntimeError(
            "模型产生了额外字幕（可能混入了上下文）："
            + ", ".join(map(str, sorted(extra)))
        )
    result_map = {}
    for pos, match in enumerate(headers):
        number = int(match.group(1))
        start = match.end()
        end = headers[pos + 1].start() if pos + 1 < len(headers) else len(output)
        translated_text = output[start:end].strip()
        if not translated_text:
            raise RuntimeError(f"字幕 [{number}] 翻译结果为空。")
        result_map[number] = translated_text
    if set(result_map.keys()) != expected_set:
        raise RuntimeError("模型返回编号与当前主批次不一致。")
    translated_items = []
    for item in main_items:
        translated_items.append(
            SRTItem(item.index, item.timeline, result_map[item.index])
        )
    return translated_items
