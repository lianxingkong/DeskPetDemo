import sys

from PyQt5.QtWidgets import QApplication
from src.services import *
from src.ui import DeskpetUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DeskpetUI()
    pet.show()
    sys.exit(app.exec_())

