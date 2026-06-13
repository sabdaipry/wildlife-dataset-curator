import sys
import os
import shutil
import pandas as pd
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QFrame, QPushButton, QMessageBox,
                               QGraphicsView, QGraphicsScene, QListWidget, QListWidgetItem, 
                               QCheckBox, QAbstractItemView, QSplitter, QTableWidget, QTableWidgetItem,
                               QHeaderView, QTabWidget, QFileDialog)
from PySide6.QtGui import QPixmap, QColor, QPalette, QAction, QFont, QBrush
from PySide6.QtCore import Qt, QRectF, QTimer, Signal, QObject

# Matplotlib
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path
from matplotlib.colors import ListedColormap

# --- CONFIGURACIÓN GLOBAL ---
CONFIG = {
    "ARCHIVO_DATOS": "output/datos_clusters_vitb14.csv",
    "CARPETA_DESCARTES": "data/deleted",
    "ESTILOS": {
        "oscuro": """
            QMainWindow, QWidget { background-color: #2d2d2d; color: #e0e0e0; }
            QLabel { color: #e0e0e0; font-weight: bold; }
            QListWidget { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444; }
            /* Botón Tema: Gris medio con texto blanco brillante */
            QPushButton#btn_tema { background-color: #444; color: white; border: 1px solid #666; border-radius: 5px; font-size: 16px; }
            QPushButton#btn_tema:hover { background-color: #555; }
            /* Botón Borrar */
            QPushButton#btn_borrar { background-color: #8B0000; color: white; border-radius: 5px; padding: 5px; font-weight: bold; }
            QPushButton#btn_borrar:disabled { background-color: #442222; color: #888; }
            /* Checkbox */
            QCheckBox { color: #e0e0e0; spacing: 5px; }
            /* MessageBox */
            QMessageBox { background-color: #2d2d2d; color: white; }
            QMessageBox QLabel { color: white; }
            QMessageBox QPushButton { background-color: #444; color: white; min-width: 80px; padding: 5px; }
            /* Botón Lazo (Interruptor) */
            QPushButton#btn_lazo { background-color: #444; color: #aaa; border: 1px solid #666; border-radius: 4px; padding: 5px; }
            QPushButton#btn_lazo:checked { background-color: #008800; color: white; border: 1px solid #00aa00; }
            QPushButton#btn_lazo:hover { border: 1px solid #888; }
            /* Pestañas */
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #333; color: #aaa; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #555; color: white; font-weight: bold; border-bottom: 2px solid #00aa00; }
            /* --- TABLAS (QTableWidget) --- */
            QTableWidget {
                background-color: #1e1e1e;      /* Fondo de la tabla */
                color: #f0f0f0;                 /* Texto por defecto (Blanco humo) */
                gridline-color: #444444;        /* Líneas de la grilla */
                border: 1px solid #444;
                alternate-background-color: #2a2a2a; /* Color de la fila alternada */
            }
            /* Encabezados (Header) */
            QHeaderView::section {
                background-color: #333333;      /* Fondo del encabezado */
                color: white;                   /* Texto del encabezado */
                padding: 4px;
                border: 1px solid #555;
                font-weight: bold;
            }
            /* La esquina superior izquierda vacía */
            QTableCornerButton::section {
                background-color: #333333;
                border: 1px solid #555;
            }
        """,
        "claro": """
            QMainWindow, QWidget { background-color: #f0f0f0; color: black; }
            QLabel { color: black; font-weight: bold; }
            QListWidget { background-color: white; color: black; border: 1px solid #ccc; }
            /* Botón Tema: Blanco con borde */
            QPushButton#btn_tema { background-color: white; color: #333; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
            QPushButton#btn_tema:hover { background-color: #e6e6e6; }
            /* Botón Borrar */
            QPushButton#btn_borrar { background-color: #cc0000; color: white; border-radius: 5px; padding: 5px; font-weight: bold; }
            QPushButton#btn_borrar:disabled { background-color: #ffcccc; color: #999; }
            /* Checkbox */
            QCheckBox { color: black; spacing: 5px; }
            /* MessageBox */
            QMessageBox { background-color: #f0f0f0; color: black; }
            /* Botón Lazo (Interruptor) */
            QPushButton#btn_lazo { background-color: #e0e0e0; color: #555; border: 1px solid #ccc; border-radius: 4px; padding: 5px; }
            QPushButton#btn_lazo:checked { background-color: #4CAF50; color: white; border: 1px solid #388E3C; }
            QPushButton#btn_lazo:hover { border: 1px solid #999; }
            /* Pestañas */
            QTabWidget::pane { border: 1px solid #ccc; }
            QTabBar::tab { background: #e0e0e0; color: #555; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: white; color: black; font-weight: bold; border-bottom: 2px solid #008800; }
            /* --- TABLAS (QTableWidget) --- */
            QTableWidget {
                background-color: white;
                color: black;
                gridline-color: #ccc;
                alternate-background-color: #f9f9f9;
            }
            /* Encabezados (Header) */
            QHeaderView::section {
                background-color: #e0e0e0;
                color: black;
                padding: 4px;
                border: 1px solid #ccc;
            }
        """
    }
}

