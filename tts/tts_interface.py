import abc
import os
from playsound3 import playsound


class TTSInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def generate_audio(self, text: str, file_name_no_ext=None):
        """
        使用 TTS 引擎生成语音音频文件。
        
        参数:
            text (str): 要转换为语音的文本
            file_name_no_ext (可选): 音频文件的名称（不含扩展名）

        返回:
            str: 生成的音频文件路径
        """
        raise NotImplementedError

    def remove_file(self, filepath: str, verbose: bool = True) -> None:
        """
        删除指定路径的音频文件。

        该方法被单独抽出，因为并非所有播放方式都在 play_audio_file_local() 中进行。
        用于播放完成后清理缓存文件。

        参数:
            filepath (str): 要删除的文件路径
            verbose (bool): 是否在控制台输出日志信息
        """
        if not os.path.exists(filepath):
            print(f"文件 {filepath} 不存在")
            return
        try:
            print(f"正在删除文件 {filepath}") if verbose else None
            os.remove(filepath)
        except Exception as e:
            print(f"删除文件 {filepath} 失败：{e}")

    def play_audio_file_local(self, audio_file_path: str) -> None:
        """
        在本地设备上播放音频文件（不发送到前端）。

        参数:
            audio_file_path (str): 要播放的音频文件路径
        """
        playsound(audio_file_path)
