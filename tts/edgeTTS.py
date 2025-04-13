import asyncio
import os
import subprocess
from edge_tts import Communicate
from .tts_interface import TTSInterface
from .config import config

class TTSEngine(TTSInterface):
    def __init__(self, voice=None):
        self.voice = voice or config["TTS_VOICE"]
        self.pitch = config.get("TTS_PITCH", "+0Hz")
        self.output_path = "tts/temp/output.mp3"
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    async def _speak_async(self, text, file_path):
        communicate = Communicate(text=text, voice=self.voice, pitch=self.pitch)
        await communicate.save(file_path)

    def generate_audio(self, text: str, file_name_no_ext=None):
        if file_name_no_ext:
            output_path = f"tts/temp/{file_name_no_ext}.mp3"
        else:
            output_path = self.output_path
        asyncio.run(self._speak_async(text, output_path))
        return output_path

    def play_audio_file_local(self, audio_file_path: str = None):
        path = audio_file_path or self.output_path
        try:
            subprocess.Popen(["mpv", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print("播放失败：", e)
