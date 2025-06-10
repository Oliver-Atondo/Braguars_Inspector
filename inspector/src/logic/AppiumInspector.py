import io
import re
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QSplitter,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QSizePolicy
)
from PySide6.QtGui import QPixmap, QPen, QImage
from PySide6.QtCore import Qt, QRectF, QEvent
from PIL import Image, ImageQt
from lxml import etree

from selenium.webdriver.common.actions.interaction import POINTER
import base64
import time

class AppiumInspector(QWidget):
    def __init__(self, driver, platform):
        super().__init__()
        self.driver = driver
        self.platform = platform
        size = driver.get_window_size()
        self.vw, self.vh = size['width'], size['height']
        png = driver.get_screenshot_as_png()
        img_px = Image.open(io.BytesIO(png)).convert('RGB')
        self.dpr = img_px.width / self.vw
        px_w = int(self.vw * self.dpr)
        px_h = int(self.vh * self.dpr)
        cropped_px = img_px.crop((0, 0, px_w, px_h))
        logical = cropped_px.resize((self.vw, self.vh), Image.LANCZOS)
        self.original_image = logical

        src = driver.page_source
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(src.encode('utf-8'), parser)
        self.elements = []
        _extract_bounds(root)

        self.hovered_element = None
        self.current_clicked_element = None
        self.current_selected_element = None

        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        self.scene = QGraphicsScene()

        self.view = QGraphicsView(self.scene)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view.setMouseTracking(True)
        self.view.viewport().installEventFilter(self)
        self.view.viewport().setAttribute(Qt.WA_Hover, True)

        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        qt_image = ImageQt.ImageQt(self.original_image)
        pixmap = QPixmap.fromImage(qt_image)
        self.pixmap_item.setPixmap(pixmap)

        def on_view_resized(event):
            QGraphicsView.resizeEvent(self.view, event)
            self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        self.view.resizeEvent = on_view_resized
        self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        self.highlight_rect = self.scene.addRect(QRectF(), QPen(Qt.yellow, 2))
        self.clicked_rect = self.scene.addRect(QRectF(), QPen(Qt.green, 2))
        self.clicked_rect.setVisible(False)
        self.highlight_rect.setVisible(False)

        splitter.addWidget(self.view)

        self.info_container = QWidget()
        self.info_layout = QVBoxLayout(self.info_container)

        self.findby_table = QTableWidget()
        self.findby_table.setColumnCount(2)
        self.findby_table.setHorizontalHeaderLabels(["Locator Type", "Value"])
        self.findby_table.setWordWrap(True)
        self.findby_table.horizontalHeader().setStretchLastSection(True)
        self.findby_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.info_layout.addWidget(self.findby_table)

        self.attr_table = QTableWidget()
        self.attr_table.setColumnCount(2)
        self.attr_table.setHorizontalHeaderLabels(["Attribute", "Value"])
        self.attr_table.setWordWrap(True)
        self.attr_table.horizontalHeader().setStretchLastSection(True)
        self.attr_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.info_layout.addWidget(self.attr_table)

        splitter.addWidget(self.info_container)
        splitter.setSizes([self.original_image.width, 300])

    def show_element_info(self, elem):
        def val(key):
            return elem.attrib.get(key, '').strip() or 'null'

        if self.platform == "iOS":
            headers = [
                ("accessibility id", val('name') or val('label') or val('content-desc')),
                ("-ios class chain", build_ios_class_chain(elem)),
                ("-ios predicate string", build_ios_predicate_string(elem)),
                ("xpath", build_xpath_from_hierarchy(elem, 'iOS'))
            ]
        elif self.platform == "Android":
            headers = [
                ("resource-id", val("resource-id")),
                ("-android uiautomator", build_android_ui_automator(elem)),
                ("xpath", build_xpath_from_hierarchy(elem, 'android'))
            ]
        else:
            headers = [("unknown platform", "No headers available")]

        self.findby_table.setRowCount(len(headers))
        for i, (key, value) in enumerate(headers):
            self.findby_table.setItem(i, 0, QTableWidgetItem(key))
            self.findby_table.setItem(i, 1, QTableWidgetItem(value))

        attr_items = list(elem.attrib.items())
        if elem.text and elem.text.strip():
            attr_items.append(("text", elem.text.strip()))

        self.attr_table.setRowCount(len(attr_items))
        for i, (k, v) in enumerate(attr_items):
            self.attr_table.setItem(i, 0, QTableWidgetItem(k))
            self.attr_table.setItem(i, 1, QTableWidgetItem(v))

        for x, y, w, h, el in self.elements:
            if el is elem:
                self.highlight_rect.setRect(x, y, w, h)
                self.highlight_rect.setVisible(True)
                break

    def refresh_screenshot(self):
        png = self.driver.get_screenshot_as_png()
        img_px = Image.open(io.BytesIO(png)).convert('RGB')
        px_w = int(self.vw * self.dpr)
        px_h = int(self.vh * self.dpr)
        cropped_px = img_px.crop((0, 0, px_w, px_h))
        logical = cropped_px.resize((self.vw, self.vh), Image.LANCZOS)
        self.original_image = logical

        qt_image = ImageQt.ImageQt(self.original_image)
        pixmap = QPixmap.fromImage(qt_image)
        self.pixmap_item.setPixmap(pixmap)

        src = self.driver.page_source
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(src.encode('utf-8'), parser)
        self.elements.clear()
        self._extract_bounds(root)

        self.highlight_rect.setVisible(False)
        self.clicked_rect.setVisible(False)

    def print_all_ids(self):
        qt_image = ImageQt.ImageQt(self.original_image)
        device_image = QImage(qt_image)
        #generator = AppiumIDPrinter(device_image, self.elements)
        #return generator.export_html_overlay()

    def calculate_bounds(self, e):
        if self.platform == 'iOS':
            try:
                rect = e.rect  # WebElement.rect ya extrae x, y, width, height en dict
                x = rect.get("x", 0)
                y = rect.get("y", 0)
                w = rect.get("width", 0)
                h = rect.get("height", 0)
                return [[int(x), int(x + w - 1)], [int(y), int(y + h - 1)]]
            except Exception as e:
                print(f"⚠️ Error al calcular bounds para iOS: {e}")
                return None
        elif self.platform == 'Android':
            try:
                bounds_str = e.get_attribute("bounds")
                nums = list(map(int, re.findall(r'\d+', bounds_str)))
                if len(nums) == 4:
                    x1, y1, x2, y2 = nums
                    return [[x1, x2], [y1, y2]]
            except Exception as e:
                print(f"❌ Error al parsear bounds Android: {e}")
        return None

    def replay_element_click(self, elem):
        visible = False
        xpath = ''
        image = ''

        if self.platform == 'iOS':
            xpath = build_xpath_from_hierarchy(elem, 'iOS')
        else:
            xpath = build_xpath_from_hierarchy(elem, 'android')

        phone_size = self.driver.get_window_size()
        phone_w = phone_size['width']
        phone_h = phone_size['height'] * 0.94

        for i in range(3):
            try: 
                elem = self.driver.find_element("xpath", xpath)
            except:
                visible = False
                self.scroll_down()
                self.refresh_screenshot()
                time.sleep(2)

            bounds = self.calculate_bounds(elem)
            
            if not bounds:
                print("❌ No se pudieron determinar los bounds del elemento.")
                return
            
            [x1, x2], [y1, y2] = bounds
        
            if 0 <= x1 < phone_w and 0 <= y1 < phone_h and x2 <= phone_w and y2 <= phone_h:
                visible = True
                image = self.capture_element_base64(elem)
                print(image)
                break
            else:
                visible = False
                self.scroll_down()
                self.refresh_screenshot()
                time.sleep(2)

        if visible:
            self.driver.find_element("xpath", xpath).click()
            time.sleep(2)
            self.refresh_screenshot()
            return image

    def tap_element_center(self, bounds):
        try:
            if bounds and len(bounds) == 4:
                x1, y1, x2, y2 = bounds
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                self.driver.tap([(cx, cy)], 100)
            else:
                print("⚠ Bounds inválidos o incompletos para tap.")
        except Exception as e:
            print(f"❌ Error en tap_element_center: {e}")

    def eventFilter(self, obj, event):
        if obj is self.view.viewport():
            if event.type() == QEvent.MouseMove:
                pos = event.position() if hasattr(event, 'position') else event.localPos()
                scene_pos = self.view.mapToScene(int(pos.x()), int(pos.y()))
                mx, my = int(scene_pos.x()), int(scene_pos.y())

                hit = None
                min_area = None
                for x, y, w, h, el in self.elements:
                    if x <= mx <= x + w and y <= my <= y + h:
                        area = w * h
                        if min_area is None or area < min_area:
                            min_area = area
                            hit = (x, y, w, h, el)

                if hit:
                    x, y, w, h, el = hit
                    self.highlight_rect.setRect(x, y, w, h)
                    self.highlight_rect.setVisible(True)
                    self.hovered_element = el
                else:
                    self.highlight_rect.setVisible(False)
                    self.hovered_element = None

            elif event.type() == QEvent.MouseButtonPress:
                if self.hovered_element is not None:
                    self.current_clicked_element = self.hovered_element
                    self.current_selected_element = self.current_clicked_element
                    self.current_clicked_element = self.hovered_element
                    self.show_element_info(self.current_clicked_element)
                    for x, y, w, h, el in self.elements:
                        if el is self.current_clicked_element:
                            self.clicked_rect.setRect(x, y, w, h)
                            self.clicked_rect.setVisible(True)
                            break
                    self.highlight_rect.setVisible(True)

        return super().eventFilter(obj, event)

    def return_selected_elem(self):
        return self.current_selected_element
    
    def capture_element_base64(self, elem):
        try:
            if self.platform == "Android":
                bounds_str = elem.get_attribute("bounds")
                if bounds_str:
                    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                    else:
                        print("[⚠] No se pudieron extraer las coordenadas de bounds.")
                        return None
                else:
                    print("[⚠] El atributo 'bounds' no está disponible en el elemento.")
                    return None

            elif self.platform == "iOS":
                rect = elem.rect
                x = rect.get("x", 0)
                y = rect.get("y", 0)
                w = rect.get("width", 0)
                h = rect.get("height", 0)

                if w == 0 or h == 0:
                    print("[⚠] Dimensiones inválidas para el rect de iOS.")
                    return None

                x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)

            else:
                print("[⚠] Plataforma desconocida para captura de elemento.")
                return None

            # Recortar imagen y convertir a base64
            cropped = self.original_image.crop((x1, y1, x2, y2))
            buffered = io.BytesIO()
            cropped.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")

        except Exception as e:
            print(f"[⚠] Error capturando imagen del elemento: {e}")
            return None

    def scroll_down(self):
            try:
                platform = self.driver.capabilities.get("platformName", "").lower()
                if platform == "android":
                    size = self.driver.get_window_size()
                    x = size['width'] // 2
                    start_y = int(size['height'] * 0.8)
                    end_y = int(size['height'] * 0.2)
                    self.driver.swipe(x, start_y, x, end_y, 300)
                    print("🔻 Android scroll ejecutado.")
                elif platform == "ios":
                    self.driver.execute_script("mobile: swipe", {"direction": "up"})
                    print("🔺 iOS scroll ejecutado.")
                else:
                    print("⚠ Plataforma desconocida.")
            except Exception as e:
                print(f"❌ Error en scroll_down: {e}")

    def scroll_up(self):
            try:
                if self.platform == "Android":
                    print("↕ Scroll arriba Android")
                    self.driver.find_element_by_android_uiautomator(
                        'new UiScrollable(new UiSelector().scrollable(true)).scrollBackward()'
                    )
                elif self.platform == "iOS":
                    print("↕ Scroll arriba iOS")
                    self.driver.execute_script("mobile: swipe", {
                        "direction": "down"
                    })
            except Exception as e:
                print(f"❌ Error haciendo scroll arriba: {e}")

    def scroll_to_top(self, attempts=5):
            for _ in range(attempts):
                self.scroll_up()

    def is_element_visible(self, elem):
            try:
                if self.platform == "Android" and elem.attrib.get("bounds"):
                    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", elem.attrib["bounds"])
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        # Verifica que el centro del elemento esté en pantalla
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        return 0 <= cx <= self.vw and 0 <= cy <= self.vh
                elif self.platform == "iOS":
                    x = float(elem.attrib.get("x", 0))
                    y = float(elem.attrib.get("y", 0))
                    w = float(elem.attrib.get("width", 0))
                    h = float(elem.attrib.get("height", 0))
                    cx = x + w / 2
                    cy = y + h / 2
                    return 0 <= cx <= self.vw and 0 <= cy <= self.vh
            except:
                return False
            return False

