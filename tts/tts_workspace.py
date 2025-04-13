from .tts_interface import TTSInterface
from typing import Type

'''该工作间用于创建TTS引擎实例,还有许多正在待创建中'''
class TTSFactory:
    @staticmethod
    def get_tts_engine(engine_type, **kwargs) -> Type[TTSInterface]:
        if engine_type == "AzureTTS":
            from .azureTTS import TTSEngine as AzureTTSEngine
            return AzureTTSEngine(kwargs.get("api_key"), kwargs.get("region"), kwargs.get("voice"))
        elif engine_type == "barkTTS":
            from .barkTTS import TTSEngine as BarkTTSEngine
            return BarkTTSEngine(kwargs.get("voice"))
        elif engine_type == "edgeTTS":
            from .edgeTTS import TTSEngine as EdgeTTSEngine
            return EdgeTTSEngine(kwargs.get("voice"))
        elif engine_type == "pyttsx3TTS":
            from .pyttsx3TTS import TTSEngine as Pyttsx3TTSEngine
            return Pyttsx3TTSEngine()
        elif engine_type == "cosyvoiceTTS":
            from .cosyvoiceTTS import TTSEngine as CosyvoiceTTSEngine
            return CosyvoiceTTSEngine(
                client_url=kwargs.get("client_url"),
                mode_checkbox_group=kwargs.get("mode_checkbox_group"),
                sft_dropdown=kwargs.get("sft_dropdown"),
                prompt_text=kwargs.get("prompt_text"),
                prompt_wav_upload_url=kwargs.get("prompt_wav_upload_url"),
                prompt_wav_record_url=kwargs.get("prompt_wav_record_url"),
                instruct_text=kwargs.get("instruct_text"),
                seed=kwargs.get("seed"),
                api_name=kwargs.get("api_name"),
            )
        elif engine_type == "meloTTS":
            from .meloTTS import TTSEngine as MeloTTSEngine
            return MeloTTSEngine(
                speaker=kwargs.get("speaker"),
                language=kwargs.get("language"),
                device=kwargs.get("device"),
                speed=kwargs.get("speed"),
            )
        elif engine_type == "voicevoxTTS":
            from .voicevoxTTS import VoiceVoxTTS
            instance = VoiceVoxTTS(
                speaker=kwargs.get("speaker", 1),
                speed=kwargs.get("speed", 1.0),
                pitch=kwargs.get("pitch", 0)
            )

            # ✅ 如果 `text_file` 参数存在，自动从文件转换语音
            text_file = kwargs.get("text_file")
            output_file = kwargs.get("output_file", "output.wav")
            if text_file:
                print(f"🔄 从文件 {text_file} 生成语音...")
                instance.generate_audio_from_file(text_file, output_file)

            return instance
        elif engine_type == "piperTTS":
            from .piperTTS import TTSEngine as PiperTTSEngine
            return PiperTTSEngine(voice_path=kwargs.get("voice_model_path"), verbose=kwargs.get("verbose"))
            
        else:
            raise ValueError(f"Unknown TTS engine type: {engine_type}")