import requests
import json
import os
from pathlib import Path
from pydub import AudioSegment
from pydub.playback import play
from tts.tts_interface import TTSInterface

class VoiceVoxTTS(TTSInterface):
    def __init__(self, speaker=1, speed=1.0, pitch=0.0):
        self.speaker = speaker
        self.speed = speed
        self.pitch = pitch
        self.url = self._detect_voicevox_url()

        # 语音文件缓存目录
        self.audio_dir = "/temp"
        os.makedirs(self.audio_dir, exist_ok=True)

    def _detect_voicevox_url(self) -> str:
        for port in [50021, 50025]:
            url = f"http://localhost:{port}"
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    print(f"✅ 连接 VoiceVox: {url}")
                    return url
            except requests.exceptions.RequestException:
                continue
        raise RuntimeError("❌ VoiceVox 没有启动qwq,请检查是否安装并启动了 VoiceVox")

    def generate_audio(self, text: str, file_name_no_ext=None) -> str:
        if file_name_no_ext is None:
            file_name_no_ext = "output"
        file_path = str(Path(self.audio_dir) / f"{file_name_no_ext}.wav")

        # 1. 创建 audio_query
        query_response = requests.post(
            f"{self.url}/audio_query",
            params={"text": text, "speaker": self.speaker}
        )
        if query_response.status_code != 200:
            raise RuntimeError("❌ audio_query 失败")

        query = query_response.json()
        query["speedScale"] = self.speed
        query["pitchScale"] = self.pitch

        # 2. 合成语音
        synth_response = requests.post(
            f"{self.url}/synthesis",
            headers={"Content-Type": "application/json"},
            params={"speaker": self.speaker},
            data=json.dumps(query)
        )
        if synth_response.status_code != 200:
            raise RuntimeError("❌合成失败")

        with open(file_path, "wb") as f:
            f.write(synth_response.content)

        return file_path

    def play_audio_file_local(self, audio_file_path: str):
        audio = AudioSegment.from_file(audio_file_path)
        play(audio)

    def generate_audio_from_file(self, text_file: str, output_file: str = "output.wav"):
        with open(text_file, "r", encoding="utf-8") as f:
            text = f.read()
        audio_path = self.generate_audio(text, Path(output_file).stem)
        return audio_path