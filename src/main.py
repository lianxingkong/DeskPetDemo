import sys
from PyQt5.QtWidgets import QApplication

from src.ui.view.based_ui import DeskpetUI
from src.ui import CommunicationButler
from src.core import ThreadManager
from src.services import BaseMcpControl

if __name__ == "__main__":
    func = BaseMcpControl
    # 初始化线程
    app = QApplication(sys.argv)
    # 实例化UI
    view = DeskpetUI()
    # 实例化线程
    core = ThreadManager()
    # 连接到中间管家管理连接
    butler = CommunicationButler(view=view, core=core)
    # 显示UI
    view.show()

    exit_code = app.exec_()
    core.cleanup().exit(exit_code)
