import sys

from dotenv import load_dotenv
load_dotenv()

from PyQt5.QtWidgets import QApplication
import src.services
from src.ui import DeskpetUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DeskpetUI()
    pet.show()
    sys.exit(app.exec_())

