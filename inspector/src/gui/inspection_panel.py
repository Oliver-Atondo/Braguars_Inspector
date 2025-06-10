
import io
import re

from rtree import index
from PIL import Image, ImageQt
from lxml import etree
from PySide6.QtGui import QPixmap, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsScene, QGraphicsView, QSizePolicy, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QEvent, QRectF

from logic import AppiumDriver
from .zoomable_view import ZoomableGraphicsView

class InspectionPanel(QWidget):
    def __init__(self, appium_driver: AppiumDriver):
        super().__init__()

        self._appium_driver = appium_driver
        self.screenshot = self._appium_driver.get_screenshot_as_png()
        ss_window_size = self._appium_driver.get_window_size()

        self._rtree = index.Index()
        self._element_map = {} # id -> (x, y, width, height)
        self._next_id = 0
        self._extract_elements_bounds(self._appium_driver.page_source)

        # Load and resize image
        image_px = Image.open(io.BytesIO(self.screenshot)).convert("RGB")
        self._view_width, self._view_height = ss_window_size["width"], ss_window_size["height"]
        image = image_px.resize((self._view_width, self._view_height), Image.LANCZOS) 

        # Layout
        layout = QVBoxLayout(self)
        
        # Set image to the view with a mixmap
        self._scene = QGraphicsScene()
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)
        qt_image = ImageQt.ImageQt(image)
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

        # Selected element
        self._current_selected_element = None

        # Selected element rect
        self._highlight_rect = self._scene.addRect(QRectF(), QPen(Qt.red, 3))
        self._clicked_rect = self._scene.addRect(QRectF(), QPen(Qt.green, 3))
        self._clicked_rect.setVisible(False)
        self._highlight_rect.setVisible(False)


    def refresh_screenshot(self):
        self.screenshot = self._appium_driver.get_screenshot_as_png()
        image_px = Image.open(io.BytesIO(self.screenshot)).convert("RGB")
        image = image_px.resize((self._view_width, self._view_height), Image.LANCZOS)
        qt_image = ImageQt.ImageQt(image)
        self._pixmap_item.setPixmap(QPixmap.fromImage(qt_image))
        self._extract_elements_bounds(self._appium_driver.page_source)


    def get_selected_element_bounds(self):
        rect = self._clicked_rect.rect()
        x = rect.x()
        y = rect.y()
        width = rect.width()
        height = rect.height()
        return (x, y, width, height)
        

    def eventFilter(self, watched, event):
        if watched is self._view.viewport():
            if event.type() == QEvent.MouseMove:
                pos = event.position() if hasattr(event, 'position') else event.localPos()
                scene_pos = self._view.mapToScene(int(pos.x()), int(pos.y()))
                mx, my = int(scene_pos.x()), int(scene_pos.y())

                hit = self._find_element_at_point(mx, my)
                if hit:
                    x, y, width, height = hit
                    self._highlight_rect.setRect(x, y, width, height)
                    self._highlight_rect.setVisible(True)
                else:
                    self._highlight_rect.setVisible(False)

            elif event.type() == QEvent.MouseButtonPress:
                if self._highlight_rect.isVisible:
                    self._clicked_rect.setRect(self._highlight_rect.rect())
                    self._clicked_rect.setVisible(True)

        return super().eventFilter(watched, event)


    def _find_element_at_point(self, mx: int, my: int):
        hits = list(self._rtree.intersection((mx, my, mx, my)))
        if not hits:
            return None
        
        best_hit = None
        min_area = float('inf')

        for hit_id in hits:
            x, y, width, height, element = self._element_map[hit_id]
            area = width * height
            if area < min_area:
                min_area = area
                best_hit = (x, y, width, height)

        return best_hit


    def _extract_elements_bounds(self, page_source: str):
        parser = etree.XMLParser(recover=True)
        root_element = etree.fromstring(page_source.encode("utf-8"), parser)
        self._extract_bounds(root_element)


    def _extract_bounds(self, element):
        for child in element:
            self._extract_bounds(child)
        
        bounds = element.get("bounds")
        if bounds:
            x1, y1, x2, y2 = [float(n) for n in re.findall(r"[\d.]+", bounds)]
            if all((x1, y1, x2, y2)):
                x, y, width, height, element = x1, y1, x2 - x1, y2 - y1, element
            else:
                return
        else:
            bounds_rect = (element.get("x"), element.get("y"), element.get("width"), element.get("height"))
            if all(bounds_rect):
                x, y, width, height = map(float, bounds_rect)
            else:
                return

        bound_box = (x, y, x + width, y + height)
        self._rtree.insert(self._next_id, bound_box)
        self._element_map[self._next_id] = (x, y, width, height, element)
        self._next_id += 1
                

    def _on_view_resized(self, event):
        QGraphicsView.resizeEvent(self._view, event)
        self._view.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
