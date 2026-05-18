import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont


class MiniPet(QWidget):
    # ==========================================
    # 核心概念 2：自定义信号（对讲机频道）
    # 声明一个信号，用来传送字符串类型的数据
    # ==========================================
    api_response = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # 记录拖拽位置的变量
        self.drag_pos = None

        # 初始化界面
        self.initUI()

        # 初始化定时器
        self.initTimers()

        # 绑定信号与槽
        self.initSignals()

    def initUI(self):
        # ==========================================
        # 核心概念 1：控件（积木块） & 窗口黑魔法
        # ==========================================
        # 1. 窗口黑魔法：无边框、置顶、背景透明
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 2. 创建桌宠贴纸 (用大字号Emoji代替图片，方便测试)
        self.pet_label = QLabel("🐾", self)
        self.pet_label.setFont(QFont("Arial", 48))  # 设置字号

        # 3. 创建气泡贴纸（初始为空且隐藏）
        self.bubble_label = QLabel("", self)
        self.bubble_label.setFont(QFont("Arial", 12))
        self.bubble_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 200); /* 半透明白色背景 */
                border: 1px solid #ccc;                    /* 灰色边框 */
                border-radius: 10px;                       /* 圆角 */
                padding: 8px;                              /* 内边距 */
            }
        """)
        self.bubble_label.hide()  # 初始隐藏

        # 4. 创建一个交互按钮（模拟右键菜单的聊天选项）
        self.chat_btn = QPushButton("💬 点我说话", self)

        # 5. 使用布局自动排列控件（垂直布局：气泡在上，宠物在中，按钮在下）
        layout = QVBoxLayout()
        layout.addWidget(self.bubble_label, 0, Qt.AlignCenter)  # 居中对齐
        layout.addWidget(self.pet_label, 0, Qt.AlignCenter)
        layout.addWidget(self.chat_btn, 0, Qt.AlignCenter)
        self.setLayout(layout)

        # 自动调整窗口大小适应内容
        self.adjustSize()

    def initTimers(self):
        # ==========================================
        # 核心概念 4：QTimer（闹钟）
        # ==========================================
        # 1. 买个闹钟：用于控制气泡几秒后消失
        self.bubble_timer = QTimer()
        self.bubble_timer.setSingleShot(True)  # 只响一次

        # 2. 买个闹钟：模拟网络请求的延迟
        self.api_timer = QTimer()
        self.api_timer.setSingleShot(True)

    def initSignals(self):
        # ==========================================
        # 核心概念 2：信号与槽（连接对讲机）
        # ==========================================
        # 内置信号连接：按钮点击 -> 触发聊天函数
        self.chat_btn.clicked.connect(self.on_chat_clicked)

        # 内置信号连接：气泡闹钟响 -> 隐藏气泡
        self.bubble_timer.timeout.connect(self.bubble_label.hide)

        # 内置信号连接：模拟API闹钟响 -> 发送自定义信号
        self.api_timer.timeout.connect(self.mock_api_call)

        # 自定义信号连接：收到API返回 -> 显示在气泡上
        self.api_response.connect(self.show_bubble)

    # ==========================================
    # 核心概念 3：事件重写（拦截鼠标事件实现拖拽）
    # ==========================================
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 记录偏移量
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            # 改变鼠标样式为抓手
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drag_pos:
            # 移动窗口
            self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 恢复鼠标样式
            self.setCursor(Qt.ArrowCursor)

    # ==========================================
    # 槽函数：处理具体业务逻辑
    # ==========================================
    def on_chat_clicked(self):
        """点击按钮时触发"""
        # 1. 先显示思考中
        self.show_bubble("🤔 思考中...")

        # 2. 关闭之前的闹钟（防抖）
        self.api_timer.stop()

        # 3. 启动模拟API闹钟，2秒后响
        self.api_timer.start(2000)

    def mock_api_call(self):
        """模拟 API 请求返回结果"""
        # 模拟大模型回复，通过自定义信号发出去
        self.api_response.emit("你好喵~ 我是 PyQt 桌宠！")

    def show_bubble(self, text):
        """显示气泡并重置消失倒计时"""
        self.bubble_label.setText(text)
        self.bubble_label.adjustSize()  # 根据文字长度自适应大小
        self.bubble_label.show()

        # 重置消失闹钟，5秒后隐藏气泡
        self.bubble_timer.start(5000)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = MiniPet()
    pet.show()
    sys.exit(app.exec_())
