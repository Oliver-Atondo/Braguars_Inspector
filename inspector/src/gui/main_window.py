
import io, os, uuid, re

from PIL import Image
from PySide6.QtWidgets import QMainWindow,  QWidget, QSplitter, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt

from logic import AppiumDriver
from .inspection_panel import InspectionPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Inspector")

        self._panels: list[InspectionPanel] = []
        self._main_layout = QVBoxLayout(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setLayout(self._main_layout)
        
        btn_bar = QHBoxLayout()
        self._refresh_btn = QPushButton("Refresh Screenshots")
        save_recording = QPushButton("Capture")

        btn_bar.addWidget(self._refresh_btn)
        btn_bar.addWidget(save_recording)
        save_recording.clicked.connect(self._save)

        self._main_layout.addLayout(btn_bar)


    def _save(self):
        for panel in self._panels:
            x, y, width, height = panel.get_selected_element_bounds()
            if not all((x, y, width, height)):
                continue

            output_dir = "../dataset/images/train"
            os.makedirs(output_dir, exist_ok=True)
            
            img_id = str(uuid.uuid4())
            file_path = os.path.join(output_dir, f"img{img_id}.png")
            screen_shoot = panel.screenshot
            with open(file_path, "wb") as f:
                f.write(screen_shoot)

            width_img, height_img = Image.open(io.BytesIO(screen_shoot)).convert('RGB').size

            label_id = 0 # TODO:
            center_x = (x + width/2)  * (1 / width_img)
            center_y = (y + height/2)  * (1 / height_img)
            width_rect = width * (1 / width_img)
            height_rect = height * (1 / height_img)

            output_dir = "../dataset/labels/train"
            os.makedirs(output_dir, exist_ok=True)

            label = f"{label_id} {center_x} {center_y} {width_rect} {height_rect}"
            file_path = os.path.join(output_dir, f"img{img_id}.txt")
            with open(file_path, "w") as f:
                f.write(label)

                
    def load(self, capabilities: dict):
        splitter = QSplitter(Qt.Horizontal)

        index = 0 # TODO: Refactor this
        for _, cap in capabilities.items():
            driver = AppiumDriver("http://localhost:4723", cap)
            panel = InspectionPanel(driver)
            self._panels.append(panel)
            splitter.addWidget(panel)
            splitter.setStretchFactor(index, 1)
            index += 1

        total_panels = splitter.count()
        panel_size = int(splitter.size().width() / total_panels)
        splitter.setSizes([panel_size] * total_panels)
        
        self._refresh_btn.clicked.connect(self._refresh_screenshots)
        self._main_layout.addWidget(splitter)

    
    def _refresh_screenshots(self):
        for panel in self._panels:
            panel.refresh_screenshot()
