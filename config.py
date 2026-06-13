# Data paths
DATA_FILE = "output/datos_clusters_vitb14.csv"
TRASH_FOLDER = "data/deleted"
EMBEDDING_MODEL_NAME = "DINOv2 ViT-B/14"

# CSS styles (dark theme / light theme)
DARK_THEME = """
    QMainWindow, QWidget { background-color: #2d2d2d; color: #e0e0e0; }
    QLabel { color: #e0e0e0; font-weight: bold; }
    QListWidget { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444; }
    QPushButton#btn_tema { background-color: #444; color: white; border: 1px solid #666; border-radius: 5px; font-size: 16px; }
    QPushButton#btn_tema:hover { background-color: #555; }
    QPushButton#btn_borrar { background-color: #8B0000; color: white; border-radius: 5px; padding: 5px; font-weight: bold; }
    QPushButton#btn_borrar:disabled { background-color: #442222; color: #888; }
    QCheckBox { color: #e0e0e0; spacing: 5px; }
    QMessageBox { background-color: #2d2d2d; color: white; }
    QMessageBox QLabel { color: white; }
    QMessageBox QPushButton { background-color: #444; color: white; min-width: 80px; padding: 5px; }
    QPushButton#btn_lazo { background-color: #444; color: #aaa; border: 1px solid #666; border-radius: 4px; padding: 5px; }
    QPushButton#btn_lazo:checked { background-color: #008800; color: white; border: 1px solid #00aa00; }
    QPushButton#btn_lazo:hover { border: 1px solid #888; }
    QTabWidget::pane { border: 1px solid #444; }
    QTabBar::tab { background: #333; color: #aaa; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
    QTabBar::tab:selected { background: #555; color: white; font-weight: bold; border-bottom: 2px solid #00aa00; }
    QTableWidget {
        background-color: #1e1e1e;
        color: #f0f0f0;
        gridline-color: #444444;
        border: 1px solid #444;
        alternate-background-color: #2a2a2a;
    }
    QHeaderView::section {
        background-color: #333333;
        color: white;
        padding: 4px;
        border: 1px solid #555;
        font-weight: bold;
    }
    QTableCornerButton::section {
        background-color: #333333;
        border: 1px solid #555;
    }
"""

LIGHT_THEME = """
    QMainWindow, QWidget { background-color: #f0f0f0; color: black; }
    QLabel { color: black; font-weight: bold; }
    QListWidget { background-color: white; color: black; border: 1px solid #ccc; }
    QPushButton#btn_tema { background-color: white; color: #333; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
    QPushButton#btn_tema:hover { background-color: #e6e6e6; }
    QPushButton#btn_borrar { background-color: #cc0000; color: white; border-radius: 5px; padding: 5px; font-weight: bold; }
    QPushButton#btn_borrar:disabled { background-color: #ffcccc; color: #999; }
    QCheckBox { color: black; spacing: 5px; }
    QMessageBox { background-color: #f0f0f0; color: black; }
    QPushButton#btn_lazo { background-color: #e0e0e0; color: #555; border: 1px solid #ccc; border-radius: 4px; padding: 5px; }
    QPushButton#btn_lazo:checked { background-color: #4CAF50; color: white; border: 1px solid #388E3C; }
    QPushButton#btn_lazo:hover { border: 1px solid #999; }
    QTabWidget::pane { border: 1px solid #ccc; }
    QTabBar::tab { background: #e0e0e0; color: #555; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
    QTabBar::tab:selected { background: white; color: black; font-weight: bold; border-bottom: 2px solid #008800; }
    QTableWidget {
        background-color: white;
        color: black;
        gridline-color: #ccc;
        alternate-background-color: #f9f9f9;
    }
    QHeaderView::section {
        background-color: #e0e0e0;
        color: black;
        padding: 4px;
        border: 1px solid #ccc;
    }
"""

# Grouped for access by theme name (used in main_window)
THEMES = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}
