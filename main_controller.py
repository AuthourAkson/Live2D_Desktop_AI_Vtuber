import subprocess, json
import threading, requests
import base64
import io
import numpy as np
import soundfile as sf
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from ollama import Client
from tts.tts_controller import speak_text
from tts.config import config
from asr.asr_factory import ASRFactory
from asr.asr_interface import ASRInterface

#对话控制中心，处理LLM逻辑与信号中转
class ChatController(QObject):
    response_updated = pyqtSignal(str)
    mmd_mouth_updated = pyqtSignal(float)
    mmd_action_triggered = pyqtSignal(str)

    def __init__(self, chara_model: str, asr_system: ASRInterface = None, parent=None):
        super().__init__(parent)
        
        self.chara_model = chara_model
        self.asr_system = asr_system
        self.use_ollama = config.get("USE_OLLAMA", True)
        self.use_custom_api = config.get("USE_CUSTOM_API", False)

        #优先初始化自定义API配置
        if self.use_custom_api:
            self.api_url = config.get("CUSTOM_API_URL")
            self.api_key = config.get("CUSTOM_API_KEY")
            self.custom_api_model = config.get("CUSTOM_API_MODEL")
            if not self.api_url:
                print("警告:已启用自定义API但未配置CUSTOM_API_URL。")
        elif self.use_ollama:
            #默认连接本地11434端口的Ollama服务
            self.model_name = config.get("OLLAMA_MODEL", "qwen2.5:latest")
            self.client = Client(host="http://localhost:11434")
        else:
            print("警告:Ollama和自定义API都未启用。")
            self.client = None

        #载入角色人设Prompt
        self.system_prompt = self._load_prompt("prompt/Amiya.txt")
        self.chat_history = []

    @pyqtSlot(str)
    def send_response(self, message):
        #通用文字信号转发
        self.response_updated.emit(message)

    @pyqtSlot(float)
    def send_mouth_value(self, value):
        #处理口型数据，live2d通过指令前缀区分，mmd使用独立信号
        if self.chara_model in ["mmd", "vrm"]:
            self.mmd_mouth_updated.emit(value)
        else:
            self.response_updated.emit(f"__MOUTH__:{value}")

    def _load_prompt(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def ask(self, user_input):
        #请求LLM并管理对话上下文
        if not self.use_ollama and not self.use_custom_api:
            return "[Ollama和自定义API都未启用]"

        messages = [{"role": "system", "content": self.system_prompt}] if self.system_prompt else []
        messages += self.chat_history + [{"role": "user", "content": user_input}]

        reply = ""
        #方案一：OpenAI兼容格式的自定义API
        if self.use_custom_api:
            if not self.api_url:
                return "[自定义API URL未配置]"
            try:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                payload = {
                    "model": self.custom_api_model,
                    "messages": messages
                }

                response = requests.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                api_response = response.json()
                reply = api_response["choices"][0]["message"]["content"]
            except requests.exceptions.RequestException as e:
                print(f"自定义API请求失败: {e}")
                return f"[自定义API请求失败: {e}]"
            except KeyError as e:
                print(f"解析自定义API响应失败: 缺少键{e}")
                return "[解析自定义API响应失败]"
        #方案二：本地Ollama服务
        elif self.use_ollama:
            try:
                response = self.client.chat(model=self.model_name, messages=messages)
                reply = response["message"]["content"]
            except Exception as e:
                print(f"Ollama请求失败: {e}")
                return f"[Ollama请求失败: {e}]"

        if reply:
            #更新历史记录以维持短期记忆
            self.chat_history.append({"role": "user", "content": user_input})
            self.chat_history.append({"role": "assistant", "content": reply})
            #触发前端UI更新显示AI回复
            self.send_response(reply)
            
            #特定角色动作联动（仅MMD/VRM模型支持）
            if self.chara_model in ["mmd", "vrm"]:
                if "你好" in reply:
                    self.mmd_action_triggered.emit("greeting")
            
            #调用TTS引擎播放语音并同步触发口型回调
            speak_text(reply, mouth_callback=self.send_mouth_value)
            return reply
        else:
            return "[未获取到有效回复]"