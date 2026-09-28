# -*- coding: utf-8 -*-
"""
默认配置、全局运行时配置、路径与 GUI 配置读写。
"""
import json
from datetime import datetime
from pathlib import Path

# 程序版本号（展示在侧栏左下角）
APP_VERSION = "1.0.5"

# ============================================================
# 默认配置（可被 GUI 覆盖）
# ============================================================
DEFAULT_CONFIG = {
    "ollama": {
        "url": "http://localhost:11434/api/generate",
        "model": "",
        "timeout_seconds": 3600,
        "keep_alive": "120m"
    },
    "translation": {
        "main_count": 20,
        "context_before": 5,
        "context_after": 5,
        "max_retries": 3,
        "retry_wait_seconds": 5
    },
    "files": {
        "input_dir": "input",
        "output_dir": "output",
        "cache_dir": "cache",
        "input_file": "",
        "output_file": "translated.srt"
    }
}

# ============================================================
# 全局运行时配置（GUI 启动后填充）
# ============================================================
CONFIG = DEFAULT_CONFIG.copy()
OLLAMA = CONFIG["ollama"]
TRANS = CONFIG["translation"]
FILES = CONFIG["files"]

# 以本包所在目录的上一级（项目根）为 BASE_DIR，与原脚本「脚本所在目录」行为一致
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / FILES["input_dir"]
OUTPUT_DIR = BASE_DIR / FILES["output_dir"]
CACHE_DIR = BASE_DIR / FILES["cache_dir"]

INPUT_FILE = None
OUTPUT_FILE = None

MANIFEST_FILE = CACHE_DIR / "manifest.json"
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE = CACHE_DIR / "run.log"

MAIN_COUNT = int(TRANS.get("main_count", 20))
CONTEXT_BEFORE = int(TRANS.get("context_before", 5))
CONTEXT_AFTER = int(TRANS.get("context_after", 5))
MAX_RETRIES = int(TRANS.get("max_retries", 3))
RETRY_WAIT = int(TRANS.get("retry_wait_seconds", 5))


def ensure_dirs():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_gui_config() -> dict:
    """读取上次保存的 GUI 配置，失败则返回空字典"""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_gui_config(data: dict):
    """保存 GUI 配置到 config.json"""
    try:
        CONFIG_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


def write_log_file(msg: str, level: str = "info"):
    """把日志同步写入 cache/run.log（纯文本）"""
    try:
        ensure_dirs()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level.upper()}] {msg}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # 写日志失败不影响主程序
