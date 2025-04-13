import sys
import threading
from PyQt6.QtWidgets import QApplication
from ui.main_window import Live2DWindow
import os

''' os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222" 此段用于在网页中调试'''
def input_thread(window):
    while True:
        user_input = input("你说：")
        if user_input.strip():
            # 调用控制器的实际方法
            reply = window.chat_controller.ask(user_input)
            window.chat_controller.send_response(reply)

def main():
    app = QApplication(sys.argv)
    window = Live2DWindow()
    window.show()

    # 启动输入线程
    threading.Thread(target=input_thread, args=(window,), daemon=True).start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()