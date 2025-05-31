
import io

from PIL import Image, ImageQt
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsScene, QGraphicsView, QSizePolicy, QGraphicsPixmapItem
from PySide6.QtCore import Qt

from logic import AppiumDriver

class InspectionPanel(QWidget):
    def __init__(self, appium_driver: AppiumDriver):
        super().__init__()

        self._appium_driver = appium_driver
        ss_png = self._appium_driver.get_screenshot_as_png()
        ss_window_size = self._appium_driver.get_window_size()

        # Load and resize image
        image_px = Image.open(io.BytesIO(ss_png)).convert("RGB")
        self._view_width, self._view_height = ss_window_size["width"], ss_window_size["height"]
        # TODO: Maybe we don't need to store _image
        self._image = image_px.resize((self._view_width, self._view_height), Image.LANCZOS) 

        # Layout
        layout = QVBoxLayout(self)
        
        # Set image to the view with a mixmap
        self._scene = QGraphicsScene()
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)
        qt_image = ImageQt.ImageQt(self._image)
        self._pixmap_item.setPixmap(QPixmap.fromImage(qt_image))
        
        # View
        self._view = ZoomableGraphicsView(self._scene)
        self._view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._view.setMouseTracking(True)
        self._view.viewport().installEventFilter(self)
        self._view.viewport().setAttribute(Qt.WA_Hover, True)
        
        # Set event listener
        self._view.resizeEvent = self._on_view_resized
        
        layout.addWidget(self._view)


    def refresh_screenshot(self):
        ss_png = self._appium_driver.get_screenshot_as_png()
        image_px = Image.open(io.BytesIO(ss_png)).convert("RGB")
        self._image = image_px.resize((self._view_width, self._view_height), Image.LANCZOS)
        qt_image = ImageQt.ImageQt(self._image)
        self._pixmap_item.setPixmap(QPixmap.fromImage(qt_image))


    def _on_view_resized(self, event):
        QGraphicsView.resizeEvent(self._view, event)
        self._view.fitInView(self._pixmap_item, Qt.KeepAspectRatio)



class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zoom = 0
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.ScrollHandDrag)


    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
            self._zoom += 1
        else:
            zoom_factor = zoom_out_factor
            self._zoom -= 1

        self.scale(zoom_factor, zoom_factor)


    def mouseDoubleClickEvent(self, event):
        self.reset_zoom()
        super().mouseDoubleClickEvent(event)
        

    def reset_zoom(self):
        self.resetTransform()
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self._zoom = 0