# =============================================================================
# CAPA 1: MODELO Y LÓGICA DE NEGOCIO (Backend)
# =============================================================================

class DataManager(QObject):
    """
    Se encarga exclusivamente de la manipulación de datos y archivos.
    No sabe nada de la interfaz gráfica.
    """

    data_changed = Signal()
    
    def __init__(self, csv_path, trash_path):
        super().__init__() # Init del QObject
        self.csv_path = csv_path
        self.trash_path = trash_path
        self.df = self._cargar_datos()
        
    def _cargar_datos(self):
        try:
            df = pd.read_csv(self.csv_path)
            if 'estado' not in df.columns:
                df['estado'] = 'activo'
            return df
        except FileNotFoundError:
            print(f"Error: No se encontró {self.csv_path}")
            return pd.DataFrame() # Retornar vacío para no romper la app
        
    def _guardar_csv(self):
        """Escribe el estado actual del DataFrame al disco."""
        try:
            self.df.to_csv(self.csv_path, index=False)
        except Exception as e:
            print(f"Error guardando CSV: {e}")


    def get_puntos_umap(self):
        """
        Retorna SOLO los puntos activos para graficar.
        Importante: Retorna también los índices reales del DF para mapear clicks.
        """
        if self.df.empty: return [], [], [], []
        
        # Filtramos solo los activos
        df_activos = self.df[self.df['estado'] == 'activo']
        
        if df_activos.empty: return [], [], [], []

        # Colores
        columna_color = 'familia'
        if columna_color in df_activos.columns:
            colores = df_activos[columna_color].astype('category').cat.codes
        else:
            colores = np.zeros(len(df_activos))
            
        # Retornamos X, Y, Colores e INDICES REALES (del DataFrame original)
        return (df_activos['x'].values, 
                df_activos['y'].values, 
                colores, 
                df_activos.index.values) # <--- Esto es clave para el mapeo

    def get_info_registro(self, idx):
        return self.df.iloc[idx]

    def filtrar_por_lazo(self, vertices_lazo):
        """Devuelve los índices de los puntos dentro del lazo."""
        if self.df.empty: return []
        path = Path(vertices_lazo)
        puntos = self.df[['x', 'y']].values
        mask = path.contains_points(puntos)
        indices = np.where(mask)[0]
        # Filtramos los que ya están borrados
        indices_validos = [i for i in indices if self.df.iloc[i]['estado'] != 'borrado']
        return indices_validos

    def mover_a_descartes(self, indices):
        """Mueve archivos respetando la jerarquía taxonómica."""
        errores, movidos = 0, 0
        for idx in indices:
            registro = self.df.iloc[idx]
            ruta_origen = str(registro['ruta_absoluta'])
            
            carpeta_destino, ruta_destino = self._calcular_ruta_destino(ruta_origen)
            
            if not os.path.exists(carpeta_destino):
                os.makedirs(carpeta_destino, exist_ok=True)
                
            try:
                # Movemos físicamente
                if os.path.exists(ruta_origen):
                    shutil.move(ruta_origen, ruta_destino)
                
                # Actualizamos flag en memoria
                self.df.at[idx, 'estado'] = 'borrado'
                movidos += 1
            except Exception as e:
                print(f"Error moviendo {ruta_origen}: {e}")
                errores += 1
        
        # Guardamos cambios en disco y avisamos
        if movidos > 0:
            self._guardar_csv()
            self.data_changed.emit()
                
        return movidos, errores

    def _calcular_ruta_destino(self, ruta_origen_absoluta):
        """Lógica pura de cálculo de rutas (la que arreglamos antes)."""
        ruta_norm = os.path.normpath(ruta_origen_absoluta)
        partes = ruta_norm.split(os.sep)
        nombre_archivo = partes[-1]
        
        try:
            idx_images = partes.index('images')
            estructura_intermedia = partes[idx_images+1:-1]
        except ValueError:
            estructura_intermedia = []

        carpeta_destino_final = os.path.join(self.trash_path, *estructura_intermedia)
        ruta_destino_final = os.path.join(carpeta_destino_final, nombre_archivo)
        return carpeta_destino_final, ruta_destino_final
    
    def get_estadisticas_detalladas(self):
        """
        Genera una tabla pivote con el balance de imágenes por especie.
        Retorna: DataFrame con columnas [Activo, Borrado, Total, familia, genero]
        """
        if self.df.empty: return pd.DataFrame()

        # 1. Agrupamos SOLO por Nombre Científico y Estado para los números
        # Esto asegura que "Puma" y "puma" (si hubiera error) o variantes de nombre común se sumen juntos.
        conteo = self.df.groupby(['nombre_cientifico', 'estado']).size().unstack(fill_value=0)
        
        # 'unstack' convierte los valores de 'estado' en columnas ('activo', 'borrado')
        # Si no hay borrados, la columna 'borrado' podría no crearse, aseguramos que existan:
        if 'activo' not in conteo.columns: conteo['activo'] = 0
        if 'borrado' not in conteo.columns: conteo['borrado'] = 0
        
        # 2. Extraemos la Metadata Representativa
        # Para cada nombre científico, tomamos el primer valor encontrado de los otros campos.
        # (Así unificamos si hay ligeras diferencias en los JSONs)
        metadata = self.df.groupby('nombre_cientifico')[['nombre_comun', 'familia', 'genero']].first()


        # 3. Unimos todo en un solo DataFrame
        # El índice de ambos es 'nombre_cientifico', así que Pandas los alinea automáticamente
        df_final = pd.concat([metadata, conteo], axis=1)
        
        # 4. Calculamos totales
        df_final['total_original'] = df_final['activo'] + df_final['borrado']
        
        return df_final.sort_values('total_original', ascending=False)
    
    
    
    def get_estadisticas_familias(self):
        if self.df.empty: return pd.DataFrame()
        
        conteo = self.df.groupby(['familia', 'estado']).size().unstack(fill_value=0)
        
        if 'activo' not in conteo.columns: conteo['activo'] = 0
        if 'borrado' not in conteo.columns: conteo['borrado'] = 0
        
        conteo['total_original'] = conteo['activo'] + conteo['borrado']
        return conteo.sort_values('total_original', ascending=False)
    
    def get_resumen_global(self):
        if self.df.empty: return {}
        
        total_imgs = len(self.df)
        borradas = len(self.df[self.df['estado'] == 'borrado'])
        activas = total_imgs - borradas
        
        return {
            'n_especies': self.df['nombre_cientifico'].nunique(),
            'n_familias': self.df['familia'].nunique(),
            'total_imgs': total_imgs,
            'activas': activas,
            'borradas': borradas
        }
    
    def restaurar_dataset_completo(self):
        """
        RESET TOTAL: Mueve todo de 'deleted' a su lugar original y resetea el CSV.
        """
        # Filtramos los que están marcados como borrados
        indices_borrados = self.df[self.df['estado'] == 'borrado'].index
        
        restaurados = 0
        errores = 0
        
        for idx in indices_borrados:
            registro = self.df.iloc[idx]
            ruta_original = str(registro['ruta_absoluta']) # A donde debe volver
            
            # Calculamos dónde está ahora (en deleted)
            carpeta_deleted, ruta_actual_deleted = self._calcular_ruta_destino(ruta_original)
            
            try:
                # Si el archivo existe en deleted, lo movemos atrás
                if os.path.exists(ruta_actual_deleted):
                    # Asegurar que la carpeta original exista (por si se borró vacía)
                    os.makedirs(os.path.dirname(ruta_original), exist_ok=True)
                    shutil.move(ruta_actual_deleted, ruta_original)
                
                # Reseteamos flag
                self.df.at[idx, 'estado'] = 'activo'
                restaurados += 1
                
            except Exception as e:
                print(f"Error restaurando {ruta_original}: {e}")
                errores += 1
        
        # Guardamos y notificamos
        self._guardar_csv()
        self.data_changed.emit()
        
        return restaurados, errores


