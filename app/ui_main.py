from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QImage, QPixmap, QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSpinBox,
    QStackedLayout,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QScrollArea,
)

from app.config import AISettings, RenderSettings
from app.database import Database, Segment
from app.workers import RenderWorker, start_worker, TaskResult


@dataclass
class UiState:
    last_frame: QImage | None = None
    current_video: Path | None = None


class Theme:
    """主题配色 - 参考 IntelliJ IDEA 新UI设计（夜间模式）"""
    
    # 配色方案
    COLORS = {
        'bg_primary': '#1e1f22',
        'bg_secondary': '#2b2d30',
        'bg_tertiary': '#313335',
        'bg_editor': '#1e1f22',
        'bg_hover': '#2d2f32',
        'border': '#3e4245',
        'border_light': '#545659',
        'text_primary': '#bcbec4',
        'text_secondary': '#868a91',
        'text_disabled': '#5f6368',
        'accent': '#3574f0',
        'accent_hover': '#4f8cf5',
        'accent_pressed': '#2264dc',
        'button_default': '#3e4245',
        'button_disabled': '#303236',
        'title_bar': '#2b2d30',
    }
    
    @classmethod
    def get_stylesheet(cls) -> str:
        theme = cls.COLORS
        return f"""
        QMainWindow {{
            background-color: {theme['bg_primary']};
            color: {theme['text_primary']};
        }}
        
        QWidget {{
            background-color: {theme['bg_primary']};
            color: {theme['text_primary']};
            font-size: 13px;
        }}
        
        QGroupBox {{
            color: {theme['text_primary']};
            border: 1px solid {theme['border']};
            border-radius: 8px;
            margin-top: 12px;
            padding: 12px;
            font-weight: 600;
            font-size: 12px;
            background-color: {theme['bg_secondary']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px;
            background-color: {theme['bg_secondary']};
        }}
        
        QPushButton {{
            background-color: {theme['accent']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: 500;
            font-size: 13px;
            min-height: 24px;
        }}
        
        QPushButton:hover {{
            background-color: {theme['accent_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {theme['accent_pressed']};
        }}
        
        QPushButton:disabled {{
            background-color: {theme['button_disabled']};
            color: {theme['text_disabled']};
        }}
        
        QLineEdit, QPlainTextEdit, QSpinBox {{
            background-color: {theme['bg_editor']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border']};
            border-radius: 6px;
            padding: 6px 10px;
            selection-background-color: {theme['accent']};
            selection-color: white;
        }}
        
        QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
            border: 1px solid {theme['accent']};
            outline: none;
        }}
        
        QLineEdit:hover, QPlainTextEdit:hover, QSpinBox:hover {{
            border: 1px solid {theme['border_light']};
        }}
        
        QComboBox {{
            background-color: {theme['bg_editor']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border']};
            border-radius: 6px;
            padding: 5px 10px;
            min-height: 24px;
        }}
        
        QComboBox:hover {{
            border: 1px solid {theme['border_light']};
        }}
        
        QComboBox:focus {{
            border: 1px solid {theme['accent']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {theme['bg_secondary']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border']};
            border-radius: 6px;
            selection-background-color: {theme['accent']};
            selection-color: white;
            outline: none;
        }}
        
        QLabel {{
            color: {theme['text_secondary']};
            background-color: transparent;
        }}
        
        QListWidget {{
            background-color: {theme['bg_secondary']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border']};
            border-radius: 8px;
            padding: 4px;
            outline: none;
        }}
        
        QListWidget::item {{
            padding: 12px;
            background-color: {theme['bg_editor']};
            margin-bottom: 6px;
            border-radius: 6px;
            border: 1px solid transparent;
        }}
        
        QListWidget::item:hover {{
            background-color: {theme['bg_hover']};
            border: 1px solid {theme['border_light']};
        }}
        
        QListWidget::item:selected {{
            background-color: {theme['bg_editor']};
            border: 1px solid {theme['accent']};
            color: {theme['text_primary']};
        }}
        
        QStatusBar {{
            background-color: {theme['bg_secondary']};
            color: {theme['text_secondary']};
            border-top: 1px solid {theme['border']};
            padding: 4px 8px;
        }}
        
        QMenuBar {{
            background-color: {theme['title_bar']};
            color: {theme['text_primary']};
            border-bottom: 1px solid {theme['border']};
            padding: 2px;
            spacing: 2px;
        }}
        
        QMenuBar::item {{
            padding: 6px 12px;
            background-color: transparent;
            border-radius: 6px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {theme['bg_hover']};
        }}
        
        QMenuBar::item:pressed {{
            background-color: {theme['accent']};
            color: white;
        }}
        
        QMenu {{
            background-color: {theme['bg_secondary']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border']};
            border-radius: 8px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 6px 20px 6px 12px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {theme['accent']};
            color: white;
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {theme['border']};
            margin: 4px 0;
        }}
        
        QScrollBar:vertical {{
            background-color: transparent;
            width: 12px;
            border: none;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {theme['border_light']};
            border-radius: 6px;
            min-height: 30px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {theme['border']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
            border: none;
        }}
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        
        QScrollBar:horizontal {{
            background-color: transparent;
            height: 12px;
            border: none;
            margin: 0;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {theme['border_light']};
            border-radius: 6px;
            min-width: 30px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {theme['border']};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
            border: none;
        }}
        
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
        
        QTabWidget::pane {{
            border: none;
            background-color: transparent;
        }}
        
        QTabBar {{
            background-color: transparent;
        }}
        
        QTabBar::tab {{
            background-color: transparent;
            color: {theme['text_secondary']};
            padding: 8px 16px;
            margin-right: 4px;
            border: none;
            border-bottom: 2px solid transparent;
            font-weight: 500;
        }}
        
        QTabBar::tab:hover {{
            color: {theme['text_primary']};
            background-color: {theme['bg_hover']};
            border-radius: 6px 6px 0 0;
        }}
        
        QTabBar::tab:selected {{
            color: {theme['accent']};
            border-bottom: 2px solid {theme['accent']};
        }}
        
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 16px;
            border: none;
            background-color: transparent;
        }}
        
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: {theme['bg_hover']};
        }}
        """
    
    @classmethod
    def apply(cls, app: QApplication) -> None:
        """\u5e94\u7528\u591c\u95f4\u4e3b\u9898"""
        app.setStyle("Fusion")
        app.setStyleSheet(cls.get_stylesheet())


class PlayerWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.video_widget = QVideoWidget(self)
        self.still_label = QLabel("", self)
        self.still_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.still_label.setStyleSheet("background: black;")
        self.still_label.hide()
        self._last_frame: QImage | None = None

        self.layout = QStackedLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.video_widget)
        self.layout.addWidget(self.still_label)
        self.layout.setCurrentWidget(self.video_widget)

    def show_last_frame(self, image: QImage) -> None:
        self._last_frame = image
        self._update_still_pixmap()
        self.layout.setCurrentWidget(self.still_label)
        self.still_label.show()

    def show_video(self) -> None:
        self.layout.setCurrentWidget(self.video_widget)
        self.still_label.hide()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.still_label.isVisible() and self._last_frame is not None:
            self._update_still_pixmap()

    def _update_still_pixmap(self) -> None:
        if self._last_frame is None:
            return
        pixmap = QPixmap.fromImage(self._last_frame)
        if pixmap.isNull():
            return
        target = self.video_widget.size()
        if target.width() > 0 and target.height() > 0:
            pixmap = pixmap.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.still_label.setPixmap(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, db: Database, jobs_dir: Path) -> None:
        super().__init__()
        self.setWindowTitle("Manimai")
        self.resize(1400, 900)

        self._db = db
        self._jobs_dir = jobs_dir
        self._ui_state = UiState()
        self._worker_thread = None
        self._current_worker = None
        self._play_queue: list[Path] = []
        self._active_workspace = self._db.get_setting("active_workspace", "default")
        self._active_job_dir = self._jobs_dir / self._active_workspace
        self._current_segment: Segment | None = None
        self._playback_active = False

        self._build_ui()
        self._load_settings()
        self._load_history()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧：输入和播放器（占比 2:1）
        left_widget = self._build_left_panel()
        
        # 右侧：设置和历史（占比 1）
        right_widget = self._build_right_panel()

        main_layout.addWidget(left_widget, 2)
        main_layout.addWidget(right_widget, 1)

        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

        self._build_menus()
        self._build_player_backend()

    def _build_left_panel(self) -> QWidget:
        """构建左侧面板：输入和播放器"""
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {Theme.COLORS['bg_primary']};")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 8, 16)
        layout.setSpacing(16)

        # 标题
        title = QLabel("动画生成")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {Theme.COLORS['text_primary']}; padding-bottom: 8px;")
        layout.addWidget(title)

        # 输入区
        input_group = self._build_input_group()
        layout.addWidget(input_group)

        # 播放器
        player_group = self._build_player_group()
        layout.addWidget(player_group, 1)

        return widget

    def _build_input_group(self) -> QGroupBox:
        """构建输入分组"""
        group = QGroupBox("输入描述")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)

        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText("请输入你想要创建的动画描述...\n\n例如: 一个旋转的立方体，然后变成一个球体")
        self.prompt_input.setMinimumHeight(100)
        self.prompt_input.setMaximumHeight(120)
        layout.addWidget(self.prompt_input)

        self.generate_btn = QPushButton("生成并播放")
        self.generate_btn.setMinimumHeight(36)
        self.generate_btn.clicked.connect(self._on_generate)
        gen_font = QFont()
        gen_font.setPointSize(13)
        gen_font.setWeight(QFont.Weight.Medium)
        self.generate_btn.setFont(gen_font)
        layout.addWidget(self.generate_btn)

        return group

    def _build_player_group(self) -> QGroupBox:
        """构建播放器分组"""
        group = QGroupBox("播放器")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(2, 20, 2, 2)
        
        self.player = PlayerWidget()
        self.player.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.player)

        return group

    def _build_right_panel(self) -> QWidget:
        """构建右侧面板：选项卡"""
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {Theme.COLORS['bg_secondary']};")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 16, 16, 16)
        layout.setSpacing(0)

        # 使用选项卡来组织内容
        tabs = QTabWidget()

        # 历史选项卡
        history_widget = self._build_history_tab()
        tabs.addTab(history_widget, "分段历史")

        # 设置选项卡
        settings_widget = self._build_settings_tab()
        tabs.addTab(settings_widget, "设置")

        # 控制台选项卡
        console_widget = self._build_console_tab()
        tabs.addTab(console_widget, "控制台")

        layout.addWidget(tabs)

        return widget

    def _build_history_tab(self) -> QWidget:
        """构建历史选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.history_list)
        
        return widget

    def _build_settings_tab(self) -> QWidget:
        """构建设置选项卡"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # 输出设置
        output_group = self._build_output_settings_group()
        layout.addWidget(output_group)

        # AI 设置
        ai_group = self._build_ai_settings_group()
        layout.addWidget(ai_group)

        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _build_console_tab(self) -> QWidget:
        """构建控制台选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Consolas, Courier New, monospace", 10))
        layout.addWidget(self.console_output)
        
        return widget

    def _build_output_settings_group(self) -> QGroupBox:
        """构建输出设置分组"""
        group = QGroupBox("输出参数")
        layout = QFormLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(16)

        self.width_input = QSpinBox()
        self.width_input.setRange(320, 3840)
        self.width_input.setValue(1920)
        self.height_input = QSpinBox()
        self.height_input.setRange(240, 2160)
        self.height_input.setValue(1080)
        self.fps_input = QSpinBox()
        self.fps_input.setRange(1, 120)
        self.fps_input.setValue(30)
        self.quality_input = QComboBox()
        self.quality_input.addItems(["l", "m", "h", "k"])
        self.quality_input.setCurrentText("k")

        layout.addRow("分辨率宽度", self.width_input)
        layout.addRow("分辨率高度", self.height_input)
        layout.addRow("帧率 (FPS)", self.fps_input)
        layout.addRow("质量", self.quality_input)

        return group

    def _build_ai_settings_group(self) -> QGroupBox:
        """构建 AI 设置分组"""
        group = QGroupBox("AI 配置")
        layout = QFormLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setVerticalSpacing(12)
        layout.setHorizontalSpacing(16)

        self.ai_mode_input = QComboBox()
        self.ai_mode_input.addItems(["DeepSeek", "Gemini"])
        self.ai_mode_input.currentTextChanged.connect(self._on_ai_mode_changed)

        self.deepseek_key = QLineEdit()
        self.deepseek_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepseek_base = QLineEdit()
        self.deepseek_model = QLineEdit()

        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_model = QLineEdit()

        self.deepseek_key_label = QLabel("API Key")
        self.deepseek_base_label = QLabel("API 地址")
        self.deepseek_model_label = QLabel("模型名称")
        self.gemini_key_label = QLabel("API Key")
        self.gemini_model_label = QLabel("模型名称")

        layout.addRow("AI 模型", self.ai_mode_input)
        layout.addRow("", QWidget())  # 分隔符
        layout.addRow(self.deepseek_key_label, self.deepseek_key)
        layout.addRow(self.deepseek_base_label, self.deepseek_base)
        layout.addRow(self.deepseek_model_label, self.deepseek_model)
        layout.addRow(self.gemini_key_label, self.gemini_key)
        layout.addRow(self.gemini_model_label, self.gemini_model)

        self.save_settings_btn = QPushButton("保存配置")
        self.save_settings_btn.clicked.connect(self._save_settings)
        layout.addRow("", self.save_settings_btn)

        return group

    def _build_menus(self) -> None:
        workspace_menu = self.menuBar().addMenu("工作区")
        manage_menu = workspace_menu.addMenu("管理")
        self.new_workspace_action = QAction("新建工作区", self)
        self.new_workspace_action.triggered.connect(self._create_workspace)
        self.switch_workspace_action = QAction("切换工作区", self)
        self.switch_workspace_action.triggered.connect(self._switch_workspace)
        self.delete_workspace_action = QAction("删除工作区", self)
        self.delete_workspace_action.triggered.connect(self._delete_workspace)
        manage_menu.addAction(self.new_workspace_action)
        manage_menu.addAction(self.switch_workspace_action)
        manage_menu.addAction(self.delete_workspace_action)

    def _build_player_backend(self) -> None:
        self.player_backend = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player_backend.setAudioOutput(self.audio_output)
        self.player_backend.setVideoOutput(self.player.video_widget)
        self.player_backend.mediaStatusChanged.connect(self._on_media_status)
        video_sink = self.player.video_widget.videoSink()
        if video_sink is not None:
            video_sink.videoFrameChanged.connect(self._on_video_frame)

    def _on_ai_mode_changed(self, mode: str) -> None:
        is_deepseek = mode == "DeepSeek"
        self.deepseek_key_label.setVisible(is_deepseek)
        self.deepseek_key.setVisible(is_deepseek)
        self.deepseek_base_label.setVisible(is_deepseek)
        self.deepseek_base.setVisible(is_deepseek)
        self.deepseek_model_label.setVisible(is_deepseek)
        self.deepseek_model.setVisible(is_deepseek)
        
        is_gemini = mode == "Gemini"
        self.gemini_key_label.setVisible(is_gemini)
        self.gemini_key.setVisible(is_gemini)
        self.gemini_model_label.setVisible(is_gemini)
        self.gemini_model.setVisible(is_gemini)

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console_output.appendPlainText(f"[{timestamp}] {message}")

    def _create_workspace(self) -> None:
        name, ok = QInputDialog.getText(self, "新建工作区", "输入工作区名称")
        if not ok:
            return
        workspace = name.strip()
        if not workspace:
            QMessageBox.warning(self, "提示", "工作区名称不能为空")
            return
        self._set_active_workspace(workspace)

    def _switch_workspace(self) -> None:
        name, ok = QInputDialog.getText(self, "切换工作区", "输入工作区名称")
        if not ok:
            return
        workspace = name.strip()
        if not workspace:
            QMessageBox.warning(self, "提示", "工作区名称不能为空")
            return
        self._set_active_workspace(workspace)

    def _set_active_workspace(self, workspace: str) -> None:
        self._active_workspace = workspace
        self._active_job_dir = self._jobs_dir / workspace
        self._active_job_dir.mkdir(parents=True, exist_ok=True)
        self._db.set_setting("active_workspace", workspace)
        self._load_history()
        self._log(f"已切换工作区: {workspace}")

    def _delete_workspace(self) -> None:
        workspaces = self._list_workspaces()
        if not workspaces:
            QMessageBox.information(self, "提示", "暂无可删除的工作区")
            return

        name, ok = QInputDialog.getItem(self, "删除工作区", "选择要删除的工作区", workspaces, 0, False)
        if not ok:
            return
        workspace = name.strip()
        if not workspace:
            QMessageBox.warning(self, "提示", "工作区名称不能为空")
            return

        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除工作区 '{workspace}' 吗？此操作不可撤销。"
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        import shutil
        workspace_dir = self._jobs_dir / workspace
        try:
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)
            self._db.delete_workspace_data(workspace)
            self._log(f"已删除工作区: {workspace}")

            # 如果删除的是当前工作区，需要切换到其他工作区或创建临时工作区
            if workspace == self._active_workspace:
                remaining = self._list_workspaces()
                target_workspace = remaining[0] if remaining else "temp"
                self._set_active_workspace(target_workspace)
                message = f"当前工作区已删除，已切换到 '{target_workspace}'"
                QMessageBox.information(self, "提示", message)

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "错误", f"删除工作区失败: {exc}")
            self._log(f"删除工作区失败: {exc}")

    def _list_workspaces(self) -> list[str]:
        if not self._jobs_dir.exists():
            return []
        return sorted(
            [
                item.name
                for item in self._jobs_dir.iterdir()
                if item.is_dir() and not item.name.startswith(".")
            ]
        )

    def _load_settings(self) -> None:
        self.width_input.setValue(int(self._db.get_setting("width", "1920")))
        self.height_input.setValue(int(self._db.get_setting("height", "1080")))
        self.fps_input.setValue(int(self._db.get_setting("fps", "30")))
        self.quality_input.setCurrentText(self._db.get_setting("quality", "k"))
        self.ai_mode_input.setCurrentText(self._db.get_setting("ai_mode", "DeepSeek"))

        self.deepseek_key.setText(self._db.get_setting("deepseek_key", ""))
        self.deepseek_base.setText(self._db.get_setting("deepseek_base", "https://api.deepseek.com"))
        self.deepseek_model.setText(self._db.get_setting("deepseek_model", "deepseek-chat"))

        self.gemini_key.setText(self._db.get_setting("gemini_key", ""))
        self.gemini_model.setText(self._db.get_setting("gemini_model", "gemini-1.5-flash"))
        self._on_ai_mode_changed(self.ai_mode_input.currentText())

    def _save_settings(self) -> None:
        self._db.bulk_set_settings(
            [
                ("width", str(self.width_input.value())),
                ("height", str(self.height_input.value())),
                ("fps", str(self.fps_input.value())),
                ("quality", self.quality_input.currentText()),
                ("ai_mode", self.ai_mode_input.currentText()),
                ("deepseek_key", self.deepseek_key.text().strip()),
                ("deepseek_base", self.deepseek_base.text().strip()),
                ("deepseek_model", self.deepseek_model.text().strip()),
                ("gemini_key", self.gemini_key.text().strip()),
                ("gemini_model", self.gemini_model.text().strip()),
            ]
        )
        self.status.showMessage("设置已保存", 3000)

    def _load_history(self) -> None:
        self.history_list.clear()
        for segment in self._db.list_segments(self._active_workspace):
            list_item = QListWidgetItem()
            list_item.setData(Qt.ItemDataRole.UserRole, segment)
            widget = self._build_segment_widget(segment)
            list_item.setSizeHint(widget.sizeHint())
            self.history_list.addItem(list_item)
            self.history_list.setItemWidget(list_item, widget)

    def _build_segment_widget(self, segment: Segment) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(20)
        
        # 分段信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)
        title = QLabel(f"<b>分段 #{segment.segment_index}</b>")
        title.setStyleSheet(f"color: {Theme.COLORS['text_primary']}; font-size: 14px;")
        desc = QLabel(segment.input_text[:100] + "..." if len(segment.input_text) > 100 else segment.input_text)
        desc.setStyleSheet(f"color: {Theme.COLORS['text_secondary']}; font-size: 13px; line-height: 1.6;")
        desc.setWordWrap(True)
        desc.setMinimumHeight(45)
        info_layout.addWidget(title)
        info_layout.addWidget(desc)
        
        # 播放按钮
        play_btn = QPushButton("播放")
        play_btn.setFixedWidth(80)
        play_btn.setFixedHeight(32)
        play_btn.setEnabled(bool(segment.section_video_path))
        play_btn.clicked.connect(lambda: self._play_segment(segment))
        
        layout.addLayout(info_layout, 1)
        layout.addWidget(play_btn)
        
        return container


    def _on_generate(self) -> None:
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "请输入动画描述")
            return

        if self._worker_thread is not None and self._worker_thread.isRunning():
            QMessageBox.information(self, "提示", "已有任务正在运行")
            return

        self._log("开始新任务")
        
        # 先获取上一轮的累积代码，再创建新分段，防止获取到空代码
        previous_code_str = self._db.get_latest_cumulative_code(self._active_workspace)

        self._current_segment = self._db.create_segment(self._active_workspace, prompt)
        self._load_history()

        self.generate_btn.setEnabled(False)

        settings = RenderSettings(
            width=self.width_input.value(),
            height=self.height_input.value(),
            fps=self.fps_input.value(),
            quality=self.quality_input.currentText(),
        )
        previous_code = previous_code_str
        ai_settings = AISettings(
            deepseek_api_key=self.deepseek_key.text().strip(),
            deepseek_base_url=self.deepseek_base.text().strip(),
            deepseek_model=self.deepseek_model.text().strip(),
            gemini_api_key=self.gemini_key.text().strip(),
            gemini_model=self.gemini_model.text().strip(),
        )
        self._log(
            f"输出设置: {settings.width}x{settings.height} @ {settings.fps}fps | 质量 {settings.quality}"
        )
        self._log(f"AI 选择模式: {self.ai_mode_input.currentText()}")
        self._log(f"分段索引: {self._current_segment.segment_index}")

        segment_dir = self._active_job_dir
        segment_dir.mkdir(parents=True, exist_ok=True)

        ai_mode_text = self.ai_mode_input.currentText()
        ai_mode = {
            "DeepSeek": "deepseek",
            "Gemini": "gemini",
        }.get(ai_mode_text, "deepseek")
        if ai_mode == "deepseek" and not ai_settings.deepseek_model:
            QMessageBox.warning(self, "提示", "必须指定 DeepSeek 模型")
            self.generate_btn.setEnabled(True)
            return
        if ai_mode == "gemini" and not ai_settings.gemini_model:
            QMessageBox.warning(self, "提示", "必须指定 Gemini 模型")
            self.generate_btn.setEnabled(True)
            return
        worker = RenderWorker(ai_settings, ai_mode, prompt, previous_code, settings, segment_dir)
        self._current_worker = worker
        worker.started.connect(lambda: self.status.showMessage("任务开始..."))
        worker.progress.connect(self.status.showMessage)
        worker.progress.connect(self._log)
        worker.started.connect(lambda: self._log("渲染线程已启动"))
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_finished)
        self._worker_thread = start_worker(worker)
        self._log("渲染线程已启动请求已发送")

    def _on_failed(self, message: str) -> None:
        QMessageBox.critical(self, "错误", message)
        self.status.showMessage("任务失败", 3000)
        self._log(f"任务失败: {message}")
        
        # 删除失败的会话记录
        if self._current_segment is not None:
            self._db.delete_segment(self._current_segment.id)
            self._load_history()
            self._log("已删除失败的会话记录")
        
        self.generate_btn.setEnabled(True)
        self._current_worker = None
        self._current_segment = None

    def _on_finished(self, result: TaskResult) -> None:
        self.status.showMessage("开始播放")
        self._log(f"渲染完成，输出: {result.render_result.video_path}")
        self._log(f"分段视频: {len(result.render_result.section_videos)} 个")
        
        if self._current_segment is not None:
            # 第一轮播放全帧视频，其余轮播放分段
            if self._current_segment.segment_index == 0:
                section_video_path = str(result.render_result.video_path)
            else:
                section_video_path = ""
                if result.render_result.section_videos:
                    sorted_videos = sorted(result.render_result.section_videos, key=lambda p: p.name)
                    idx = self._current_segment.segment_index
                    if idx < len(sorted_videos):
                        section_video_path = str(sorted_videos[idx])
                    else:
                        section_video_path = str(sorted_videos[-1])

            self._db.update_segment_render(
                self._current_segment.id,
                result.manim_code,
                section_video_path,
            )
            self._load_history()

            # 播放当前分段
            if section_video_path and Path(section_video_path).exists():
                updated_segment = Segment(
                    id=self._current_segment.id,
                    workspace=self._current_segment.workspace,
                    segment_index=self._current_segment.segment_index,
                    input_text=self._current_segment.input_text,
                    cumulative_code=result.manim_code,
                    section_video_path=section_video_path,
                    created_at=self._current_segment.created_at,
                )
                self._play_segment(updated_segment)
            else:
                self._log(f"未找到分段 #{{self._current_segment.segment_index}} 对应的视频")
        
        self.generate_btn.setEnabled(True)
        self._current_worker = None
        self._current_segment = None

    def _play_segment(self, segment: Segment) -> None:
        """播放单个分段视频"""
        if not segment.section_video_path:
            self._log(f"分段 #{segment.segment_index} 没有视频")
            return
        video_path = Path(segment.section_video_path)
        if not video_path.exists():
            self._log(f"分段 #{segment.segment_index} 视频文件不存在")
            return
        self._log(f"播放分段 #{segment.segment_index}")
        self._play_video_file(video_path)

    def _play_video_file(self, file_path: Path) -> None:
        if not file_path.exists():
            self._log("视频文件不存在，无法播放")
            return
        self._reset_playback_state()
        self._playback_active = True
        self._ui_state.current_video = file_path
        self.player.show_video()
        self.player_backend.setSource(QUrl.fromLocalFile(str(file_path)))
        self.player_backend.play()

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if not self._playback_active:
                return
            if self._ui_state.last_frame is None:
                self._capture_current_frame()
            if self._ui_state.last_frame:
                self.player.show_last_frame(self._ui_state.last_frame)
                self.player_backend.stop()
                self.player_backend.setSource(QUrl())
                self._ui_state.current_video = None
                self._playback_active = False
                self.status.showMessage("播放结束，已定格最后一帧", 3000)
                self._log("播放结束，已定格最后一帧")
            else:
                self._log("播放结束，无最后一帧可显示")

    def _reset_playback_state(self) -> None:
        self.player_backend.stop()
        self.player_backend.setSource(QUrl())
        self._play_queue = []
        self._ui_state.last_frame = None
        self._ui_state.current_video = None
        self._playback_active = False

    def _on_video_frame(self, frame) -> None:
        if not self._playback_active:
            return
        current = self._ui_state.current_video
        if current is None:
            return
        source = self.player_backend.source()
        if source != QUrl.fromLocalFile(str(current)):
            return
        if frame.isValid():
            image = frame.toImage()
            if not image.isNull():
                self._ui_state.last_frame = image.copy()

    def _capture_current_frame(self) -> None:
        video_sink = self.player.video_widget.videoSink()
        if video_sink is None:
            return
        try:
            frame = video_sink.videoFrame()
        except AttributeError:
            return
        if frame is None or not frame.isValid():
            return
        image = frame.toImage()
        if image.isNull():
            return
        self._ui_state.last_frame = image.copy()


def run_app(db: Database, jobs_dir: Path) -> None:
    app = QApplication([])
    
    # 应用夜间主题
    Theme.apply(app)
    
    window = MainWindow(db, jobs_dir)
    window.show()
    app.exec()
