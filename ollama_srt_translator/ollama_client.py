# -*- coding: utf-8 -*-
"""
Ollama API：模型列表与流式生成。
"""
import json
import time
from urllib import request, error

from .config import OLLAMA
from .srt_utils import clean_model_output


def fetch_ollama_models(base_url="http://localhost:11434"):
    """返回模型名称列表"""
    tags_url = base_url.rstrip("/") + "/api/tags"
    try:
        with request.urlopen(tags_url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("models", [])
            names = []
            for m in models:
                name = m.get("name") or m.get("model")
                if name:
                    names.append(name)
            return sorted(names)
    except Exception as e:
        raise RuntimeError(f"无法获取 Ollama 模型列表：{e}")


def call_ollama(prompt, log_callback=None):
    payload = {
        "model": OLLAMA["model"],
        "prompt": prompt,
        "stream": True,
        "keep_alive": OLLAMA.get("keep_alive", "120m")
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        OLLAMA["url"],
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    timeout = int(OLLAMA.get("timeout_seconds", 3600))
    full_output = []
    last_display_time = time.time()
    stream_buffer = []
    try:
        with request.urlopen(req, timeout=timeout) as response:
            while True:
                line = response.readline()
                if not line:
                    break
                line = line.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                try:
                    data_json = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "error" in data_json:
                    raise RuntimeError(data_json["error"])
                piece = data_json.get("response", "")
                if piece:
                    full_output.append(piece)
                    stream_buffer.append(piece)
                    now = time.time()
                    # 每 0.35 秒或缓冲区较大时刷一次，既流畅又不卡 UI
                    if (now - last_display_time >= 0.35 or len(stream_buffer) > 30) and log_callback:
                        chunk = "".join(stream_buffer)
                        log_callback(chunk, "stream")
                        stream_buffer.clear()
                        last_display_time = now
                if data_json.get("done", False):
                    break
        # 刷干净最后剩余内容
        if stream_buffer and log_callback:
            log_callback("".join(stream_buffer), "stream")
    except error.URLError as e:
        raise RuntimeError(f"无法连接 Ollama：{e}")
    output = "".join(full_output)
    if not output.strip():
        raise RuntimeError("Ollama 返回空内容。")
    return clean_model_output(output)
