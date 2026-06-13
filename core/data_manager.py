import logging
import os
import shutil
import pandas as pd
import numpy as np
from PySide6.QtCore import QObject, Signal
from matplotlib.path import Path

logger = logging.getLogger(__name__)


class DataManager(QObject):
    """Manages dataset state, CSV persistence, and file moves. Emits data_changed after any modification."""

    data_changed = Signal()

    def __init__(self, csv_path, trash_path):
        super().__init__()
        self.csv_path = csv_path
        self.trash_path = trash_path
        self.df = self._load_data()

    def _load_data(self):
        try:
            df = pd.read_csv(self.csv_path)
            if 'status' not in df.columns:
                df['status'] = 'active'
            logger.info("Loaded %d records from %s", len(df), self.csv_path)
            return df
        except FileNotFoundError:
            logger.error("CSV not found: %s", self.csv_path)
            return pd.DataFrame()
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as e:
            logger.error("Failed to parse CSV %s: %s", self.csv_path, e)
            return pd.DataFrame()

    def _guardar_csv(self):
        try:
            self.df.to_csv(self.csv_path, index=False)
            logger.info("CSV saved: %s", self.csv_path)
        except Exception as e:
            logger.error("Failed to save CSV: %s", e)

    def get_puntos_umap(self):
        if self.df.empty: return [], [], [], []
        df_activos = self.df[self.df['status'] == 'active']
        if df_activos.empty: return [], [], [], []
        columna_color = 'family'
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
        return [i for i in indices if self.df.iloc[i]['status'] != 'deleted']

    def mover_a_descartes(self, indices):
        errores, movidos = 0, 0
        for idx in indices:
            registro = self.df.iloc[idx]
            ruta_origen = str(registro['absolute_path'])
            carpeta_destino, ruta_destino = self._calcular_ruta_destino(ruta_origen)
            if not os.path.exists(carpeta_destino):
                os.makedirs(carpeta_destino, exist_ok=True)
            try:
                if os.path.exists(ruta_origen):
                    shutil.move(ruta_origen, ruta_destino)
                self.df.at[idx, 'status'] = 'deleted'
                movidos += 1
            except Exception as e:
                logger.error("Failed to move %s: %s", ruta_origen, e)
                errores += 1
        if movidos > 0:
            self._guardar_csv()
            self.data_changed.emit()
        logger.info("Discarded %d files (%d errors)", movidos, errores)
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
        conteo = self.df.groupby(['scientific_name', 'status']).size().unstack(fill_value=0)
        if 'active' not in conteo.columns: conteo['active'] = 0
        if 'deleted' not in conteo.columns: conteo['deleted'] = 0
        metadata = self.df.groupby('scientific_name')[['common_name', 'family', 'genus']].first()
        df_final = pd.concat([metadata, conteo], axis=1)
        df_final['total'] = df_final['active'] + df_final['deleted']
        return df_final.sort_values('total', ascending=False)

    def get_estadisticas_familias(self):
        if self.df.empty: return pd.DataFrame()
        conteo = self.df.groupby(['family', 'status']).size().unstack(fill_value=0)
        if 'active' not in conteo.columns: conteo['active'] = 0
        if 'deleted' not in conteo.columns: conteo['deleted'] = 0
        conteo['total'] = conteo['active'] + conteo['deleted']
        return conteo.sort_values('total', ascending=False)

    def get_resumen_global(self):
        if self.df.empty: return {}
        total_imgs = len(self.df)
        borradas = len(self.df[self.df['status'] == 'deleted'])
        return {
            'n_especies': self.df['scientific_name'].nunique(),
            'n_familias': self.df['family'].nunique(),
            'total_imgs': total_imgs,
            'activas': total_imgs - borradas,
            'borradas': borradas,
        }

    def restaurar_dataset_completo(self):
        indices_borrados = self.df[self.df['status'] == 'deleted'].index
        restaurados, errores = 0, 0
        for idx in indices_borrados:
            registro = self.df.iloc[idx]
            ruta_original = str(registro['absolute_path'])
            carpeta_deleted, ruta_actual_deleted = self._calcular_ruta_destino(ruta_original)
            try:
                if os.path.exists(ruta_actual_deleted):
                    os.makedirs(os.path.dirname(ruta_original), exist_ok=True)
                    shutil.move(ruta_actual_deleted, ruta_original)
                self.df.at[idx, 'status'] = 'active'
                restaurados += 1
            except Exception as e:
                logger.error("Failed to restore %s: %s", ruta_original, e)
                errores += 1
        self._guardar_csv()
        self.data_changed.emit()
        logger.info("Restored %d files (%d errors)", restaurados, errores)
        return restaurados, errores
