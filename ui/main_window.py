import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QMessageBox,
                               QListWidget, QListWidgetItem,
                               QAbstractItemView, QSplitter, QTabWidget)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from config import DATA_FILE, TRASH_FOLDER, THEMES, EMBEDDING_MODEL_NAME
from core.data_manager import DataManager
from ui.umap_widget import UMAPWidget
from ui.visor_zoom_widget import VisorZoomWidget
from ui.pestana_estadisticas import StatisticsPanel


class CuratorMainWindow(QMainWindow):
    """Main application window: hosts the visual audit tab (UMAP + image preview) and the statistics tab."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Auditoría de Dataset")
        self.resize(1000, 700)

        self.manager = DataManager(DATA_FILE, TRASH_FOLDER)
        self.stats_window = None

        self._setup_ui()
        self._connect_signals()

        self.is_dark_mode = True
        self.apply_dark_theme()

        if not self.manager.df.empty:
            x, y, c, idxs = self.manager.get_puntos_umap()
            self.umap_widget.graficar(x, y, c, idxs)
        else:
            QMessageBox.warning(self, "Atención", "No hay datos para mostrar.")

    def _setup_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        audit_tab = QWidget()
        audit_layout = QHBoxLayout(audit_tab)

        splitter = QSplitter(Qt.Horizontal)

        self.umap_widget = UMAPWidget(nombre_modelo=EMBEDDING_MODEL_NAME)
        splitter.addWidget(self.umap_widget)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        buttons_layout = QHBoxLayout()
        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName("btn_tema")
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.setFixedWidth(30)

        self.btn_delete = QPushButton("🗑️ Eliminar Seleccionados")
        self.btn_delete.setObjectName("btn_borrar")
        self.btn_delete.setEnabled(False)
        self.btn_delete.setCursor(Qt.PointingHandCursor)

        buttons_layout.addWidget(self.btn_theme)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_delete)
        right_layout.addLayout(buttons_layout)

        self.lbl_lista_titulo = QLabel("Archivos Seleccionados:")
        right_layout.addWidget(self.lbl_lista_titulo)

        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QAbstractItemView.SingleSelection)
        right_layout.addWidget(self.files_list, stretch=1)

        self.lbl_info = QLabel("Seleccione un punto en el mapa.")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setAlignment(Qt.AlignCenter)
        self.lbl_info.setStyleSheet("font-size: 14px; padding: 10px;")
        right_layout.addWidget(self.lbl_info)

        self.visor = VisorZoomWidget()
        right_layout.addWidget(self.visor, stretch=2)

        splitter.addWidget(right_panel)
        splitter.setSizes([700, 400])

        audit_layout.addWidget(splitter)

        self.tab_stats = StatisticsPanel(self.manager)

        self.tabs.addTab(audit_tab, "🔍 Auditoría Visual")
        self.tabs.addTab(self.tab_stats, "📊 Estadísticas y Control")

    def _connect_signals(self):
        self.umap_widget.seleccion_realizada.connect(self.process_batch_selection)
        self.umap_widget.punto_cliqueado.connect(self.process_single_selection)

        self.files_list.itemClicked.connect(self.load_preview_from_list)
        self.files_list.itemChanged.connect(self.update_deletion_count)
        self.btn_delete.clicked.connect(self.execute_deletion)
        self.btn_theme.clicked.connect(self.toggle_theme)

        self.umap_widget.canvas.mpl_connect('button_press_event', self.on_canvas_click_main)

        self.manager.data_changed.connect(self.reload_map)

    def reload_map(self):
        x, y, c, idxs = self.manager.get_puntos_umap()
        self.umap_widget.graficar(x, y, c, idxs)
        self.clear_selection()

    def on_canvas_click_main(self, event):
        if event.button != 1:
            return
        if self.umap_widget.btn_lazo.isChecked():
            return
        contains, _ = self.umap_widget.ax.collections[0].contains(event)
        if not contains:
            self.clear_selection()

    def clear_selection(self):
        self.files_list.clear()
        self.lbl_info.setText("Selección limpiada.")
        self.btn_delete.setText("🗑️ Eliminar Seleccionados")
        self.btn_delete.setEnabled(False)
        self.visor.scene.clear()
        self.umap_widget.limpiar_dibujo_lazo()

    def process_batch_selection(self, potential_indices):
        if not potential_indices:
            self.clear_selection()
            return

        self.files_list.blockSignals(True)
        self.files_list.clear()
        count = 0

        for idx in potential_indices:
            reg = self.manager.get_info_registro(idx)
            if reg['status'] == 'deleted':
                continue
            item = QListWidgetItem(f"{reg['filename']} ({reg.get('common_name','?')})")
            item.setData(Qt.UserRole, int(idx))
            item.setCheckState(Qt.Checked)
            self.files_list.addItem(item)
            count += 1

        self.files_list.blockSignals(False)
        self.update_deletion_count()

        self.lbl_info.setText(f"Lote seleccionado: {count} imágenes.")
        self.btn_delete.setEnabled(count > 0)
        if count > 0:
            self.btn_delete.setText(f"🗑️ Eliminar {count} elementos")

    def process_single_selection(self, idx):
        reg = self.manager.get_info_registro(idx)
        if reg['status'] == 'deleted':
            self.lbl_info.setText("❌ Imagen ya eliminada.")
            return

        self.files_list.clear()
        item = QListWidgetItem(f"{reg['filename']}")
        item.setData(Qt.UserRole, int(idx))
        item.setCheckState(Qt.Checked)
        self.files_list.addItem(item)
        self.files_list.setCurrentRow(0)

        self.load_preview_from_list(item)
        self.btn_delete.setEnabled(True)
        self.btn_delete.setText("🗑️ Eliminar 1 elemento")

    def load_preview_from_list(self, item):
        idx = item.data(Qt.UserRole)
        reg = self.manager.get_info_registro(idx)

        family = reg.get('family', 'Unknown')
        genus = reg.get('genus', 'Unknown')
        common_name = reg.get('common_name', 'Unknown')
        scientific_name = reg.get('scientific_name', 'Unknown')

        ruta = str(reg['absolute_path'])
        exists_on_disk = os.path.exists(ruta)

        if exists_on_disk:
            status_warning = ""
        else:
            self.visor.scene.clear()
            status_warning = ("<br><br><h2 style='color: #ff4444; background-color: #330000; padding: 5px;'>"
                              "⚠️ IMAGEN NO DISPONIBLE<br><span style='font-size:12px'>"
                              "(Archivo eliminado o movido)</span></h2>")

        texto = (f"<h2 style='margin:0'>{common_name}</h2>"
                 f"<i style='color:#888; font-size: 14px'>{scientific_name}</i><br>"
                 f"<b>Familia:</b> {family} | <b>Género:</b> {genus}"
                 f"</p>"
                 f"{status_warning}")
        self.lbl_info.setText(texto)

        self.visor.cargar_imagen(ruta)

    def execute_deletion(self):
        indices_to_delete = []
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            if item.checkState() == Qt.Checked:
                indices_to_delete.append(item.data(Qt.UserRole))

        if not indices_to_delete:
            return

        resp = QMessageBox.question(self, "Confirmar",
                                    f"¿Mover {len(indices_to_delete)} imágenes a descartes?",
                                    QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.No:
            return

        moved, errors = self.manager.mover_a_descartes(indices_to_delete)
        self.lbl_info.setText(f"{moved} movidos. {errors} errores.")
        self.visor.scene.clear()
        self.btn_delete.setEnabled(False)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    def apply_dark_theme(self):
        self.setStyleSheet(THEMES["dark"])
        self.umap_widget.set_tema(True)
        self.visor.setBackgroundBrush(QColor("#1e1e1e"))
        self.btn_theme.setText("🌞")
        self.btn_theme.setToolTip("Cambiar a modo claro")
        if self.stats_window:
            self.stats_window.set_tema(True)

    def apply_light_theme(self):
        self.setStyleSheet(THEMES["light"])
        self.umap_widget.set_tema(False)
        self.visor.setBackgroundBrush(QColor("#f0f0f0"))
        self.btn_theme.setText("🌚")
        self.btn_theme.setToolTip("Cambiar a modo oscuro")
        if self.stats_window:
            self.stats_window.set_tema(False)

    def update_deletion_count(self, item=None):
        count = sum(
            1 for i in range(self.files_list.count())
            if self.files_list.item(i).checkState() == Qt.Checked
        )
        if count > 0:
            self.btn_delete.setEnabled(True)
            self.btn_delete.setText(f"🗑️ Eliminar {count} Seleccionados")
        else:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setText("🗑️ Eliminar Seleccionados")
