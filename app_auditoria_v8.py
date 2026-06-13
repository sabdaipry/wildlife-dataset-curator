import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QMessageBox,
                               QListWidget, QListWidgetItem,
                               QAbstractItemView, QSplitter, QTabWidget)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt

from config import ARCHIVO_DATOS, CARPETA_DESCARTES, ESTILOS, NOMBRE_MODELO_EMBEDDING
from core.data_manager import DataManager
from ui.umap_widget import UMAPWidget
from ui.visor_zoom_widget import VisorZoomWidget
from ui.pestana_estadisticas import StatisticsPanel

# =============================================================================
# CAPA 3: VENTANA PRINCIPAL (Orquestador)
# =============================================================================

class AuditoriaMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Auditoría de Dataset")
        self.resize(1000, 700)

        # 1. Instanciar Lógica
        self.manager = DataManager(ARCHIVO_DATOS, CARPETA_DESCARTES)
        self.ventana_stats = None # Variable para guardar la ventana hija

        # 2. Configurar UI
        self._setup_ui()
        self._conectar_senales()

        # 3. Cargar estado inicial
        self.es_modo_oscuro = True # Flag para tema
        self.aplicar_tema_oscuro()  # Iniciar en oscuro por defecto

        # 4. Plotear datos iniciales
        if not self.manager.df.empty:
            x, y, c, idxs = self.manager.get_puntos_umap()
            self.umap_widget.graficar(x, y, c, idxs)
        else:
            QMessageBox.warning(self, "Atención", "No hay datos para mostrar.")

    def _setup_ui(self):

        # 1. Crear el Widget de Pestañas
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs) # Ahora las pestañas son el centro de todo

        # --- PESTAÑA 1: AUDITORÍA (Lo que tenías antes) ---
        pestana_auditoria = QWidget()
        layout_auditoria = QHBoxLayout(pestana_auditoria) # Layout principal de esta pestaña

        # Usamos Splitter para que el usuario pueda redimensionar paneles
        splitter = QSplitter(Qt.Horizontal)

        # --- PANEL IZQUIERDO: Mapa ---
        self.umap_widget = UMAPWidget(nombre_modelo=NOMBRE_MODELO_EMBEDDING)
        splitter.addWidget(self.umap_widget)

        # --- PANEL DERECHO: Lista y Visor ---
        panel_derecho = QWidget()
        layout_derecho = QVBoxLayout(panel_derecho)

        # Botonera superior derecha
        layout_botones = QHBoxLayout()
        # Asignamos un ID (objectName) al botón para poder darle estilo CSS específico
        self.btn_tema = QPushButton()
        self.btn_tema.setObjectName("btn_tema")
        self.btn_tema.setCursor(Qt.PointingHandCursor)
        self.btn_tema.setFixedWidth(30) # Hacemos el botón cuadradito

        # BOTÓN ESTADÍSTICAS
        """
        self.btn_stats = QPushButton("📊 Ver Estadísticas")
        self.btn_stats.setCursor(Qt.PointingHandCursor)
        self.btn_stats.clicked.connect(self.abrir_estadisticas)
        """
        # BOTÓN BORRAR
        self.btn_borrar = QPushButton("🗑️ Eliminar Seleccionados")
        self.btn_borrar.setObjectName("btn_borrar") # ID para CSS
        self.btn_borrar.setEnabled(False)
        self.btn_borrar.setCursor(Qt.PointingHandCursor)

        layout_botones.addWidget(self.btn_tema)
        #layout_botones.addWidget(self.btn_stats) # Lo agregamos al layout
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_borrar)
        layout_derecho.addLayout(layout_botones)

        # Lista
        self.lbl_lista_titulo = QLabel("Archivos Seleccionados:")
        layout_derecho.addWidget(self.lbl_lista_titulo)

        self.lista_archivos = QListWidget()
        self.lista_archivos.setSelectionMode(QAbstractItemView.SingleSelection)
        layout_derecho.addWidget(self.lista_archivos, stretch=1)

        # Info
        self.lbl_info = QLabel("Seleccione un punto en el mapa.")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setAlignment(Qt.AlignCenter)
        self.lbl_info.setStyleSheet("font-size: 14px; padding: 10px;")
        layout_derecho.addWidget(self.lbl_info)

        # Visor
        self.visor = VisorZoomWidget()
        layout_derecho.addWidget(self.visor, stretch=2)

        splitter.addWidget(panel_derecho)
        splitter.setSizes([700, 400])

        # Agregamos el splitter al layout de la pestaña auditoría
        layout_auditoria.addWidget(splitter)

        # --- PESTAÑA 2: ESTADÍSTICAS (La nueva) ---
        self.tab_stats = StatisticsPanel(self.manager)

        # --- AGREGAR PESTAÑAS AL WIDGET PRINCIPAL ---
        self.tabs.addTab(pestana_auditoria, "🔍 Auditoría Visual")
        self.tabs.addTab(self.tab_stats, "📊 Estadísticas y Control")

    def _conectar_senales(self):
        # Conectamos las señales del Widget UMAP a métodos del Main
        self.umap_widget.seleccion_realizada.connect(self.procesar_seleccion_lote)
        self.umap_widget.punto_cliqueado.connect(self.procesar_seleccion_unica)

        # Interacciones UI
        self.lista_archivos.itemClicked.connect(self.cargar_preview_desde_lista)
        self.lista_archivos.itemChanged.connect(self.actualizar_conteo_borrado)
        self.btn_borrar.clicked.connect(self.ejecutar_borrado)
        self.btn_tema.clicked.connect(self.alternar_tema)

        # TRUCO PARA CLICK VACÍO:
        # El evento 'button_press_event' de matplotlib devuelve un evento.
        # Si 'event.inaxes' es None o no choca con puntos, limpiamos.
        self.umap_widget.canvas.mpl_connect('button_press_event', self.on_canvas_click_main)

        # CONEXIÓN CLAVE: Cuando cambian los datos (borrado o reset), redibujamos el mapa
        self.manager.data_changed.connect(self.recargar_mapa)

    def recargar_mapa(self):
        # Obtenemos solo los puntos activos
        x, y, c, idxs = self.manager.get_puntos_umap()
        self.umap_widget.graficar(x, y, c, idxs)

        # Limpiamos la selección actual para evitar errores
        self.limpiar_seleccion()

    #  MÉTODO para manejar clicks en el mapa
    def on_canvas_click_main(self, event):
        if event.button != 1: return # Solo click izquierdo
        if self.umap_widget.btn_lazo.isChecked(): return # Si está en modo lazo, no interferir

        # Verificamos si el click tocó algún punto usando el método 'contains' del scatter plot
        # Accedemos a la colección de puntos del widget (esto es un poco avanzado,
        # pero es la forma correcta de saber si le pegaste a algo o al fondo)
        contains, _ = self.umap_widget.ax.collections[0].contains(event)

        if not contains:
            self.limpiar_seleccion()

    def limpiar_seleccion(self):
        self.lista_archivos.clear()
        self.lbl_info.setText("Selección limpiada.")
        self.btn_borrar.setText("🗑️ Eliminar Seleccionados") # Reseteamos texto
        self.btn_borrar.setEnabled(False)
        self.visor.scene.clear() # Limpiamos el visor de imagen

        # Le decimos al mapa que borre la línea roja también
        self.umap_widget.limpiar_dibujo_lazo()

    # --- LÓGICA DE CONTROL ---

    def procesar_seleccion_lote(self, indices_potenciales):
        """Recibe índices geométricos, filtra por estado y actualiza lista."""
        # Si la lista de índices viene vacía (se soltó el lazo sin agarrar nada)
        if not indices_potenciales:
            self.limpiar_seleccion()
            return

        self.lista_archivos.blockSignals(True)
        self.lista_archivos.clear()
        count = 0

        # Usamos el manager para validar que no estén borrados
        for idx in indices_potenciales:
            reg = self.manager.get_info_registro(idx)
            if reg['estado'] == 'borrado': continue

            item = QListWidgetItem(f"{reg['archivo']} ({reg.get('nombre_comun','?')})")
            item.setData(Qt.UserRole, int(idx)) # Guardamos el ID real en el item
            item.setCheckState(Qt.Checked)
            self.lista_archivos.addItem(item)
            count += 1

        self.lista_archivos.blockSignals(False)
        self.actualizar_conteo_borrado()

        self.lbl_info.setText(f"Lote seleccionado: {count} imágenes.")
        self.btn_borrar.setEnabled(count > 0)
        if count > 0:
            self.btn_borrar.setText(f"🗑️ Eliminar {count} elementos")

    def procesar_seleccion_unica(self, idx):
        reg = self.manager.get_info_registro(idx)
        if reg['estado'] == 'borrado':
            self.lbl_info.setText("❌ Imagen ya eliminada.")
            return

        self.lista_archivos.clear()
        item = QListWidgetItem(f"{reg['archivo']}")
        item.setData(Qt.UserRole, int(idx))
        item.setCheckState(Qt.Checked)
        self.lista_archivos.addItem(item)
        self.lista_archivos.setCurrentRow(0)

        self.cargar_preview_desde_lista(item)
        self.btn_borrar.setEnabled(True)
        self.btn_borrar.setText("🗑️ Eliminar 1 elemento")

    def cargar_preview_desde_lista(self, item):
        idx = item.data(Qt.UserRole)
        reg = self.manager.get_info_registro(idx)

        # --- PARTE 1: METADATOS (Familia y Género) ---
        # Intentamos obtener columnas comunes, si no existen ponemos "?"
        # Ajusta 'family'/'familia' según cómo se llamen en tu CSV
        familia = reg.get('family', reg.get('familia', 'Desconocida'))
        genero = reg.get('genus', reg.get('genero', 'Desconocido'))
        nombre_comun = reg.get('nombre_comun', 'Sin nombre común')
        nombre_cientifico = reg.get('nombre_cientifico', 'Scientific Name')

        # --- PARTE 2: VERIFICAR ESTADO ---
        ruta = str(reg['ruta_absoluta'])
        existe_fisicamente = os.path.exists(ruta)

        if existe_fisicamente:
            color_titulo = "white" if self.es_modo_oscuro else "black"
            aviso_estado =""
        else:
            # Si NO existe, limpiamos el visor y agregamos el cartel ROJO en el texto
            self.visor.scene.clear()
            aviso_estado = "<br><br><h2 style='color: #ff4444; background-color: #330000; padding: 5px;'>" \
            "⚠️ IMAGEN NO DISPONIBLE<br><span style='font-size:12px'>(Archivo eliminado o movido)</span></h2>"
            color_titulo = "#888" # Grisáceo para indicar que está "deshabilitado"

        # --- ARMADO DEL HTML FINAL ---
        # Mostramos la info siempre, y abajo el aviso si corresponde
        texto = (f"<h2 style='margin:0'>{nombre_comun}</h2>"
                 f"<i style='color:#888; font-size: 14px'>{nombre_cientifico}</i><br>"
                 f"<b>Familia:</b> {familia} | <b>Género:</b> {genero}"
                 f"</p>"
                 f"{aviso_estado}") # Aquí se inserta el cartel si falta la foto
        self.lbl_info.setText(texto)

        # --- PARTE 3: CARGAR EN VISOR ---
        # El método cargar_imagen del visor ahora se encarga de mostrar el error visualmente
        self.visor.cargar_imagen(ruta)

    def ejecutar_borrado(self):
        # 1. Recolectar IDs seleccionados en la GUI
        indices_a_borrar = []
        # items_visuales = []

        for i in range(self.lista_archivos.count()):
            item = self.lista_archivos.item(i)
            if item.checkState() == Qt.Checked:
                indices_a_borrar.append(item.data(Qt.UserRole))
                # items_visuales.append(item)

        if not indices_a_borrar: return

        # 2. Confirmación
        resp = QMessageBox.question(self, "Confirmar",
                                    f"¿Mover {len(indices_a_borrar)} imágenes a descartes?",
                                    QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.No: return

        # 3. Delegar la acción sucia al Manager
        movidos, errores = self.manager.mover_a_descartes(indices_a_borrar)
        # for item in items_visuales: self.lista_archivos.takeItem(self.lista_archivos.row(item))
        self.lbl_info.setText(f"{movidos} movidos. {errores} errores.")
        self.visor.scene.clear()
        self.btn_borrar.setEnabled(False)

    def alternar_tema(self):
        self.es_modo_oscuro = not self.es_modo_oscuro
        if self.es_modo_oscuro:
            self.aplicar_tema_oscuro()
        else:
            self.aplicar_tema_claro()

    def aplicar_tema_oscuro(self):
        # 1. Aplicar CSS Global (arregla QMessageBox y Textos)
        self.setStyleSheet(ESTILOS["oscuro"])
        # 2. Configurar Gráfico
        self.umap_widget.set_tema(True)
        # 3. Configurar Visor
        self.visor.setBackgroundBrush(QColor("#1e1e1e"))
        # 4. Icono Botón (Emoji Luna)
        self.btn_tema.setText("🌞")
        self.btn_tema.setToolTip("Cambiar a modo claro")

        if self.ventana_stats: self.ventana_stats.set_tema(True)

    def aplicar_tema_claro(self):
        self.setStyleSheet(ESTILOS["claro"])
        self.umap_widget.set_tema(False)
        self.visor.setBackgroundBrush(QColor("#f0f0f0"))
        # Icono Botón (Emoji Sol)
        self.btn_tema.setText("🌚")
        self.btn_tema.setToolTip("Cambiar a modo oscuro")

        if self.ventana_stats: self.ventana_stats.set_tema(False)

    def actualizar_conteo_borrado(self, item=None):
        count = 0
        for i in range(self.lista_archivos.count()):
            if self.lista_archivos.item(i).checkState() == Qt.Checked:
                count += 1

        if count > 0:
            self.btn_borrar.setEnabled(True)
            self.btn_borrar.setText(f"🗑️ Eliminar {count} Seleccionados")
        else:
            self.btn_borrar.setEnabled(False)
            self.btn_borrar.setText("🗑️ Eliminar Seleccionados")

    """
    def abrir_estadisticas(self):
        if self.ventana_stats is None:
            # Creamos la ventana pasándole el MISMO manager
            self.ventana_stats = VentanaEstadisticas(self.manager, self)

        # Aplicamos el tema actual antes de mostrar
        self.ventana_stats.set_tema(self.es_modo_oscuro)
        self.ventana_stats.show()
        # Traer al frente por si estaba minimizada
        self.ventana_stats.raise_()
        self.ventana_stats.activateWindow()
    """



if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Fuente un poco más grande para legibilidad
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = AuditoriaMainWindow()
    window.showMaximized()
    sys.exit(app.exec())
