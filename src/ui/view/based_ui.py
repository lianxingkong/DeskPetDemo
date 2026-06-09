import base64
import ctypes
import json
import os
import tempfile
import time

import webview
from loguru import logger

from src.services.voice_recognize import AsyncVoiceRecorder
from src.ui.config import ui_setting
from src.core.sum_thread.thread_connect import ThreadManager

import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler


class MascotApi:
    def __init__(self):
        self.replay_msg = None
        self._window = None
        ThreadManager()._on_callback(self.show_reply)   # 入队

    def set_window(self, window):
        self._window = window

    def move_by(self, dx, dy):
        """拖动移动逻辑"""
        if self._window:
            self._window.move(self._window.x + dx, self._window.y + dy)

    def close_window(self):
        """关闭窗口"""
        if self._window:
            ThreadManager().cleanup()
            self._window.destroy()

    def process_text(self, text):
        """获取接收到的文本"""
        print(f"收到文本: {text}")
        # ★ 修改：传入 false，告诉前端这是普通消息，不要追加到 AI 的气泡里
        self._window.evaluate_js(f"addReply('收到：{text}', false)")
        ThreadManager().send_text_to_queue(text)

    def show_reply(self, text):
        """将后端的返回结果推送到前端 UI 显示"""
        if not self._window:
            logger.warning("Window 未初始化，无法显示回复")
            return

        if text is None:
            # 返回None说明结束信号
            self._window.evaluate_js('endStream()')

        js_safe_text = json.dumps(text, ensure_ascii=False)

        # 调用前端写好的 addReply 函数
        self._window.evaluate_js(f"addReply({js_safe_text}, true)")


    def get_mouse_relative_pos(self):
        try:
            # 1. 获取屏幕上的绝对物理坐标
            cursor = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))

            # 2. 处理 Windows DPI 缩放问题
            # 尝试获取窗口底层句柄的 DPI 缩放比
            scale_factor = 1.0
            try:
                hwnd = self._window.gui.hwnd
                if hwnd:
                    dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
                    scale_factor = dpi / 96.0
            except Exception:
                pass  # 如果获取失败，默认为 1.0

            # 3. 将物理像素转换为逻辑像素 (与 pywebview 的 window.x/y 对齐)
            logical_x = cursor.x / scale_factor
            logical_y = cursor.y / scale_factor

            # 4. 计算相对于窗口左上角的坐标
            rel_x = logical_x - self._window.x
            rel_y = logical_y - self._window.y

            return rel_x, rel_y
        except Exception:
            return None, None

    def pick_image(self):
        """点击确定时，调用 pywebview 原生文件框选择图片"""
        if not self._window:
            return

        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=('Image Files (*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp)',),
        )

        if result and len(result) > 0:
            file_path = result[0]
            logger.info(f"选择了图片: {file_path}")
            # 将路径推送到前端显示预览
            self._window.evaluate_js(f"setImagePreview('{file_path}')")

            # ★ TODO: 将路径送入你的业务队列
            ThreadManager().send_image_to_queue(file_path)

    def process_dropped_image(self, base64_data):
        """处理前端拖拽或粘贴过来的 Base64 图片，保存为本地文件并返回路径"""
        try:
            # 解析 Base64 (格式: data:image/png;base64,xxxxx)
            header, encoded = base64_data.split(",", 1)

            # 提取图片后缀
            ext = ".png"
            if "image/jpeg" in header:
                ext = ".jpg"
            elif "image/gif" in header:
                ext = ".gif"
            elif "image/webp" in header:
                ext = ".webp"

            # 生成临时文件路径
            temp_dir = tempfile.gettempdir()
            file_name = f"pet_paste_{int(time.time())}{ext}"
            file_path = os.path.join(temp_dir, file_name).replace("\\", "/")

            # 解码并保存
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(encoded))

            logger.info(f"拖拽/粘贴图片已保存至: {file_path}")

            # 将路径推送到前端显示预览
            self._window.evaluate_js(f"setImagePreview('{file_path}')")

            # ★ TODO: 将路径送入你的业务队列
            ThreadManager().send_image_to_queue(file_path)

        except Exception as e:
            logger.error(f"处理拖拽图片失败: {e}")

    def handle_voice(self, audio_data):
        """录音完成，拿到 numpy 数组"""
        ThreadManager().send_voice_to_queue(audio_data)

    def send_voice(self):
        """前端语音模式下点击确定按钮触发"""
        self.start_recording()

    def start_recording(self):
        """启动录音功能"""
        # 防止重复点击：如果正在录音，则直接返回
        if hasattr(self, 'recorder') and self.recorder and self.recorder.is_recording:
            print("正在录音中，请勿重复操作")
            return
        print("开始录音")
        self._window.evaluate_js('setVoiceStatus("录音中...")')
        self.recorder = AsyncVoiceRecorder(
            duration=5,
            on_data_ready = self.handle_voice,
        )
        self.recorder.start_recording()  # 非阻塞，5秒后自动停止并回调数据


# ★ 修正：用自定义 Handler 指定目录，不用 os.chdir
class ResourceHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ui_setting.ui.RESOURCES_DIR, **kwargs)

    def log_message(self, format, *args):
        pass  # 静默日志


def start_http_server():
    HTTP_PORT = ui_setting.ui.HTTP_PORT
    server = HTTPServer(('127.0.0.1', HTTP_PORT), ResourceHandler)
    print(f"HTTP 服务器启动: http://127.0.0.1:{HTTP_PORT}/")
    print(f"服务目录: {ui_setting.ui.RESOURCES_DIR}")
    server.serve_forever()


# 后台启动 HTTP 服务器
server_thread = threading.Thread(target=start_http_server, daemon=True)
server_thread.start()
