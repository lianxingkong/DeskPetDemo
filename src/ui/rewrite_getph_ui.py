from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QImage
from PyQt5.QtCore import QMimeData


class ChatBox(QTextEdit):
    """自定义交互框，支持粘贴图片和拖拽图片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # 允许拖拽进入

    # --- 场景2：重写粘贴事件，支持截图粘贴 ---
    def insertFromMimeData(self, source: QMimeData):
        # 如果剪贴板里有图片（比如截图或者复制的图片）
        if source.hasImage():
            image = source.imageData()
            # 将图片插入到光标位置
            cursor = self.textCursor()
            cursor.insertImage(image)
        else:
            # 否则按普通文本处理
            super().insertFromMimeData(source)

    # --- 场景3：重写拖拽事件，支持拖入图片文件 ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            # 获取拖入的文件路径
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                image = QImage(file_path)
                if not image.isNull():
                    cursor = self.textCursor()
                    cursor.insertImage(image)
                    return
        super().dropEvent(event)

