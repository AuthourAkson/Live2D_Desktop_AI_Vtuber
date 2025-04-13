import sys
import os
import time
from tts.config import config
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from main_controller import ChatController
from ui.mouth_controller import MouthController
from PyQt6.QtCore import Qt, QUrl,pyqtSignal, QTimer, QPoint,QObject
from PyQt6.QtGui import QCursor



class Live2DWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 400, 600)

        self.view = QWebEngineView()
        self.view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.view.setStyleSheet("background: transparent;")

        local_path = os.path.abspath("live2d/live2d_web/index.html")
        print("加载路径：", local_path)
        self.view.load(QUrl.fromLocalFile(local_path))


        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 添加拖动层
        self.overlay = DraggableOverlay(self)
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        self.overlay.raise_()

        if config.get("USE_OLLAMA", False):
            model_name = config.get("OLLAMA_MODEL", "qwen2.5:latest")
        else:
            model_name = None
        self.chat_controller = ChatController()

        # 配置 WebChannel
        self.channel = QWebChannel(self)
        self.channel.registerObject('chatController', self.chat_controller)
        self.mouse_tracker = MouseTracker(self)
        self.channel.registerObject("mouseTracker", self.mouse_tracker)
        self.view.page().setWebChannel(self.channel)
        
        self.mouth_sync = MouthController()  # 同步嘴部动作
        self.channel.registerObject("mouthSync", self.mouth_sync)
        # QtWebChannel注册部件，上面的过程同理
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(0, 0, self.width(), self.height())

class DraggableOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        self._old_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.window().move(self.window().pos() + delta)
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._old_pos = None

class MouseTracker(QObject):
    mouseMoved = pyqtSignal(int, int)

    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window  # 传入主窗口
        self.timer = QTimer()
        self.timer.timeout.connect(self.track_mouse)
        self.timer.start(16)  # 约 60 FPS

    def track_mouse(self):
        if self.parent_window is None:
            return
        global_pos = QCursor.pos()
        relative_pos = global_pos - self.parent_window.geometry().topLeft()
        self.mouseMoved.emit(relative_pos.x(), relative_pos.y())
