from PyQt6.QtCore import QObject, pyqtSignal

class MouthController(QObject):
    updateMouth = pyqtSignal(float)  # 发送单个音量值（帧）

    def send_mouth_value(self, value: float):
        self.updateMouth.emit(value)
