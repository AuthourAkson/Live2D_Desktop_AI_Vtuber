import sys
import threading
from PyQt6.QtWidgets import QApplication
from ui.main_window import Live2DWindow

def input_thread(window):
    print("\n--- 系统已就绪 ---")
    while True:
        #这里依然保持原样，它是阻塞的
        user_input = input("你说：")
        
        if user_input.strip():
            #异步调用，不在这里直接print
            window.chat_controller.ask(user_input)

def print_ai_reply(message):
    """
    终端显示 AI 回复的逻辑
    """
    #过滤掉口型指令，这东西没必要在终端刷屏
    if message.startswith("__MOUTH__"):
        return
    
    #\r 让光标回到行首
    #打印一串空格把原本的 "你说：" 覆盖掉
    #再次 \r 回到行首打印 AI 的话
    #最后留一个换行，这样 input() 线程下一轮的 "你说：" 就会自动出现在新的一行
    #原本在语音识别里main_window.py中也有一套逻辑回复的逻辑，就直接搬到这里来了不会再重复
    sys.stdout.write("\r" + " " * 20 + "\r") 
    sys.stdout.write(f"🤖 AI回复：{message}\n")
    sys.stdout.flush()

def on_model_reloaded():
    # 模型重载时的提示也按这个逻辑走
    sys.stdout.write("\r" + " " * 30 + "\r")
    sys.stdout.write("🔄 系统：检测到 config.yaml 变更，模型已重载\n")
    sys.stdout.flush()

def main():
    app = QApplication(sys.argv)
    window = Live2DWindow()
    
    #绑定信号
    window.chat_controller.response_updated.connect(print_ai_reply)
    window.config_handler.config_changed.connect(on_model_reloaded)

    window.show()

    #启动输入线程
    t = threading.Thread(target=input_thread, args=(window,), daemon=True)
    t.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()