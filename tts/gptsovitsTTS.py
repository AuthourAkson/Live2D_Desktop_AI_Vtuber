import os,requests,subprocess,time,shutil
from typing import Optional, Callable
from .tts_interface import TTSInterface
from tts.config import config

GPT_SOVITS_REF_AUDIO_DIR = "D:/GPT-Sovits-Main/ref_audios"
os.makedirs(GPT_SOVITS_REF_AUDIO_DIR, exist_ok=True)

CLIENT_AUDIO_OUTPUT_DIR = "generated_audio"
os.makedirs(CLIENT_AUDIO_OUTPUT_DIR, exist_ok=True)


class TTSEngine(TTSInterface):
    def __init__(
        self,
        api_base_url: str,
        ref_audio_path: str,
        text_lang: str = "zh",
        prompt_lang: str = "zh",
        prompt_text: str = "",
        speed_factor: float = 1.0,
        **kwargs
    ):
        super().__init__()
        self.api_base_url = api_base_url
        self.client_original_ref_audio_path = ref_audio_path
        self.text_lang = text_lang
        self.prompt_lang = prompt_lang
        self.prompt_text = prompt_text
        self.speed_factor = speed_factor
        self.other_params = kwargs

        if not self.api_base_url:
            raise ValueError("GPT-SoVITS API URL 未配置。请检查 config.yaml 中的 'gptsovitsTTS.api_base_url'。")
        if not self.client_original_ref_audio_path:
            raise ValueError("GPT-SoVITS 参考音频路径未配置。请检查 config.yaml 中的 'gptsovitsTTS.ref_audio_path'。")
        if not os.path.exists(self.client_original_ref_audio_path):
            print(f"警告: 客户端原始参考音频文件不存在于路径: {self.client_original_ref_audio_path}。请检查路径或确保文件存在。")

    def convert_audio_to_wav(self, input_path, output_path):
        command = [
            "ffmpeg",
            "-i", input_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            output_path
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg 转换失败 ({input_path} -> {output_path})，错误码：{e.returncode}")
            return False
        except FileNotFoundError:
            print("错误:ffmpeg 命令未找到。请确保 FFmpeg 已安装并添加到系统 PATH 中。")
            return False
        except Exception as e:
            print(f"发生未知错误：{e}")
            return False

    def generate_audio(self, text: str) -> str:
        output_filename = os.path.join(CLIENT_AUDIO_OUTPUT_DIR, f"gptsovits_output_{int(time.time())}.wav")

        base_name = os.path.splitext(os.path.basename(self.client_original_ref_audio_path))[0]
        client_converted_ref_audio_path = os.path.join(CLIENT_AUDIO_OUTPUT_DIR, f"{base_name}_16k_mono.wav")

        if not os.path.exists(client_converted_ref_audio_path) or os.path.getmtime(self.client_original_ref_audio_path) > os.path.getmtime(client_converted_ref_audio_path):
            if not self.convert_audio_to_wav(self.client_original_ref_audio_path, client_converted_ref_audio_path):
                print("客户端参考音频转换失败，无法继续 GPT-SoVITS 合成。")
                return ""

        gpt_sovits_ref_audio_file = os.path.join(GPT_SOVITS_REF_AUDIO_DIR, os.path.basename(client_converted_ref_audio_path))

        try:
            shutil.copy2(client_converted_ref_audio_path, gpt_sovits_ref_audio_file)
        except Exception as e:
            print(f"复制参考音频文件到 GPT-SoVITS API 目录失败: {e}")
            return ""

        gpt_sovits_api_root = config.get("GPT_SOVITS_API_PATH", "D:/GPT-Sovits-Main")
        relative_path_for_api = os.path.relpath(gpt_sovits_ref_audio_file, gpt_sovits_api_root)
        relative_path_for_api = relative_path_for_api.replace("\\", "/")

        params = {
            "text": text,
            "text_lang": self.text_lang,
            "ref_audio_path": relative_path_for_api,
            "prompt_lang": self.prompt_lang,
            "speed_factor": self.speed_factor,
            "media_type": "wav",
            "streaming_mode": False,
            "prompt_text": self.prompt_text,
            **self.other_params
        }

        if not params["text"].strip():
            print("错误: 尝试发送给 GPT-SoVITS API 的文本为空，跳过请求。")
            return ""

        try:
            response = requests.post(self.api_base_url, json=params)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            #print(f"GPT-SoVITS API 返回的 Content-Type: '{content_type}'")
            
            if 'audio' in content_type:
                with open(output_filename, "wb") as f:
                    f.write(response.content)
                print(f"GPT-SoVITS 语音合成成功！保存为 {output_filename}")
                return output_filename
            else:
                print(f"GPT-SoVITS API 返回非音频内容。状态码: {response.status_code}，内容: {response.text}")
                return ""
        except requests.exceptions.RequestException as e:
            print(f"GPT-SoVITS API 请求失败: {e}")
            if e.response is not None:
                print(f"GPT-SoVITS API 返回状态码: {e.response.status_code}")
                print(f"GPT-SoVITS API 错误响应内容: {e.response.text}")
            return ""
        except Exception as e:
            print(f"GPT-SoVITS 合成过程中发生未知错误: {str(e)}")
            return ""

    def remove_file(self, filepath: str, verbose: bool = True) -> None:
        if not os.path.exists(filepath):
            #print(f"文件 {filepath} 不存在") 
            return
        try:
            #print(f"正在删除文件 {filepath}") if verbose else None 
            os.remove(filepath)
        except Exception as e:
            print(f"删除文件 {filepath} 失败：{e}")

    def play_audio_file_local(self, audio_file_path: str) -> None:
        if not os.path.exists(audio_file_path):
            print(f"错误: 音频文件 '{audio_file_path}' 不存在，无法播放。")
            return
        try:
            subprocess.run(["mpv", audio_file_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print("错误: mpv 播放器未找到。请确保 mpv 已安装并添加到系统 PATH 中。")
        except subprocess.CalledProcessError as e:
            print(f"播放音频失败: {e}")
        except Exception as e:
            print(f"播放器发生未知错误: {e}")

    def generate_audio_fragment(self, text: str, callback: Callable[[bytes], None]):
        audio_path = self.generate_audio(text)
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            callback(audio_data)
            self.remove_file(audio_path)
        else:
            print("生成音频失败，无法进行回调。")

    def stop(self):
        pass