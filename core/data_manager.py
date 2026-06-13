import os
import shutil
import pandas as pd
import numpy as np
from PySide6.QtCore import QObject, Signal
from matplotlib.path import Path


class DataManager(QObject):
    """
    Se encarga exclusivamente de la manipulación de datos y archivos.
    No sabe nada de la interfaz gráfica.
    """

    data_changed = Signal()

    def __init__(self, csv_path, trash_path):
        super().__init__()
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
            return pd.DataFrame()

    def _guardar_csv(self):
        try:
            self.df.to_csv(self.csv_path, index=False)
        except Exception as e:
            print(f"Error guardando CSV: {e}")

    def get_puntos_umap(self):
        if self.df.empty: return [], [], [], []
        df_activos = self.df[self.df['estado'] == 'activo']
        if df_activos.empty: return [], [], [], []
        columna_color = 'familia'
        if columna_color in df_activos.columns:
            colores = df_activos[columna_color].astype('category').cat.codes
        else:
            colores = np.zeros(len(df_activos))
        return (df_activos['x'].values,
                df_activos['y'].values,
                colores,
                df_activos.index.values)

    def get_info_registro(self, idx):
        return self.df.iloc[idx]

    def filtrar_por_lazo(self, vertices_lazo):
        if self.df.empty: return []
        path = Path(vertices_lazo)
        puntos = self.df[['x', 'y']].values
        mask = path.contains_points(puntos)
        indices = np.where(mask)[0]
        return [i for i in indices if self.df.iloc[i]['estado'] != 'borrado']

    def mover_a_descartes(self, indices):
        errores, movidos = 0, 0
        for idx in indices:
            registro = self.df.iloc[idx]
            ruta_origen = str(registro['ruta_absoluta'])
            carpeta_destino, ruta_destino = self._calcular_ruta_destino(ruta_origen)
            if not os.path.exists(carpeta_destino):
                os.makedirs(carpeta_destino, exist_ok=True)
            try:
                if os.path.exists(ruta_origen):
                    shutil.move(ruta_origen, ruta_destino)
                self.df.at[idx, 'estado'] = 'borrado'
                movidos += 1
            except Exception as e:
                print(f"Error moviendo {ruta_origen}: {e}")
                errores += 1
        if movidos > 0:
            self._guardar_csv()
            self.data_changed.emit()
        return movidos, errores

    def _calcular_ruta_destino(self, ruta_origen_absoluta):
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
        if self.df.empty: return pd.DataFrame()
        conteo = self.df.groupby(['nombre_cientifico', 'estado']).size().unstack(fill_value=0)
        if 'activo' not in conteo.columns: conteo['activo'] = 0
        if 'borrado' not in conteo.columns: conteo['borrado'] = 0
        metadata = self.df.groupby('nombre_cientifico')[['nombre_comun', 'familia', 'genero']].first()
        df_final = pd.concat([metadata, conteo], axis=1)
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
        return {
            'n_especies': self.df['nombre_cientifico'].nunique(),
            'n_familias': self.df['familia'].nunique(),
            'total_imgs': total_imgs,
            'activas': total_imgs - borradas,
            'borradas': borradas,
        }

    def restaurar_dataset_completo(self):
        indices_borrados = self.df[self.df['estado'] == 'borrado'].index
        restaurados, errores = 0, 0
        for idx in indices_borrados:
            registro = self.df.iloc[idx]
            ruta_original = str(registro['ruta_absoluta'])
            carpeta_deleted, ruta_actual_deleted = self._calcular_ruta_destino(ruta_original)
            try:
                if os.path.exists(ruta_actual_deleted):
                    os.makedirs(os.path.dirname(ruta_original), exist_ok=True)
                    shutil.move(ruta_actual_deleted, ruta_original)
                self.df.at[idx, 'estado'] = 'activo'
                restaurados += 1
            except Exception as e:
                print(f"Error restaurando {ruta_original}: {e}")
                errores += 1
        self._guardar_csv()
        self.data_changed.emit()
        return restaurados, errores
