import sys
import os
import time
import yaml
import numpy as np
import torch
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer, QObject, QThread, pyqtSlot
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtGui import QCursor

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from asr.asr_factory import ASRFactory
from tts.tts_workspace import TTSFactory
from tts.config import config
from main_controller import ChatController
from ui.mouth_controller import MouthController

#配置文件监听处理器，实现热重载的核心
class ConfigFileHandler(FileSystemEventHandler, QObject):
    config_changed = pyqtSignal()

    def on_modified(self, event):
        #只关心config.yaml的变动
        if not event.is_directory and event.src_path.endswith("config.yaml"):
            self.config_changed.emit()

#后端异步任务执行器，负责ASR识别和LLM请求
class Worker(QObject):
    finished = pyqtSignal(str)

    def __init__(self, asr_system, chat_controller, tts_engine):
        super().__init__()
        self.asr_system = asr_system
        self.chat_controller = chat_controller
        self.tts_engine = tts_engine

    @pyqtSlot(np.ndarray)
    def process_audio(self, full_audio):
        try:
            print(f"🎤正在后台处理语音...")
            text = self.asr_system.transcribe_np(full_audio)
            if not text:
                self.finished.emit("⚠️未检测到语音输入")
                return
            print(f"📝识别结果: {text}")
            #通知终端和前端UI显示识别文字
            self.finished.emit(text)
            #请求AI回复，这里内部会触发TTS和口型信号
            reply = self.chat_controller.ask(text)
        except Exception as e:
            print(f"❌Worker错误: {e}")
            self.finished.emit(f"❌错误: {e}")

#音频流处理器，集成VAD静音检测
class AudioHandler(QObject):
    audio_processed = pyqtSignal(np.ndarray)
    def __init__(self):
        super().__init__()
        self.sampling_rate = 16000
        self.speech_start_time = None
        self.speech_end_time = None
        self.audio_buffer = []
        #本地加载Silero VAD模型，force_reload设为False提升启动速度
        self.vad_model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False)

    @pyqtSlot(list)
    def processAudio(self, audio_data_list):
        audio_chunk = np.array(audio_data_list, dtype=np.float32)
        #VAD要求输入必须是特定长度的Tensor
        audio_tensor = torch.from_numpy(audio_chunk).unsqueeze(0)
        with torch.no_grad():
            speech_prob = self.vad_model(audio_tensor, self.sampling_rate).item()
        self.audio_buffer.append(audio_chunk)
        #判断是否正在说话
        if speech_prob > 0.5:
            if self.speech_start_time is None: self.speech_start_time = time.time()
            self.speech_end_time = time.time()
        else:
            #如果检测到停顿超过0.5秒，判定为一句话结束
            if self.speech_start_time is not None and (time.time() - self.speech_end_time > 0.5):
                full_audio = np.concatenate(self.audio_buffer)
                self.audio_processed.emit(full_audio)
                self.speech_start_time = None
                self.audio_buffer = []

#窗口拖拽控制器，解决无边框窗口移动问题
class WindowController(QObject):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.old_pos = None

    @pyqtSlot()
    def start_drag(self): self.old_pos = QCursor.pos()
    @pyqtSlot()
    def end_drag(self): self.old_pos = None
    @pyqtSlot()
    def drag(self):
        if self.old_pos:
            delta = QCursor.pos() - self.old_pos
            self.parent_window.move(self.parent_window.pos() + delta)
            self.old_pos = QCursor.pos()

#鼠标位置追踪，让模型视线跟随
class MouseTracker(QObject):
    mouseMoved = pyqtSignal(int, int)
    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        self.timer = QTimer()
        self.timer.timeout.connect(self.track_mouse)
        self.timer.start(16)#约60帧每秒的频率
    def track_mouse(self):
        if self.parent_window:
            global_pos = QCursor.pos()
            #计算相对于窗口左上角的坐标传给前端
            relative_pos = global_pos - self.parent_window.geometry().topLeft()
            self.mouseMoved.emit(relative_pos.x(), relative_pos.y())

