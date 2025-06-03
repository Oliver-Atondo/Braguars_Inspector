
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QWheelEvent, QKeyEvent

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zoom = 0
        self._ctrl_or_meta_pressed = False
        
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.NoDrag)


    def wheelEvent(self, event: QWheelEvent):
        modifier = event.modifiers()
        if modifier & (Qt.ControlModifier | Qt.MetaModifier):
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor

            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
                self._zoom += 1
            else:
                zoom_factor = zoom_out_factor
                self._zoom -= 1

            self.scale(zoom_factor, zoom_factor)
        else:
            super().wheelEvent(event)


    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Control, Qt.Key_Meta):
            self._ctrl_or_meta_pressed = True
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().keyPressEvent(event)

    
    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Control, Qt.Key_Meta):
            self._ctrl_or_meta_pressed = False
            self.setDragMode(QGraphicsView.NoDrag)
        return super().keyReleaseEvent(event)


    def mouseDoubleClickEvent(self, event):
        self.reset_zoom()
        super().mouseDoubleClickEvent(event)
        

    def reset_zoom(self):
        self.resetTransform()
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self._zoom = 0
