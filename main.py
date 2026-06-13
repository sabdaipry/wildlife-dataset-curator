import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from core.logger import setup_logging
from ui.main_window import CuratorMainWindow


if __name__ == "__main__":
    setup_logging()
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = CuratorMainWindow()
    window.showMaximized()
    sys.exit(app.exec())