# =============================================================================
# CAPA 2: COMPONENTES VISUALES (Widgets Reutilizables)
# =============================================================================

class UMAPWidget(QWidget):
    """Widget autónomo que maneja el gráfico Matplotlib y el Selector."""
    
    # Señales personalizadas: Comunican eventos al exterior sin saber quién escucha
    seleccion_realizada = Signal(list) # Emite lista de índices
    punto_cliqueado = Signal(int)      # Emite un solo índice
    deseleccion_total = Signal() # Avisa que se hizo click en la nada
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Toolbar y Canvas
        self.figure = Figure(figsize=(5, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Botón de Lazo
        layout_boton = QHBoxLayout()
        layout_boton.setContentsMargins(10, 0, 0, 0) # Un poco de margen a la izquierda

        self.btn_lazo = QPushButton("➰ Selección Múltiple")
        self.btn_lazo.setObjectName("btn_lazo") # Para el CSS
        self.btn_lazo.setCheckable(True)
        self.btn_lazo.setCursor(Qt.PointingHandCursor)
        self.btn_lazo.toggled.connect(self.toggle_lazo)
        
        layout_boton.addWidget(self.btn_lazo) # Agregamos el botón
        layout_boton.addStretch()             # EL RESORTE: Empuja todo a la izquierda

        layout.addWidget(self.toolbar)
        layout.addLayout(layout_boton)        # Agregamos este contenedor al layout principal
        
        # ------------------------
        
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)

        # 1. Creamos nuestra propia línea para "congelar" el dibujo
        # Inicialmente vacía. zorder alto para que se vea encima de los puntos.
        self.linea_persistente = None
        self.crosshair_v = None # Línea Vertical
        self.crosshair_h = None # Línea Horizontal
        self.selector = None

        self.puntos_cache = None
        self.indices_reales = None
        self.color_titulo_actual = 'black'
        self.es_modo_oscuro = False # Para recordar el estado al redibujar

        # Configuración inicial del selector (se recrea en graficar por seguridad si se limpia ax)
        self._inicializar_artistas()

    def _inicializar_artistas(self):
        """Crea los objetos gráficos (líneas) si no existen o tras un clear()."""
        # 1. Línea del Lazo (Roja, gruesa)
        self.linea_persistente, = self.ax.plot([], [], color='red', linewidth=2, alpha=0.9, zorder=10)
        
        # 2. CROSSHAIRS (Las líneas de guía)
        # Inicialmente invisibles (visible=False)
        # zorder=5 para que estén detrás del lazo pero sobre los puntos
        style = {'color': 'cyan', 'linestyle': '--', 'linewidth': 0.8, 'alpha': 0.8, 'visible': False, 'zorder': 5}
        self.crosshair_v = self.ax.axvline(x=0, **style)
        self.crosshair_h = self.ax.axhline(y=0, **style)

        # 3. Selector
        if self.selector: self.selector.disconnect_events()
        self.selector = LassoSelector(self.ax, onselect=self.on_lasso_finished, useblit=True)
        self.selector.set_active(False)

    def graficar(self, x, y, c, indices_reales):
        self.ax.clear()

        # Al hacer clear(), se borran los artistas, hay que recrearlos
        self._inicializar_artistas() 
        self.aplicar_colores_tema() # Re-aplicar colores correctos según tema actual 

        self.puntos_cache = np.column_stack((x, y))
        self.indices_reales = indices_reales # Guardamos el mapeo: IndiceVisual -> IndiceDF
        
        # COLORES POR FAMILIA
        # Calculamos cuántas familias únicas hay
        n_familias = int(np.max(c)) + 1 if len(c) > 0 else 1

        if n_familias <= 10: mi_cmap = 'tab10'
        elif n_familias <= 20: mi_cmap = 'tab20'
        else:
            cmap1 = mpl.colormaps['tab20']
            cmap2 = mpl.colormaps['tab20b']
            cmap3 = mpl.colormaps['tab20c']

            # Stackeamos los colores
            colores_combinados = np.vstack((
                cmap1(np.linspace(0, 1, 20)),
                cmap2(np.linspace(0, 1, 20)),
                cmap3(np.linspace(0, 1, 20))
            ))

            mi_cmap = ListedColormap(colores_combinados, name='tab60')

        self.ax.scatter(x, y, c=c, cmap=mi_cmap, s=15, picker=5)
        self.ax.axis('off')
        self.ax.set_title("Espacio Semántico (DINOv2_vitb14 + UMAP)", color=self.color_titulo_actual)
        
        self.canvas.draw()
        
        self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)

    def on_lasso_finished(self, verts):
        """Se ejecuta INMEDIATAMENTE al soltar el mouse."""
        
        # Ocultamos crosshairs si se usa el lazo
        self.ocultar_crosshair()

        # 1. ACTUALIZACIÓN VISUAL INSTANTÁNEA
        verts_np = np.array(verts)
        if len(verts_np) > 2:
            # Cerramos el polígono
            verts_np = np.vstack([verts_np, verts_np[0]])
            self.linea_persistente.set_data(verts_np[:, 0], verts_np[:, 1])
            self.linea_persistente.set_visible(True)
            
            # Forzamos el redibujado YA MISMO.
            # Esto congela la línea en la pantalla antes de que Python se ponga a pensar.
            self.canvas.draw()
        
        # 2. DELEGAMOS EL CÁLCULO PESADO (Math)
        # Usamos un timer de 1ms para dejar que la GUI respire y muestre la línea,
        # y recién después hacemos el cálculo de "quién está adentro".
        QTimer.singleShot(10, lambda: self._procesar_matematica_lazo(verts))

    def _procesar_matematica_lazo(self, verts):
        """Cálculo pesado que corre después de que la línea ya se dibujó."""
        if self.puntos_cache is None: return
        
        path = Path(verts)
        mask = path.contains_points(self.puntos_cache)
        indices_visuales = np.where(mask)[0]
        
        # TRADUCCIÓN CRÍTICA: De índice visual a índice del DataFrame
        if self.indices_reales is not None and len(indices_visuales) > 0:
            indices_finales = self.indices_reales[indices_visuales]
            self.seleccion_realizada.emit(indices_finales.tolist())
        else:
            # Si no seleccionó nada, enviamos lista vacía
            self.seleccion_realizada.emit([])

    def on_lasso_select(self, verts):

        # Ocultamos crosshairs si se usa el lazo
        # self.ocultar_crosshair()

        # 1. DIBUJO INMEDIATO (Para evitar la sensación de que se borra)
        # Copiamos los vertices del lazo recién terminado a nuestra línea persistente
        verts_np = np.array(verts)
        if len(verts_np) > 2:
            # Cerramos el polígono visualmente agregando el primer punto al final
            verts_np = np.vstack([verts_np, verts_np[0]])
            self.linea_persistente.set_data(verts_np[:, 0], verts_np[:, 1])
            self.canvas.draw_idle() # Forzamos el redibujado visual YA
        
        # 2. CÁLCULO (Puede tardar unos milisegundos, pero el usuario ya ve la línea)
        path = Path(verts)
        mask = path.contains_points(self.puntos_cache)
        indices = np.where(mask)[0]
        self.seleccion_realizada.emit(indices.tolist())


    def on_canvas_click(self, event):
        if event.inaxes != self.ax: return

        # Si estamos en modo lazo e iniciamos un click nuevo
        if self.btn_lazo.isChecked():
            # Limpiamos la línea vieja para empezar limpios
            self.linea_persistente.set_data([], [])
            self.linea_persistente.set_visible(False)
            self.ocultar_crosshair()
            self.canvas.draw()
        else:
            # Si es click simple en el fondo (sin pick), ocultamos crosshair
            # Nota: pick event ocurre antes. Si no hubo pick, limpiamos.
            # (Lo delegamos al padre vía deselección o lo hacemos aquí visualmente)
            pass

    def on_pick(self, event):
        if self.btn_lazo.isChecked(): return

        if len(event.ind) > 0: 
            idx_visual = event.ind[0]

            # MOSTRAR CROSSHAIR EN EL PUNTO SELECCIONADO
            # Obtenemos las coordenadas exactas del punto clickeado
            x_pt = self.puntos_cache[idx_visual, 0]
            y_pt = self.puntos_cache[idx_visual, 1]
            self.actualizar_crosshair(x_pt, y_pt)

            # TRADUCCIÓN: De visual a real
            if self.indices_reales is not None:
                idx_real = self.indices_reales[idx_visual]
                self.punto_cliqueado.emit(int(idx_real))

    # Sobreescribimos el mouseRelease para detectar click en vacío
    # Matplotlib a veces complica el "click en nada". Una forma 100% efectiva en Qt
    # es capturar el evento del canvas, pero usaremos un enfoque simple:
    # Si 'on_pick' no se dispara, asumimos click en vacio? No, mejor:
    # Usamos la señal button_press_event de matplotlib arriba y verificamos "contains".
    
    # CORRECCIÓN SIMPLE PARA CLICK VACÍO:
    # Vamos a confiar en que el usuario quiere deseleccionar si usa el botón derecho
    # O simplemente agregamos un botón "Limpiar".
    # PERO, para cumplir tu pedido de "click en otro lado":
    def mouseReleaseEvent(self, event):
        # Este método es de QT, no de Matplotlib.
        super().mouseReleaseEvent(event)
        # Si quisieras lógica compleja de clicks vacíos, iría aquí, 
        # pero dejémoslo simple con el botón de lazo.

    def toggle_lazo(self, activo):
        # Pequeño truco: Redibujamos antes de activar para asegurar que el fondo esté listo para blitting
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
    
    # Método auxiliar para borrar la línea roja
    def limpiar_dibujo_lazo(self):
        # Borramos nuestra línea manual
        self.linea_persistente.set_data([], [])
        self.linea_persistente.set_visible(False)
        self.ocultar_crosshair()
        self.canvas.draw()
        
    def set_tema(self, es_oscuro):
        self.es_modo_oscuro = es_oscuro
        self.aplicar_colores_tema()
        self.canvas.draw()

    def aplicar_colores_tema(self):
        """Aplica colores específicos al gráfico Matplotlib"""
        if self.es_modo_oscuro:
            bg_color = '#2d2d2d'
            self.color_titulo_actual = 'white' # Guardamos estado
            # El toolbar de matplotlib usa iconos negros por defecto.
            # En modo oscuro, forzamos el fondo del toolbar a un gris claro para que se vean los iconos.
            self.toolbar.setStyleSheet("background-color: #b0b0b0; border-radius: 4px;")
            # Colores de líneas para fondo oscuro
            if self.linea_persistente: self.linea_persistente.set_color('yellow')
            # Crosshair Cyan resalta mucho en oscuro
            if self.crosshair_v: 
                self.crosshair_v.set_color('#00FFFF')
                self.crosshair_h.set_color('#00FFFF')
        else:
            bg_color = 'white'
            self.color_titulo_actual = 'black' # Guardamos estado
            self.toolbar.setStyleSheet("") # Restaurar default
            self.linea_persistente.set_color('red')

            # Colores de líneas para fondo claro
            if self.linea_persistente: self.linea_persistente.set_color('red')
            # Crosshair Magenta o Negro resalta en blanco
            if self.crosshair_v: 
                self.crosshair_v.set_color('#FF00FF') 
                self.crosshair_h.set_color('#FF00FF')

        self.figure.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)
        self.ax.set_title("Espacio Semántico (DinoV2 + UMAP)", color=self.color_titulo_actual)

        self.canvas.draw()

    #  MÉTODOS PARA MANEJAR EL CROSSHAIR
    def actualizar_crosshair(self, x, y):
        self.crosshair_v.set_xdata([x, x])
        self.crosshair_h.set_ydata([y, y])
        self.crosshair_v.set_visible(True)
        self.crosshair_h.set_visible(True)
        self.canvas.draw()

    def ocultar_crosshair(self):
        self.crosshair_v.set_visible(False)
        self.crosshair_h.set_visible(False)
        # No llamamos a draw() aquí para no ralentizar, se llamará luego