def build_xpath_from_hierarchy(elem, platform="iOS"):
    parts = []

    while elem is not None:
        tag = elem.tag
        attrib = elem.attrib

        predicate = ""
        if platform.lower() == "ios":
            if "name" in attrib and attrib["name"].strip():
                predicate = f"[@name='{attrib['name']}']"
                parts.insert(0, f"{tag}{predicate}")
                break  # ¡corta aquí! este es el ancla
            elif "label" in attrib and attrib["label"].strip():
                predicate = f"[@label='{attrib['label']}']"
                parts.insert(0, f"{tag}{predicate}")
                break
        elif platform.lower() == "android":
            if "resource-id" in attrib and attrib["resource-id"].strip():
                predicate = f"[@resource-id='{attrib['resource-id']}']"
                parts.insert(0, f"{tag}{predicate}")
                break
            elif "text" in attrib and attrib["text"].strip():
                predicate = f"[@text='{attrib['text']}']"
                parts.insert(0, f"{tag}{predicate}")
                break

        parts.insert(0, tag)
        elem = elem.getparent()

    xpath = "//" + "/".join(parts)
    return xpath

def build_ios_predicate_string(elem):
    attrib = elem.attrib
    if "name" in attrib and attrib["name"].strip():
        return f"name == '{attrib['name'].strip()}'"
    elif "label" in attrib and attrib["label"].strip():
        return f"label == '{attrib['label'].strip()}'"
    elif "value" in attrib and attrib["value"].strip():
        return f"value == '{attrib['value'].strip()}'"
    else:
        return None

