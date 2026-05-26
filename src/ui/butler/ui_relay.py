from loguru import logger

class CommunicationButler:
    def __init__(self, view, core):
        self.view = view
        self.core = core

        self.pending_text_msg = ""
        self.pending_photo_desc = None
        self.init_check_status = 0
        self.init_voices_text = None

        # ===== 连接 View 发来的信号 =====
        self.view.text_input_confirmed.connect(self.handle_text_input)
        self.view.image_selected.connect(self.handle_image_input)
        self.view.voice_record_triggered.connect(self._on_voice_triggered)

        # ===== 连接 core Thread 返回的信号 =====
        # 文本 AI
        self.core.chat_worker.message_received.connect(self.on_ai_chunk_received)
        self.core.chat_worker.finished.connect(self.on_api_finished)
        # 记忆
        self.core.memory_worker.query_result.connect(self.on_memory_query_result)
        self.core.memory_worker.finished.connect(self.on_memory_finished)
        # 语音
        self.core.voice_worker.result_finished.connect(self._handle_transcribed_text)
        self.core.recorder_worker.recording_status.connect(self.view.show_system_message)
        # 图片
        self.core.photo_worker.img_finished.connect(self.handle_photo_result)

    def _on_voice_triggered(self):
        """UI按钮点击 -> 通知线程管理器开始录音"""
        self.view.voiceBotton.setEnabled(False)
        self.view.show_system_message("正在录音(5秒)...")
        # 触发 ThreadManager 的信号，子线程的录音器开始工作
        self.core.voice_record_triggered.emit()

    def _handle_transcribed_text(self, text):
        """Whisper 转写完成的回调"""
        self.handle_text_input(text)
        self.view.show_system_message(f"你(语音)：{text}\n")
        # 把文字发给大模型去对话
        self.core.text_message_sent.emit(text)

    # ===== 处理 View 传来的动作 =====
    def handle_text_input(self, msg):
        """执行检索记忆的操作方法"""
        self.pending_user_msg = msg
        self.view.show_system_message("检索记忆中...\n")
        self.view.set_loading_state(True)
        self.core.memory_query_signal.emit(msg)

    def handle_image_input(self, file_path):
        self.view.set_loading_state(True)
        self.core.photo_msg.emit(file_path)

    # ===== 处理 Service 传回的结果 =====
    def on_memory_query_result(self, user_msg):
        memory_prompt = ""
        full_msg = f"{memory_prompt}【当前问题】{user_msg}" if memory_prompt else user_msg
        if self.pending_photo_desc:
            full_msg = f"图片内容：{self.pending_photo_desc}\n{full_msg}"

        logger.debug(f"拼接后{full_msg}")
        self.view.set_loading_state(True)
        self.core.text_message_sent.emit(full_msg)

    def on_ai_chunk_received(self, chunk_text):
        self.init_check_status = 1
        self.pending_text_msg += chunk_text
        self.view.append_response_chunk(chunk_text)

    def on_api_finished(self):
        logger.info(f"回复完成：{self.pending_text_msg}")
        self.view.set_loading_state(False)

        if self.pending_text_msg and self.pending_user_msg:
            full_dialogue = f"用户问题：{self.pending_user_msg}{self.pending_photo_desc}\nAI回复：{self.pending_text_msg}"
            self.core.memory_msg.emit(full_dialogue)

        self.pending_text_msg = ""
        self.init_check_status = 0
        self.pending_photo_desc = None

    def handle_photo_result(self, img_desc):
        self.pending_photo_desc = img_desc
        self.view.show_system_message("\n图片已识别，请输入你想问的问题\n")
        self.view.set_loading_state(False)

    def on_memory_finished(self, msg):
        if msg:
            logger.info("已找到相同记忆，记忆已归档")
