# /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama SRT 长篇自动翻译工具 - 入口

功能概览（逻辑与拆分前完全一致）：
1. 点击按钮选择本地 SRT 文件
2. 自动读取本机 Ollama 已安装模型
3. 下拉框选择 Ollama 模型（不再写死 config.json）
4. 支持手动刷新模型列表
5. 保留原有全部翻译逻辑（20+5+5 窗口、缓存、严格解析等）
6. 超时时间可配置
7. 实时流式输出到日志
8. 每次发给模型的完整 Prompt 会打印
9. 彩色分级日志（时间戳 + 图标）
"""
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from ollama_srt_translator.ui import MainWindow


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
