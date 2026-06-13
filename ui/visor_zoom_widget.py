import os
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QFrame
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QRectF


class VisorZoomWidget(QGraphicsView):
    """Image viewer widget with pan and zoom support."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setFrameShape(QFrame.NoFrame)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._current_zoom = 1.0

    def cargar_imagen(self, ruta):
        self.scene.clear()

        if not os.path.exists(ruta): return False

        pixmap = QPixmap(ruta)
        if pixmap.isNull(): return False

        item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(item, Qt.KeepAspectRatio)
        return True

    def wheelEvent(self, event):
        if not self.scene.items(): return

        zoom_factor = 1.15

        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
            self._current_zoom *= zoom_factor
        else:
            nuevo_zoom_teorico = self._current_zoom / zoom_factor

            if nuevo_zoom_teorico < 1.0:
                if self._current_zoom > 1.0:
                    factor_correccion = 1.0 / self._current_zoom
                    self.scale(factor_correccion, factor_correccion)
                    self._current_zoom = 1.0
            else:
                self.scale(1 / zoom_factor, 1 / zoom_factor)
                self._current_zoom = nuevo_zoom_teorico

        event.accept()
