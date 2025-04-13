from tts.tts_workspace import TTSFactory
from tts.config import config
from pydub import AudioSegment
from pydub.utils import make_chunks
import subprocess
import time

# 读取当前使用的 TTS 类型
engine_type = config["TTS_MODEL"]
# 读取该类型对应的参数字段
engine_config = config.get(engine_type, {})
# 初始化 TTS 引擎
tts_engine = TTSFactory.get_tts_engine(engine_type, **engine_config)

def speak_text(text, mouth_callback=None):
    audio_path = tts_engine.generate_audio(text)

    if mouth_callback:
        volume_sequence = get_volume_sequence(audio_path)
        # 播放语音
        subprocess.Popen(["mpv", audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # 同步嘴部动作（根据音量）
        for v in volume_sequence:
            mouth_callback(v)  # 直接调用传入的嘴型更新函数
            time.sleep(0.05)  # 大约在是 20 FPS
    else:
        tts_engine.play_audio_file_local(audio_path)

def get_volume_sequence(audio_path, chunk_ms=50):
    audio = AudioSegment.from_file(audio_path)
    chunks = make_chunks(audio, chunk_ms)
    amplify = config.get("MOUTH_AMPLIFY", 1.8) #从config中直接获取嘴型增益，可自行再config.yaml中更改
    rms_sequence = [min(chunk.rms / 32768 * amplify, 1.0) for chunk in chunks]  # 归一化且不超1
    return rms_sequence