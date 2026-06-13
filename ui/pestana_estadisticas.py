import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QMessageBox, QTableWidget,
                               QTableWidgetItem, QHeaderView, QFileDialog)
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import Qt


class StatisticsPanel(QWidget):
    """Widget displaying per-family and per-species image counts, with export-to-Excel and full-reset controls."""

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager

        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()

        self.lbl_resumen = QLabel("-")
        self.lbl_resumen.setStyleSheet("font-size: 14px; padding: 10px; background-color: rgba(0,0,0,0.1); border-radius: 5px;")
        header_layout.addWidget(self.lbl_resumen, stretch=1)

        layout_btns_right = QVBoxLayout()

        self.btn_export = QPushButton("💾 Exportar Tablas")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet("background-color: #92c43e; border-radius: 5px; color: white; font-weight: bold; padding: 8px;")
        self.btn_export.clicked.connect(self.export_excel)

        self.btn_reset = QPushButton("🔄 Restaurar Dataset")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet("background-color: #59802a; border-radius: 5px; color: white; font-weight: bold; padding: 8px;")
        self.btn_reset.clicked.connect(self.reset_dataset)

        layout_btns_right.addWidget(self.btn_export)
        layout_btns_right.addWidget(self.btn_reset)

        header_layout.addLayout(layout_btns_right)
        layout.addLayout(header_layout)

        layout.addWidget(QLabel("📊 Balance por Familias"))
        self.tabla_familias = QTableWidget()
        self.configurar_tabla(self.tabla_familias, ["Familia", "Originales", "Eliminadas", "Actuales"])
        layout.addWidget(self.tabla_familias, stretch=1)

        layout.addWidget(QLabel("🐾 Balance por Especies"))
        self.tabla_especies = QTableWidget()
        cols_especies = ["Nombre Científico", "Nombre Común", "Familia", "Género", "Originales", "Eliminadas", "Actuales"]
        self.configurar_tabla(self.tabla_especies, cols_especies)
        layout.addWidget(self.tabla_especies, stretch=2)

        self.manager.data_changed.connect(self.refresh_all)
        self.refresh_all()

    def reset_dataset(self):
        confirmacion = QMessageBox.warning(
            self, "PELIGRO: Restaurar Dataset",
            "¿Estás segura de que quieres RESTAURAR TODO el dataset?\n\n"
            "1. Se moverán todas las imágenes de 'deleted' a su carpeta original.\n"
            "2. Se marcarán todas como 'activas'.\n"
            "3. Los contadores de eliminados volverán a 0.\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.Cancel
        )
        if confirmacion == QMessageBox.Yes:
            restaurados, errores = self.manager.restaurar_dataset_completo()
            if errores == 0:
                QMessageBox.information(self, "Éxito", f"Se restauraron {restaurados} imágenes correctamente.\nEl dataset está como nuevo.")
            else:
                QMessageBox.warning(self, "Atención", f"Se restauraron {restaurados} imágenes, pero hubo {errores} errores (quizás archivos perdidos).")

    def configurar_tabla(self, tabla, columnas):
        tabla.setColumnCount(len(columnas))
        tabla.setHorizontalHeaderLabels(columnas)
        header = tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(columnas)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        tabla.setSortingEnabled(True)
        tabla.setAlternatingRowColors(True)

    def refresh_all(self):
        self.update_summary()
        self.update_families_table()
        self.update_species_table()

    def update_summary(self):
        kpis = self.manager.get_resumen_global()
        if not kpis:
            return
        txt = (f"<b>Total Imágenes:</b> {kpis['total_imgs']} "
               f"(✅ {kpis['activas']} Activas | 🗑️ {kpis['borradas']} Eliminadas) &nbsp;|&nbsp; "
               f"<b>Especies:</b> {kpis['n_especies']} &nbsp;|&nbsp; "
               f"<b>Familias:</b> {kpis['n_familias']}")
        self.lbl_resumen.setText(txt)

    def update_families_table(self):
        df = self.manager.get_estadisticas_familias()
        t = self.tabla_familias
        t.setSortingEnabled(False)
        t.setRowCount(len(df))
        for row, (family, registro) in enumerate(df.iterrows()):
            items = [
                QTableWidgetItem(str(family)),
                QTableWidgetItem(), QTableWidgetItem(), QTableWidgetItem()
            ]
            items[1].setData(Qt.DisplayRole, int(registro['total']))
            items[2].setData(Qt.DisplayRole, int(registro['deleted']))
            items[3].setData(Qt.DisplayRole, int(registro['active']))
            for col, item in enumerate(items):
                t.setItem(row, col, item)
        t.setSortingEnabled(True)

    def update_species_table(self):
        df = self.manager.get_estadisticas_detalladas()
        t = self.tabla_especies
        t.setSortingEnabled(False)
        t.setRowCount(len(df))
        COLOR_RED = QColor("#ffcccc")
        COLOR_YELLOW = QColor("#ffffcc")
        for row, (scientific_name, registro) in enumerate(df.iterrows()):
            n_comun = str(registro['common_name'])
            family = str(registro['family'])
            genus = str(registro['genus'])
            activo = int(registro['active'])
            borrado = int(registro['deleted'])
            total = int(registro['total'])
            items = [
                QTableWidgetItem(str(scientific_name)),
                QTableWidgetItem(n_comun),
                QTableWidgetItem(family),
                QTableWidgetItem(genus),
                QTableWidgetItem(), QTableWidgetItem(), QTableWidgetItem()
            ]
            items[4].setData(Qt.DisplayRole, total)
            items[5].setData(Qt.DisplayRole, borrado)
            items[6].setData(Qt.DisplayRole, activo)
            bg = None
            if activo == 0:
                bg = COLOR_RED
            elif activo < 10:
                bg = COLOR_YELLOW
            for col, item in enumerate(items):
                if bg:
                    item.setBackground(bg)
                    item.setForeground(QColor("black"))
                else:
                    item.setForeground(QBrush())
                t.setItem(row, col, item)
        t.setSortingEnabled(True)

    def export_excel(self):
        archivo, _ = QFileDialog.getSaveFileName(self, "Exportar Estadísticas", "estadisticas_dataset.xlsx", "Excel Files (*.xlsx)")
        if not archivo:
            return
        try:
            df_fam = self.manager.get_estadisticas_familias()
            df_esp = self.manager.get_estadisticas_detalladas()
            with pd.ExcelWriter(archivo) as writer:
                df_fam.to_excel(writer, sheet_name='Por Familias')
                df_esp.to_excel(writer, sheet_name='Por Especies')
            QMessageBox.information(self, "Éxito", f"Datos exportados correctamente a:\n{archivo}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{str(e)}\n\nAsegurate de tener instalada la librería 'openpyxl'.")
