import os
import webview
from src.core.sum_thread import ThreadManager
from src.ui.view.based_ui import MascotApi

# 透明窗口所需参数（无 --incognito，无强制杀进程）
os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = (
    '--disable-features=CalculateNativeWinOcclusion '
    '--enable-transparent-visuals '
    '--enable-blink-features=WebGLAlpha,Accelerated2dCanvas '
    '--disable-gpu-vsync'
)

if __name__ == "__main__":
    core = ThreadManager()
    ui_api = MascotApi()
    HTTP_PORT = 8111

    window = webview.create_window(
        '桌宠助手',
        url=f'http://127.0.0.1:{HTTP_PORT}/pyweb.html',
        js_api=ui_api,
        width=360, height=500,
        frameless=True,
        transparent=True,
        easy_drag=False,
        on_top=True,
    )

    ui_api.set_window(window)

    webview.start(gui='edgechromium')
