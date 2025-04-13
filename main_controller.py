import subprocess
import json
import threading
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from ollama import Client

from tts.tts_controller import speak_text
from tts.config import config

class ChatController(QObject):  # 必须继承自 QObject
    response_updated = pyqtSignal(str)

    def __init__(self, parent=None):  # 添加 parent 参数
        super().__init__(parent)       # 必须调用父类初始化

        self.use_ollama = config.get("USE_OLLAMA", True)
        self.model_name = config.get("OLLAMA_MODEL", "qwen2.5:latest")
        self.client = Client(host="http://localhost:11434") if self.use_ollama else None

        self.system_prompt = self._load_prompt("prompt/Amiya.txt")
        self.chat_history = []

    # 添加的pyqtSlot 装饰器
    @pyqtSlot(str)
    def send_response(self, message):
        self.response_updated.emit(message)

    @pyqtSlot(float)
    def send_mouth_value(self, value):
        self.response_updated.emit(f"__MOUTH__:{value}")# 发送嘴部同步数据

    def _load_prompt(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def ask(self, user_input):
        if not self.use_ollama:
            return "[Ollama 未启用]"

        messages = [{"role": "system", "content": self.system_prompt}] if self.system_prompt else []
        messages += self.chat_history + [{"role": "user", "content": user_input}]

        response = self.client.chat(model=self.model_name, messages=messages)
        reply = response["message"]["content"]

        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": reply})
        # 使用统一接口播放语音（包含嘴部同步）
        self.send_response(reply)
        speak_text(reply, mouth_callback=self.send_mouth_value)
        return reply
    