#主窗体类，负责所有组件的调度
class Live2DWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #强制开启麦克风权限标识
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--use-fake-ui-for-media-stream"
        #1.窗口基础设置：置顶、无边框、工具栏属性防止任务栏占位
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 400, 600)
        
        #2.WebView配置：透明背景与跨域访问权限
        self.view = QWebEngineView()
        self.view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        settings = self.view.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        #3.确定模型路径并加载HTML
        self.chara_model = config.get("CHARA_MODEL", "live2d").lower()
        base_folder = "mmd_web" if self.chara_model in ["vrm", "mmd"] else "live2d_web"
        local_path = os.path.abspath(f"live2d/{base_folder}/index.html")
        self.view.load(QUrl.fromLocalFile(local_path))
        self.view.loadFinished.connect(self.on_load_finished)
        
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        #4.启动后端子系统
        self.init_backend_systems()

        #5.建立JS与Python的桥梁
        self.setup_web_channel()

        #6.热更新模块初始化
        self.setup_config_observer()

    def init_backend_systems(self):
        try:
            self.asr_system = ASRFactory.get_asr_system(config["ASR_MODEL"], **config.get(config["ASR_MODEL"], {}))
        except Exception as e:
            print(f"ASR初始化失败: {e}")
            self.asr_system = None
        
        self.chat_controller = ChatController(chara_model=self.chara_model, asr_system=self.asr_system)
        self.tts_engine = TTSFactory.get_tts_engine(config["TTS_MODEL"], **config.get(config["TTS_MODEL"], {}))
        self.audio_handler = AudioHandler()
        self.mouth_sync = MouthController()

        #将耗时的Worker放到独立线程防止界面卡死
        self.worker_thread = QThread()
        self.worker = Worker(self.asr_system, self.chat_controller, self.tts_engine)
        self.worker.moveToThread(self.worker_thread)
        self.audio_handler.audio_processed.connect(self.worker.process_audio)
        self.worker.finished.connect(self.handle_asr_result)
        self.worker_thread.start()

    def setup_web_channel(self):
        self.channel = QWebChannel(self)
        self.window_controller = WindowController(self)
        self.mouse_tracker = MouseTracker(self)
        
        #注册的对象可在前端js中通过channel.objects访问
        self.channel.registerObject('chatController', self.chat_controller)
        self.channel.registerObject('audioHandler', self.audio_handler)
        self.channel.registerObject("windowController", self.window_controller)
        self.channel.registerObject("mouseTracker", self.mouse_tracker)
        self.channel.registerObject("mouthSync", self.mouth_sync)
        self.view.page().setWebChannel(self.channel)

    def setup_config_observer(self):
        self.config_handler = ConfigFileHandler()
        self.config_handler.config_changed.connect(self.on_config_modified)
        
        self.observer = Observer()
        self.observer.schedule(self.config_handler, path=".", recursive=False)
        self.observer.start()

        #500ms防抖逻辑，避免保存文件时产生的多次重复触发
        self.reload_timer = QTimer()
        self.reload_timer.setSingleShot(True)
        self.reload_timer.timeout.connect(self.reload_config_and_model)

    def on_config_modified(self):
        self.reload_timer.start(500)

    def reload_config_and_model(self):
        print("🔄检测到配置文件变化，正在尝试热重载模型...")
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                new_conf = yaml.safe_load(f)
            
            model_name = new_conf.get("live2d_model", "")
            if model_name:
                model_path = f"model/{model_name}/{model_name}.model3.json"
                #直接向前端发送JS代码执行模型切换
                self.view.page().runJavaScript(f"window.changeModel('{model_path}');")
                print(f"✅已下发切换指令: {model_name}")
        except Exception as e:
            print(f"❌读取配置文件失败: {e}")

    def on_load_finished(self, ok):
        if not ok: return
        #页面初次加载完成后，根据配置载入对应模型
        model_name = config.get("live2d_model", "")
        if self.chara_model == "live2d" and model_name:
            path = f"model/{model_name}/{model_name}.model3.json"
            self.view.page().runJavaScript(f"window.changeModel('{path}');")
        elif self.chara_model == "vrm":
            self.view.page().runJavaScript(f"window.loadModel('vrm', '{config.get('VRM_MODEL_PATH','')}');")

    def handle_asr_result(self, text):
        #将识别结果通过信号转发，触发终端/UI更新
        #self.chat_controller.response_updated.emit(text)
        pass

    def closeEvent(self, event):
        #退出前必须清理线程和观察者，否则进程无法正常结束
        self.observer.stop()
        self.observer.join()
        self.worker_thread.quit()
        self.worker_thread.wait()
        event.accept()