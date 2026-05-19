from PyQt5.QtCore import Qt, QEvent


class MouseEvent:
    """专门用来拖动窗口的混入类,通过继承调用"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.drag_pos = None

    # --- 鼠标事件重写 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ArrowCursor)