# -*- coding: utf-8 -*-
"""
主窗口 UI、样式与交互。

布局：左侧导航菜单（设置 / 日志），右侧对应页面。
日志页可独占右侧大面积，避免与设置抢垂直空间。
"""
import html
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QTextEdit,
    QProgressBar, QGroupBox, QMessageBox, QSpinBox,
    QLineEdit, QCheckBox, QSizePolicy, QStackedWidget,
    QFrame, QScrollArea,
)

from .config import (
    ensure_dirs, load_gui_config, save_gui_config, write_log_file, LOG_FILE,OUTPUT_DIR,
)
from .ollama_client import fetch_ollama_models
from .worker import TranslateWorker


# ============================================================
# 全局样式表（现代扁平风格 + 侧边栏）
# ============================================================
MODERN_STYLE = """
/* ===== 全局 ===== */
QMainWindow, QWidget {
    background-color: #f5f7fa;
    color: #1a1a2e;
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ===== 左侧导航栏 ===== */
QFrame#sidebar {
    background-color: #ffffff;
    border: none;
    border-right: 1px solid #e1e5eb;
}
QLabel#sidebarTitle {
    color: #1a1a2e;
    font-size: 15px;
    font-weight: 700;
    padding: 4px 8px 2px 8px;
}
QLabel#sidebarSub {
    color: #7f8c8d;
    font-size: 11px;
    padding: 0 8px 12px 8px;
}
QPushButton#navBtn {
    background-color: transparent;
    color: #475569;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
    min-height: 22px;
}
QPushButton#navBtn:hover {
    background-color: #eef2f7;
    color: #1a1a2e;
}
QPushButton#navBtn[active="true"] {
    background-color: #3498db;
    color: #ffffff;
}
QPushButton#navBtn[active="true"]:hover {
    background-color: #2980b9;
    color: #ffffff;
}

/* ===== 分组框 ===== */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e1e5eb;
    border-radius: 10px;
    margin-top: 14px;
    padding: 18px 16px 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: #2c3e50;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    background-color: #ffffff;
    color: #3498db;
}

/* ===== 按钮通用 ===== */
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #2980b9;
}
QPushButton:pressed {
    background-color: #1f6dad;
}
QPushButton:disabled {
    background-color: #bdc3c7;
    color: #ecf0f1;
}
QPushButton#btnSecondary {
    background-color: #ecf0f1;
    color: #2c3e50;
    border: 1px solid #d5dbe1;
}
QPushButton#btnSecondary:hover {
    background-color: #dfe6e9;
    border-color: #b2bec3;
}
QPushButton#btnSecondary:pressed {
    background-color: #d1d8de;
}
QPushButton#btnDanger {
    background-color: #e74c3c;
}
QPushButton#btnDanger:hover {
    background-color: #c0392b;
}
QPushButton#btnDanger:pressed {
    background-color: #a93226;
}
QPushButton#btnDanger:disabled {
    background-color: #f5b7b1;
    color: #fadbd8;
}
QPushButton#btnPrimary {
    background-color: #27ae60;
    font-size: 15px;
    font-weight: 700;
    min-height: 22px;
    padding: 10px 24px;
}
QPushButton#btnPrimary:hover {
    background-color: #219a52;
}
QPushButton#btnPrimary:pressed {
    background-color: #1e8449;
}
QPushButton#btnPrimary:disabled {
    background-color: #a9dfbf;
    color: #eafaf1;
}

/* ===== 下拉框 ===== */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 20px;
    selection-background-color: #3498db;
}
QComboBox:hover {
    border-color: #3498db;
}
QComboBox:focus {
    border-color: #2980b9;
    outline: none;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #7f8c8d;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    selection-background-color: #3498db;
    selection-color: white;
    outline: none;
    padding: 4px;
}

/* ===== 数字输入框 / 文本输入框 ===== */
QSpinBox, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 5px 10px;
    min-height: 18px;
}
QSpinBox:hover, QLineEdit:hover {
    border-color: #3498db;
}
QSpinBox:focus, QLineEdit:focus {
    border-color: #2980b9;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #f0f3f6;
    border: none;
    border-radius: 4px;
    width: 20px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #e1e8ed;
}
QLineEdit:read-only {
    background-color: #f8f9fa;
    color: #495057;
}

/* ===== 复选框 ===== */
QCheckBox {
    spacing: 8px;
    color: #2c3e50;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #bdc3c7;
    border-radius: 4px;
    background-color: #ffffff;
}
QCheckBox::indicator:hover {
    border-color: #3498db;
}
QCheckBox::indicator:checked {
    background-color: #3498db;
    border-color: #3498db;
}

/* ===== 进度条 ===== */
QProgressBar {
    background-color: #e9ecef;
    border: none;
    border-radius: 10px;
    height: 20px;
    text-align: center;
    color: #2c3e50;
    font-weight: 600;
    font-size: 12px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #3498db, stop:1 #2ecc71);
    border-radius: 10px;
}

/* ===== 文本编辑区（日志） ===== */
QTextEdit {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 10px;
    padding: 10px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    selection-background-color: #45475a;
}

/* ===== 标签 ===== */
QLabel#pageTitle {
    font-size: 18px;
    font-weight: 700;
    color: #1a1a2e;
    padding: 2px 0 4px 0;
}
QLabel#statusLabel {
    font-size: 13px;
    font-weight: 600;
    color: #3498db;
    padding: 4px 0;
}
QLabel#tipLabel {
    color: #7f8c8d;
    font-size: 12px;
    padding: 4px 2px;
}

/* ===== 滚动条 ===== */
QScrollBar:vertical {
    background: #f0f0f0;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #c0c0c0;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #a0a0a0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ollama SRT 长篇自动翻译工具")
        self.resize(1000, 720)
        self.setMinimumSize(860, 580)
        self.worker = None
        self.selected_srt = None
        self.setStyleSheet(MODERN_STYLE)
        self._init_ui()
        self.refresh_models()
        self._load_settings()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ---- 左侧导航 ----
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(168)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 20, 12, 16)
        side_layout.setSpacing(6)

        title = QLabel("Ollama SRT")
        title.setObjectName("sidebarTitle")
        side_layout.addWidget(title)
        side_layout.addSpacing(12)

        self.btn_nav_settings = QPushButton("  ⚙  设置")
        self.btn_nav_settings.setObjectName("navBtn")
        self.btn_nav_settings.setCursor(Qt.PointingHandCursor)
        self.btn_nav_settings.clicked.connect(lambda: self._switch_page(0))
        side_layout.addWidget(self.btn_nav_settings)

        self.btn_nav_log = QPushButton("  📋  运行日志")
        self.btn_nav_log.setObjectName("navBtn")
        self.btn_nav_log.setCursor(Qt.PointingHandCursor)
        self.btn_nav_log.clicked.connect(lambda: self._switch_page(1))
        side_layout.addWidget(self.btn_nav_log)

        side_layout.addStretch(1)

        # 侧栏底部： 状态（翻译时随时可见）
        self.side_status = QLabel("就绪")
        self.side_status.setStyleSheet(
            "color: #7f8c8d; font-size: 12px; padding: 4px 8px;"
        )
        self.side_status.setWordWrap(True)
        side_layout.addWidget(self.side_status)

        root.addWidget(sidebar)

        # ---- 右侧内容栈 ----
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.stack.addWidget(self._build_settings_page())  # index 0
        self.stack.addWidget(self._build_log_page())       # index 1

        self._switch_page(0)

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(20, 16, 20, 14)
        outer.setSpacing(10)

        page_title = QLabel("设置")
        page_title.setObjectName("pageTitle")
        outer.addWidget(page_title)

        # 可滚动表单，窗口较矮时也能看全
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        form_host = QWidget()
        form_layout = QVBoxLayout(form_host)
        form_layout.setContentsMargins(0, 0, 8, 0)
        form_layout.setSpacing(10)

        form_box = QGroupBox("翻译参数")
        box = QVBoxLayout(form_box)
        box.setContentsMargins(14, 14, 14, 12)
        box.setSpacing(10)

        # 模型
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(QLabel("Ollama 模型:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(220)
        self.model_combo.setEditable(False)
        self.model_combo.setCursor(Qt.PointingHandCursor)
        row1.addWidget(self.model_combo, 1)
        btn_refresh = QPushButton("刷新模型")
        btn_refresh.setObjectName("btnSecondary")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_models)
        row1.addWidget(btn_refresh)
        box.addLayout(row1)

        # URL
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(QLabel("Ollama:"))
        self.edit_url = QLineEdit("http://127.0.0.1:11434/api/generate")
        self.edit_url.setPlaceholderText("http://127.0.0.1:11434/api/generate")
        row2.addWidget(self.edit_url, 1)
        box.addLayout(row2)

        # SRT
        row3 = QHBoxLayout()
        row3.setSpacing(8)
        row3.addWidget(QLabel("SRT 文件:"))
        self.edit_srt = QLineEdit()
        self.edit_srt.setPlaceholderText("请选择 SRT 字幕文件…")
        self.edit_srt.setReadOnly(True)
        row3.addWidget(self.edit_srt, 1)
        btn_srt = QPushButton("选择 SRT")
        btn_srt.setObjectName("btnSecondary")
        btn_srt.setCursor(Qt.PointingHandCursor)
        btn_srt.clicked.connect(self.select_srt)
        row3.addWidget(btn_srt)
        box.addLayout(row3)

         # 输出目录（文件名在翻译结束合并时自动生成）
        row4 = QHBoxLayout()
        row4.setSpacing(8)
        row4.addWidget(QLabel("输出目录:"))
        self.edit_output = QLineEdit()
        self.edit_output.setPlaceholderText("可留空：默认项目 output/；结束时自动命名（日期+模型+原文件名_zh.srt）")
        self.edit_output.setReadOnly(True)
        row4.addWidget(self.edit_output, 1)
        btn_out = QPushButton("选择目录")
        btn_out.setObjectName("btnSecondary")
        btn_out.setCursor(Qt.PointingHandCursor)
        btn_out.clicked.connect(self.select_output)
        row4.addWidget(btn_out)
        box.addLayout(row4)

        # 窗口参数
        row5 = QHBoxLayout()
        row5.setSpacing(8)
        row5.addWidget(QLabel("主翻译:"))
        self.spin_main = QSpinBox()
        self.spin_main.setRange(1, 100)
        self.spin_main.setValue(20)
        self.spin_main.setFixedWidth(70)
        row5.addWidget(self.spin_main)
        row5.addWidget(QLabel("前上下文:"))
        self.spin_before = QSpinBox()
        self.spin_before.setRange(0, 30)
        self.spin_before.setValue(5)
        self.spin_before.setFixedWidth(60)
        row5.addWidget(self.spin_before)
        row5.addWidget(QLabel("后上下文:"))
        self.spin_after = QSpinBox()
        self.spin_after.setRange(0, 30)
        self.spin_after.setValue(5)
        self.spin_after.setFixedWidth(60)
        row5.addWidget(self.spin_after)
        row5.addWidget(QLabel("重试:"))
        self.spin_retries = QSpinBox()
        self.spin_retries.setRange(1, 20)
        self.spin_retries.setValue(3)
        self.spin_retries.setFixedWidth(55)
        row5.addWidget(self.spin_retries)
        row5.addWidget(QLabel("重试等待:"))
        self.spin_retry_wait = QSpinBox()
        self.spin_retry_wait.setRange(1, 60)
        self.spin_retry_wait.setValue(5)
        self.spin_retry_wait.setSuffix("s")
        self.spin_retry_wait.setFixedWidth(70)
        row5.addWidget(self.spin_retry_wait)
        row5.addStretch(1)
        box.addLayout(row5)

        # Keep Alive / 超时 / 清空缓存
        row6 = QHBoxLayout()
        row6.setSpacing(8)
        row6.addWidget(QLabel("Keep Alive:"))
        self.edit_keepalive = QLineEdit("120m")
        self.edit_keepalive.setFixedWidth(100)
        self.edit_keepalive.setPlaceholderText("120m")
        row6.addWidget(self.edit_keepalive)
        row6.addSpacing(12)
        row6.addWidget(QLabel("超时:"))
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(30, 7200)
        self.spin_timeout.setValue(3600)
        self.spin_timeout.setSuffix(" 秒")
        self.spin_timeout.setFixedWidth(110)
        row6.addWidget(self.spin_timeout)
        row6.addSpacing(16)
        self.chk_clear_cache = QCheckBox("开始前清空全部缓存（强制重新翻译）")
        self.chk_clear_cache.setCursor(Qt.PointingHandCursor)
        row6.addWidget(self.chk_clear_cache)
        row6.addStretch(1)
        box.addLayout(row6)

        form_layout.addWidget(form_box)
        form_layout.addStretch(1)
        scroll.setWidget(form_host)
        outer.addWidget(scroll, 1)

        # 控制按钮（始终贴在设置页底部）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.btn_start = QPushButton("开始翻译")
        self.btn_start.setObjectName("btnPrimary")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_translate)
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setObjectName("btnDanger")
        self.btn_stop.setMinimumWidth(110)
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_translate)
        btn_layout.addWidget(self.btn_start, 3)
        btn_layout.addWidget(self.btn_stop, 1)
        outer.addLayout(btn_layout)

        # 进度条：整行显示，位于按钮下方、状态/日志行上方
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(20)
        outer.addWidget(self.progress_bar)

        self.status_label = QLabel("就绪 — 请选择 SRT 文件并选择模型后开始")
        self.status_label.setObjectName("statusLabel")
        outer.addWidget(self.status_label)

        tip = QLabel("💡  提示：翻译开始后可切换到「运行日志」查看实时输出；进度条在「设置」页底部。")
        tip.setObjectName("tipLabel")
        tip.setWordWrap(True)
        outer.addWidget(tip)

        return page

    def _build_log_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        page_title = QLabel("运行日志")
        page_title.setObjectName("pageTitle")
        header.addWidget(page_title)
        header.addStretch(1)

        btn_clear = QPushButton("清空显示")
        btn_clear.setObjectName("btnSecondary")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_log_view)
        header.addWidget(btn_clear)
        layout.addLayout(header)



        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setAcceptRichText(True)
        self.log_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.log_edit, 1)

         # ✅ 新增：日志页进度条（与设置页同步）
        self.log_progress = QProgressBar()
        self.log_progress.setValue(0)
        self.log_progress.setTextVisible(True)
        self.log_progress.setFormat("%p%")
        self.log_progress.setFixedHeight(20)
        layout.addWidget(self.log_progress)

        tip = QLabel("💡  日志同时写入 cache/run.log。流式输出会实时追加；翻译中可随时返回设置页点「停止」。")
        tip.setObjectName("tipLabel")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        return page

    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        self.btn_nav_settings.setProperty("active", "true" if index == 0 else "false")
        self.btn_nav_log.setProperty("active", "true" if index == 1 else "false")
        # 强制刷新样式
        self.btn_nav_settings.style().unpolish(self.btn_nav_settings)
        self.btn_nav_settings.style().polish(self.btn_nav_settings)
        self.btn_nav_log.style().unpolish(self.btn_nav_log)
        self.btn_nav_log.style().polish(self.btn_nav_log)

    def _clear_log_view(self):
        self.log_edit.clear()

    # ------------------------------------------------------------------
    # 文件选择 / 模型
    # ------------------------------------------------------------------
    def select_srt(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 SRT 字幕文件",
            str(Path.home()),
            "SRT 文件 (*.srt);;所有文件 (*)"
        )
        if path:
            self.selected_srt = Path(path)
            self.edit_srt.setText(str(self.selected_srt))
            # 不在选中时预填输出路径；结束合并时再按规则生成
            self.append_log(f"已选择文件：{self.selected_srt}", "info")

    def select_output(self):
        # 选择输出文件夹（文件名在翻译结束合并时自动生成）
        ensure_dirs()
        current = self.edit_output.text().strip()
        default_dir = current if current and Path(current).is_dir() else str(OUTPUT_DIR)
        path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            default_dir,
        )
        if path:
            self.edit_output.setText(path)
            self.append_log(f"输出目录：{path}", "info")

    def refresh_models(self):
        self.model_combo.clear()
        self.append_log("正在获取 Ollama 模型列表…", "info")
        url = self.edit_url.text().strip() if hasattr(self, "edit_url") else "http://127.0.0.1:11434/api/generate"
        base = url
        if "/api/" in base:
            base = base.split("/api/")[0]
        try:
            models = fetch_ollama_models(base)
            if not models:
                self.append_log("未检测到任何已安装模型。请先用 ollama pull 下载模型。", "warning")
                self.model_combo.addItem("（无可用模型）")
                return
            self.model_combo.addItems(models)
            self.append_log(f"成功加载 {len(models)} 个模型。", "success")
            for preferred in ["qwen2.5:14b", "qwen2.5:7b", "llama3.1:8b", "gemma2:9b"]:
                idx = self.model_combo.findText(preferred)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
                    break
        except Exception as e:
            self.append_log(f"获取模型失败：{e}", "error")
            self.model_combo.addItem("（获取失败，请检查 Ollama 是否运行）")

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------
    def append_log(self, text, level="info"):
        """
        level: info / success / warning / error / prompt / stream / system
        同时写入界面 + cache/run.log
        """
        write_log_file(str(text), level)
        if not hasattr(self, "log_edit") or self.log_edit is None:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        colors = {
            "info":    "#cdd6f4",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "error":   "#f38ba8",
            "prompt":  "#89b4fa",
            "stream":  "#94e2d5",
            "system":  "#cba6f7",
        }
        color = colors.get(level, "#cdd6f4")
        icons = {
            "info":    "•",
            "success": "✓",
            "warning": "⚠",
            "error":   "✗",
            "prompt":  "▶",
            "stream":  "",
            "system":  "◆",
        }
        icon = icons.get(level, "•")
        safe_text = html.escape(str(text)).replace("\n", "<br>")
        if level == "stream":
            html_line = f'<span style="color:{color};">{safe_text}</span>'
        else:
            html_line = (
                f'<span style="color:#6c7086;">[{ts}]</span> '
                f'<span style="color:{color};">{icon} {safe_text}</span>'
            )
        self.log_edit.append(html_line)
        self.log_edit.moveCursor(QTextCursor.End)

    # ------------------------------------------------------------------
    # 翻译控制
    # ------------------------------------------------------------------
    def start_translate(self):
        srt_text = self.edit_srt.text().strip()
        if not srt_text or not Path(srt_text).exists():
            QMessageBox.warning(self, "提示", "请先选择有效的 SRT 文件！")
            return
        model = self.model_combo.currentText().strip()
        if not model or "无可用" in model or "获取失败" in model:
            QMessageBox.warning(self, "提示", "请选择有效的 Ollama 模型！")
            return
        out_text = self.edit_output.text().strip()
        if not out_text:
            QMessageBox.warning(self, "提示", "请指定输出文件路径！")
            return
        # 输出目录可留空：默认项目 output/；文件名结束合并时自动生成
        out_dir_text = self.edit_output.text().strip()
        ollama_url = self.edit_url.text().strip()
        if not ollama_url:
            QMessageBox.warning(self, "提示", "请填写 Ollama 接口地址！")
            return

        self.selected_srt = Path(srt_text)
        output_dir = Path(out_dir_text) if out_dir_text else None
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)     # ✅ 重置设置页进度条
        self.log_progress.setValue(0)     # ✅ 重置日志页进度条
        self.status_label.setText("准备中…")
        self.side_status.setText("准备中…")

        try:
            ensure_dirs()
            LOG_FILE.write_text("", encoding="utf-8")
        except Exception:
            pass

        self.append_log("─" * 40, "system")
        self.append_log("开始翻译任务…", "system")
        # 开始后自动切到日志页，方便看流式输出
        self._switch_page(1)

        self.worker = TranslateWorker(
            srt_path=self.selected_srt,
            output_path=output_dir,
            model_name=model,
            ollama_url=ollama_url,
            main_count=self.spin_main.value(),
            ctx_before=self.spin_before.value(),
            ctx_after=self.spin_after.value(),
            max_retries=self.spin_retries.value(),
            retry_wait=self.spin_retry_wait.value(),
            keep_alive=self.edit_keepalive.text().strip() or "120m",
            timeout_seconds=self.spin_timeout.value(),
            clear_cache=self.chk_clear_cache.isChecked()
        )
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.on_progress)
        self.worker.status_signal.connect(self._on_status)
        self.worker.finished_signal.connect(self.on_finished)
        self._save_settings()
        self.worker.start()

    def stop_translate(self):
        if self.worker and self.worker.isRunning():
            self.append_log("正在请求停止…", "warning")
            self.worker.stop()
            self.btn_stop.setEnabled(False)

    def _on_status(self, text: str):
        self.status_label.setText(text)
        self.side_status.setText(text)

    def on_progress(self, current, total):
        if total > 0:
            for bar in (self.progress_bar, self.log_progress):
                bar.setMaximum(total)
                bar.setValue(current)

    def on_finished(self, success, message):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if success:
            self.status_label.setText("✅  翻译完成")
            self.side_status.setText("✅ 翻译完成")
            QMessageBox.information(self, "完成", f"翻译成功！\n\n输出文件：\n{message}")
        else:
            self.status_label.setText("⏹  已停止或失败")
            self.side_status.setText("⏹ 已停止或失败")
            if message != "用户中断":
                QMessageBox.warning(self, "失败", f"翻译未完成：\n{message}")

    def closeEvent(self, event):
        self._save_settings()
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认退出",
                "翻译正在进行中，确定要退出吗？\n已完成的批次会保留缓存。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait(3000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    # ------------------------------------------------------------------
    # 配置读写
    # ------------------------------------------------------------------
    def _load_settings(self):
        cfg = load_gui_config()
        if not cfg:
            return
        if url := cfg.get("ollama_url"):
            self.edit_url.setText(url)
        if model := cfg.get("model"):
            idx = self.model_combo.findText(model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.model_combo.setEditText(model) if self.model_combo.isEditable() else None
        if srt := cfg.get("srt_path"):
            p = Path(srt)
            if p.exists():
                self.selected_srt = p
                self.edit_srt.setText(str(p))
        if out := cfg.get("output_path"):
            p = Path(out)
            self.edit_output.setText(str(p.parent if p.suffix.lower() == ".srt" else p))
        self.spin_main.setValue(cfg.get("main_count", 20))
        self.spin_before.setValue(cfg.get("ctx_before", 5))
        self.spin_after.setValue(cfg.get("ctx_after", 5))
        self.spin_retries.setValue(cfg.get("max_retries", 3))
        self.spin_retry_wait.setValue(cfg.get("retry_wait", 5))
        self.spin_timeout.setValue(cfg.get("timeout_seconds", 3600))
        if ka := cfg.get("keep_alive"):
            self.edit_keepalive.setText(ka)
        self.chk_clear_cache.setChecked(cfg.get("clear_cache", False))

    def _save_settings(self):
        data = {
            "ollama_url": self.edit_url.text().strip(),
            "model": self.model_combo.currentText().strip(),
            "srt_path": self.edit_srt.text().strip(),
            "output_path": self.edit_output.text().strip(),
            "main_count": self.spin_main.value(),
            "ctx_before": self.spin_before.value(),
            "ctx_after": self.spin_after.value(),
            "max_retries": self.spin_retries.value(),
            "retry_wait": self.spin_retry_wait.value(),
            "keep_alive": self.edit_keepalive.text().strip() or "120m",
            "timeout_seconds": self.spin_timeout.value(),
            "clear_cache": self.chk_clear_cache.isChecked(),
        }
        save_gui_config(data)