def build_ios_class_chain(elem):
    tag = elem.tag
    name = elem.attrib.get("name", "").strip()
    label = elem.attrib.get("label", "").strip()

    if name:
        return f"**/{tag}[`name == '{name}'`]"
    elif label:
        return f"**/{tag}[`label == '{label}'`]"
    else:
        return f"**/{tag}"

def build_android_ui_automator(elem):
    attrib = elem.attrib
    if "resource-id" in attrib and attrib["resource-id"].strip():
        return f'new UiSelector().resourceId("{attrib["resource-id"].strip()}")'
    elif "text" in attrib and attrib["text"].strip():
        return f'new UiSelector().text("{attrib["text"].strip()}")'
    elif "class" in attrib and attrib["class"].strip():
        return f'new UiSelector().className("{attrib["class"].strip()}")'
    else:
        return None
    


def _extract_bounds(self, elem):
    for child in elem:
        _extract_bounds(child)

    b = elem.get('bounds')
    if b:
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            self.elements.append((x1, y1, x2 - x1, y2 - y1, elem))
    else:
        coords = (elem.get('x'), elem.get('y'), elem.get('width'), elem.get('height'))
        if all(coords):
            try:
                x, y, w, h = map(float, coords)
                self.elements.append((int(x), int(y), int(w), int(h), elem))
            except ValueError:
                pass