class VisorZoomWidget(QGraphicsView):
    """Tu visor de imágenes original, encapsulado."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Comportamiento de arrastre (Pan)
        self.setDragMode(QGraphicsView.ScrollHandDrag) 
        self.setFrameShape(QFrame.NoFrame)             
        
        # Configuración de Anclas para que el zoom siga al mouse
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Ocultamos barras de scroll (el usuario navega con drag & drop)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # CONTROL DE ZOOM: 1.0 significa el tamaño "fit" original
        self._current_zoom = 1.0 

    def cargar_imagen(self, ruta):
        self.scene.clear()

        # Validaciones básicas
        if not os.path.exists(ruta): return False
        
        pixmap = QPixmap(ruta)
        if pixmap.isNull(): return False
        
        # Agregamos la imagen a la escena
        item = self.scene.addPixmap(pixmap)
        
        # Ajustamos la vista para que la imagen quepa entera al principio
        self.scene.setSceneRect(QRectF(pixmap.rect())) 
        self.fitInView(item, Qt.KeepAspectRatio) 
        return True

    def wheelEvent(self, event):
        """Maneja el zoom con la rueda del mouse"""
        
        # preguntamos si la escena tiene ítems.
        if not self.scene.items(): return False

        # Lógica de Zoom
        zoom_factor = 1.15

        if event.angleDelta().y() > 0:
            # --- ZOOM IN (Acercar) ---
            # Siempre permitido
            self.scale(zoom_factor, zoom_factor)
            self._current_zoom *= zoom_factor
        else:
            # --- ZOOM OUT (Alejar) ---
            # Calculamos a cuánto se iría el zoom si permitimos alejar
            nuevo_zoom_teorico = self._current_zoom / zoom_factor
            
            if nuevo_zoom_teorico < 1.0:
                # BLOQUEO: Si el nuevo zoom sería menor que el original (1.0),
                # calculamos el factor exacto para volver a 1.0 clavado y no bajar más.
                
                # Matematicamente: Queremos ir de _current_zoom a 1.0
                # Factor = Destino / Origen = 1.0 / _current_zoom
                if self._current_zoom > 1.0:
                    factor_correccion = 1.0 / self._current_zoom
                    self.scale(factor_correccion, factor_correccion)
                    self._current_zoom = 1.0
                
                # Si ya estamos en 1.0, no hacemos nada (ignoramos el scroll)
            else:
                # Si estamos lejos (ej: 2.5x), permitimos alejar normalmente
                self.scale(1 / zoom_factor, 1 / zoom_factor)
                self._current_zoom = nuevo_zoom_teorico
            
        event.accept() # Le decimos a Qt que ya manejamos el evento

# =============================================================================
# CAPA 3: VENTANA PRINCIPAL (Orquestador)
# =============================================================================

class AuditoriaMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Auditoría de Dataset")
        self.resize(1000, 700)
        
        # 1. Instanciar Lógica
        self.manager = DataManager(CONFIG["ARCHIVO_DATOS"], CONFIG["CARPETA_DESCARTES"])
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
        self.umap_widget = UMAPWidget()
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
        self.tab_stats = PestañaEstadisticas(self.manager)
        
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
        self.setStyleSheet(CONFIG["ESTILOS"]["oscuro"])
        # 2. Configurar Gráfico
        self.umap_widget.set_tema(True)
        # 3. Configurar Visor
        self.visor.setBackgroundBrush(QColor("#1e1e1e"))
        # 4. Icono Botón (Emoji Luna)
        self.btn_tema.setText("🌞") 
        self.btn_tema.setToolTip("Cambiar a modo claro")

        if self.ventana_stats: self.ventana_stats.set_tema(True)

    def aplicar_tema_claro(self):
        self.setStyleSheet(CONFIG["ESTILOS"]["claro"])
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


# =============================================================================
#  PESTAÑA DE ESTADÍSTICAS
# =============================================================================

class PestañaEstadisticas(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        
        
        # Layout Principal Vertical
        layout = QVBoxLayout(self)

        # --- 1. CABECERA: Resumen y Botón Exportar ---
        header_layout = QHBoxLayout()
        
        # Panel de Resumen (KPIs)
        self.lbl_resumen = QLabel("-")
        self.lbl_resumen.setStyleSheet("font-size: 14px; padding: 10px; background-color: rgba(0,0,0,0.1); border-radius: 5px;")
        header_layout.addWidget(self.lbl_resumen, stretch=1)
        
        # Botones derechos
        layout_btns_right = QVBoxLayout()
        
        self.btn_export = QPushButton("💾 Exportar Tablas")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet("background-color: #92c43e; border-radius: 5px; color: white; font-weight: bold; padding: 8px;")
        self.btn_export.clicked.connect(self.exportar_excel)
        
        # BOTÓN DE RESET
        self.btn_reset = QPushButton("🔄 Restaurar Dataset")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet("background-color: #59802a; border-radius: 5px; color: white; font-weight: bold; padding: 8px;")
        # self.btn_reset.setToolTip("Mueve todas las imágenes borradas de vuelta a su lugar original")
        self.btn_reset.clicked.connect(self.resetear_dataset)
        
        layout_btns_right.addWidget(self.btn_export)
        layout_btns_right.addWidget(self.btn_reset)
        
        header_layout.addLayout(layout_btns_right)
        layout.addLayout(header_layout)
        
        # --- 2. TABLA FAMILIAS ---
        layout.addWidget(QLabel("📊 Balance por Familias"))
        self.tabla_familias = QTableWidget()
        self.configurar_tabla(self.tabla_familias, ["Familia", "Originales", "Eliminadas", "Actuales"])
        layout.addWidget(self.tabla_familias, stretch=1)
        
        # --- 3. TABLA ESPECIES ---
        layout.addWidget(QLabel("🐾 Balance por Especies"))
        self.tabla_especies = QTableWidget()
        # Agregamos columna 'Género'
        cols_especies = ["Nombre Científico", "Nombre Común", "Familia", "Género", "Originales", "Eliminadas", "Actuales"]
        self.configurar_tabla(self.tabla_especies, cols_especies)
        layout.addWidget(self.tabla_especies, stretch=2)

        # Conectar señal
        self.manager.data_changed.connect(self.refrescar_todo)
        
        # Carga inicial
        self.refrescar_todo()

    def resetear_dataset(self):
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
        
        # Estirar la primera columna (Nombre/Familia) y ajustar las numéricas
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(columnas)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
        tabla.setSortingEnabled(True)
        tabla.setAlternatingRowColors(True)

    def refrescar_todo(self):
        self.actualizar_resumen()
        self.actualizar_tabla_familias()
        self.actualizar_tabla_especies()

    def actualizar_resumen(self):
        kpis = self.manager.get_resumen_global()
        if not kpis: return
        
        txt = (f"<b>Total Imágenes:</b> {kpis['total_imgs']} "
               f"(✅ {kpis['activas']} Activas | 🗑️ {kpis['borradas']} Eliminadas) &nbsp;|&nbsp; "
               f"<b>Especies:</b> {kpis['n_especies']} &nbsp;|&nbsp; "
               f"<b>Familias:</b> {kpis['n_familias']}")
        self.lbl_resumen.setText(txt)

    def actualizar_tabla_familias(self):
        df = self.manager.get_estadisticas_familias()
        t = self.tabla_familias
        t.setSortingEnabled(False)
        t.setRowCount(len(df))
        
        for row, (familia, registro) in enumerate(df.iterrows()):
            items = [
                QTableWidgetItem(str(familia)),
                QTableWidgetItem(), QTableWidgetItem(), QTableWidgetItem()
            ]
            # Asignar valores numéricos (Data role para sort)
            items[1].setData(Qt.DisplayRole, int(registro['total_original']))
            items[2].setData(Qt.DisplayRole, int(registro['borrado']))
            items[3].setData(Qt.DisplayRole, int(registro['activo']))
            
            for col, item in enumerate(items):
                t.setItem(row, col, item)
                
        t.setSortingEnabled(True)

    def actualizar_tabla_especies(self):
        df = self.manager.get_estadisticas_detalladas()
        t = self.tabla_especies
        t.setSortingEnabled(False)
        t.setRowCount(len(df))
        
        COLOR_ROJO = QColor("#ffcccc")
        COLOR_AMARILLO = QColor("#ffffcc")

        # Ahora iterrows devuelve:
        # indice -> El nombre científico (String)
        # registro -> La Serie con columnas [nombre_comun, familia, genero, activo, borrado, total...]
        for row, (n_cientifico, registro) in enumerate(df.iterrows()):
            
            # Extraemos los textos del registro, no del índice
            n_comun = str(registro['nombre_comun'])
            familia = str(registro['familia'])
            genero = str(registro['genero'])
            
            activo = int(registro['activo'])
            borrado = int(registro['borrado'])
            total = int(registro['total_original'])
            
            items = [
                QTableWidgetItem(str(n_cientifico)), # Índice (Científico)
                QTableWidgetItem(n_comun),
                QTableWidgetItem(familia),
                QTableWidgetItem(genero),
                QTableWidgetItem(), QTableWidgetItem(), QTableWidgetItem()
            ]
            
            # Datos numéricos
            items[4].setData(Qt.DisplayRole, total)
            items[5].setData(Qt.DisplayRole, borrado)
            items[6].setData(Qt.DisplayRole, activo)
            
            # Lógica de colores
            bg = None
            if activo == 0: bg = COLOR_ROJO
            elif activo < 10: bg = COLOR_AMARILLO
            
            for col, item in enumerate(items):
                if bg:
                    item.setBackground(bg)
                    item.setForeground(QColor("black"))
                else:
                    item.setForeground(QBrush()) # Color default
                
                t.setItem(row, col, item)
                
        t.setSortingEnabled(True)

    def exportar_excel(self):
        archivo, _ = QFileDialog.getSaveFileName(self, "Exportar Estadísticas", "estadisticas_dataset.xlsx", "Excel Files (*.xlsx)")
        if not archivo: return
        
        try:
            # Obtenemos los dataframes limpios
            df_fam = self.manager.get_estadisticas_familias()
            df_esp = self.manager.get_estadisticas_detalladas()
            
            # Exportamos usando Pandas (requiere openpyxl instalado)
            with pd.ExcelWriter(archivo) as writer:
                df_fam.to_excel(writer, sheet_name='Por Familias')
                df_esp.to_excel(writer, sheet_name='Por Especies')
            
            QMessageBox.information(self, "Éxito", f"Datos exportados correctamente a:\n{archivo}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{str(e)}\n\nAsegurate de tener instalada la librería 'openpyxl'.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Fuente un poco más grande para legibilidad
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = AuditoriaMainWindow()
    window.showMaximized()
    sys.exit(app.exec())