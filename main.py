import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from ui.main_window import AuditoriaMainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = AuditoriaMainWindow()
    window.showMaximized()
    sys.exit(app.exec())
