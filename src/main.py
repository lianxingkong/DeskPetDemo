import sys
from PyQt5.QtWidgets import QApplication

from src.ui.view.based_ui import DeskpetUI
from src.ui import CommunicationButler
from src.core import ThreadManager
from src.services import BaseMcpStart, BaseMcpEnd

if __name__ == "__main__":
    # 初始化线程
    app = QApplication(sys.argv)
    # 实例化UI
    view = DeskpetUI()
    # 实例化线程
    core = ThreadManager()
    # 连接到中间管家管理连接
    butler = CommunicationButler(view=view, core=core)
    # 启动mcp服务
    BaseMcpStart.start_all()
    # 显示UI
    view.show()
    # 结束指令
    exit_code = app.exec_()
    # 结束mcp服务
    BaseMcpEnd.start_all()
    core.cleanup().exit(exit_code)
