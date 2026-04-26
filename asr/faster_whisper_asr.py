import numpy as np
from faster_whisper import WhisperModel
from .asr_interface import ASRInterface

class VoiceRecognition(ASRInterface):
    def __init__(
        self,
        model_path: str = "large-v3",
        download_root: str = None,
        language: str = "zh",
        device: str = "cuda"
    ) -> None:
        self.model = WhisperModel(
            model_path,
            device=device,
            compute_type="float16" if device == "cuda" else "int8",
            download_root=download_root
        )
        self.language = language

    def transcribe_np(self, audio: np.ndarray) -> str:
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5
        )

        text = "".join([seg.text for seg in segments]).strip()
        return text
