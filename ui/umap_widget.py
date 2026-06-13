import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path
from matplotlib.colors import ListedColormap

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer, Signal


class UMAPWidget(QWidget):
    """Standalone widget that manages the Matplotlib chart and Lasso Selector."""

    # Custom signals: communicate events outward without knowing who listens
    seleccion_realizada = Signal(list)  # Emits list of indices
    punto_cliqueado = Signal(int)       # Emits a single index
    deseleccion_total = Signal()        # Notifies that the user clicked on empty space

    def __init__(self, parent=None, nombre_modelo=""):
        super().__init__(parent)
        self.nombre_modelo = nombre_modelo
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(5, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout_boton = QHBoxLayout()
        layout_boton.setContentsMargins(10, 0, 0, 0)

        self.btn_lazo = QPushButton("➰ Selección Múltiple")
        self.btn_lazo.setObjectName("btn_lazo")
        self.btn_lazo.setCheckable(True)
        self.btn_lazo.setCursor(Qt.PointingHandCursor)
        self.btn_lazo.toggled.connect(self.toggle_lazo)

        layout_boton.addWidget(self.btn_lazo)
        layout_boton.addStretch()

        layout.addWidget(self.toolbar)
        layout.addLayout(layout_boton)
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)

        # Persistent line to "freeze" the lasso drawing on screen.
        # Initially empty; high zorder so it renders above the scatter points.
        self.linea_persistente = None
        self.crosshair_v = None
        self.crosshair_h = None
        self.selector = None

        self.puntos_cache = None
        self.indices_reales = None
        self.color_titulo_actual = 'black'
        self.is_dark_mode = False  # Tracks theme state for redraws

        # Initial artist setup (recreated in graficar() after ax.clear())
        self._inicializar_artistas()

    def _inicializar_artistas(self):
        """Creates graphic objects (lines) if they don't exist or after a clear()."""
        self.linea_persistente, = self.ax.plot([], [], color='red', linewidth=2, alpha=0.9, zorder=10)

        # Initially invisible; zorder=5 so they sit behind the lasso but above scatter points
        style = {'color': 'cyan', 'linestyle': '--', 'linewidth': 0.8, 'alpha': 0.8, 'visible': False, 'zorder': 5}
        self.crosshair_v = self.ax.axvline(x=0, **style)
        self.crosshair_h = self.ax.axhline(y=0, **style)

        if self.selector: self.selector.disconnect_events()
        self.selector = LassoSelector(self.ax, onselect=self.on_lasso_finished, useblit=True)
        self.selector.set_active(False)

    def graficar(self, x, y, c, indices_reales):
        self.ax.clear()

        # ax.clear() destroys artists — recreate them
        self._inicializar_artistas()
        self.aplicar_colores_tema()

        self.puntos_cache = np.column_stack((x, y))
        self.indices_reales = indices_reales  # Mapping: visual index -> DataFrame index

        n_familias = int(np.max(c)) + 1 if len(c) > 0 else 1

        if n_familias <= 10: mi_cmap = 'tab10'
        elif n_familias <= 20: mi_cmap = 'tab20'
        else:
            cmap1 = mpl.colormaps['tab20']
            cmap2 = mpl.colormaps['tab20b']
            cmap3 = mpl.colormaps['tab20c']

            # Stack colors from three colormaps to support up to 60 families
            colores_combinados = np.vstack((
                cmap1(np.linspace(0, 1, 20)),
                cmap2(np.linspace(0, 1, 20)),
                cmap3(np.linspace(0, 1, 20))
            ))

            mi_cmap = ListedColormap(colores_combinados, name='tab60')

        self.ax.scatter(x, y, c=c, cmap=mi_cmap, s=15, picker=5)
        self.ax.axis('off')
        self.ax.set_title(f"Espacio Semántico ({self.nombre_modelo} + UMAP)", color=self.color_titulo_actual)

        self.canvas.draw()

        self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)

    def on_lasso_finished(self, verts):
        """Fires immediately when the mouse is released after drawing a lasso."""
        self.ocultar_crosshair()

        verts_np = np.array(verts)
        if len(verts_np) > 2:
            verts_np = np.vstack([verts_np, verts_np[0]])
            self.linea_persistente.set_data(verts_np[:, 0], verts_np[:, 1])
            self.linea_persistente.set_visible(True)

            # Force redraw immediately to show the lasso line before heavy computation starts.
            self.canvas.draw()

        # 10ms timer lets the GUI render the line before computing which points are inside.
        QTimer.singleShot(10, lambda: self._procesar_matematica_lazo(verts))

    def _procesar_matematica_lazo(self, verts):
        """Heavy computation that runs after the lasso line is already drawn."""
        if self.puntos_cache is None: return

        path = Path(verts)
        mask = path.contains_points(self.puntos_cache)
        indices_visuales = np.where(mask)[0]

        # CRITICAL TRANSLATION: visual index -> DataFrame index
        if self.indices_reales is not None and len(indices_visuales) > 0:
            indices_finales = self.indices_reales[indices_visuales]
            self.seleccion_realizada.emit(indices_finales.tolist())
        else:
            self.seleccion_realizada.emit([])

    def on_canvas_click(self, event):
        if event.inaxes != self.ax: return

        if self.btn_lazo.isChecked():
            # Clear the previous lasso line before starting a new one
            self.linea_persistente.set_data([], [])
            self.linea_persistente.set_visible(False)
            self.ocultar_crosshair()
            self.canvas.draw()
        else:
            pass

    def on_pick(self, event):
        if self.btn_lazo.isChecked():
            return

        if len(event.ind) > 0:
            idx_visual = event.ind[0]

            x_pt = self.puntos_cache[idx_visual, 0]
            y_pt = self.puntos_cache[idx_visual, 1]
            self.actualizar_crosshair(x_pt, y_pt)

            # TRANSLATION: visual index -> real DataFrame index
            if self.indices_reales is not None:
                idx_real = self.indices_reales[idx_visual]
                self.punto_cliqueado.emit(int(idx_real))

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    def toggle_lazo(self, activo):
        # Redraw before activating to ensure the blitting background is ready
        if activo:
            self.ocultar_crosshair()
            self.canvas.draw()
            self.selector.set_active(True)
            self.btn_lazo.setText("➰ Lazo Activo")
            self.btn_lazo.setChecked(True)
        else:
            self.selector.set_active(False)
            self.btn_lazo.setText("➰ Selección Múltiple")
            self.btn_lazo.setChecked(False)
            self.limpiar_dibujo_lazo()

    def limpiar_dibujo_lazo(self):
        self.linea_persistente.set_data([], [])
        self.linea_persistente.set_visible(False)
        self.ocultar_crosshair()
        self.canvas.draw()

    def set_tema(self, es_oscuro):
        self.is_dark_mode = es_oscuro
        self.aplicar_colores_tema()
        self.canvas.draw()

    def aplicar_colores_tema(self):
        """Applies theme-specific colors to the Matplotlib chart."""
        if self.is_dark_mode:
            bg_color = '#2d2d2d'
            self.color_titulo_actual = 'white'
            # Matplotlib toolbar icons are black by default.
            # In dark mode, force the toolbar background to light grey so icons remain visible.
            self.toolbar.setStyleSheet("background-color: #b0b0b0; border-radius: 4px;")
            if self.linea_persistente: self.linea_persistente.set_color('yellow')
            if self.crosshair_v:
                self.crosshair_v.set_color('#00FFFF')
                self.crosshair_h.set_color('#00FFFF')
        else:
            bg_color = 'white'
            self.color_titulo_actual = 'black'
            self.toolbar.setStyleSheet("")
            if self.linea_persistente: self.linea_persistente.set_color('red')
            if self.crosshair_v:
                self.crosshair_v.set_color('#FF00FF')
                self.crosshair_h.set_color('#FF00FF')

        self.figure.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)
        self.ax.set_title(f"Espacio Semántico ({self.nombre_modelo} + UMAP)", color=self.color_titulo_actual)

        self.canvas.draw()

    def actualizar_crosshair(self, x, y):
        self.crosshair_v.set_xdata([x, x])
        self.crosshair_h.set_ydata([y, y])
        self.crosshair_v.set_visible(True)
        self.crosshair_h.set_visible(True)
        self.canvas.draw()

    def ocultar_crosshair(self):
        self.crosshair_v.set_visible(False)
        self.crosshair_h.set_visible(False)
        # draw() is not called here to avoid slowing down; caller handles it
