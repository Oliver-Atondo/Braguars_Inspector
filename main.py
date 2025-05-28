#!/usr/bin/env python3
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QSplitter, QVBoxLayout, QHBoxLayout, QPushButton
)
from PySide6.QtCore import Qt
from appium.options.common.base import AppiumOptions
from appium import webdriver
from LOGIC.AppiumInspector import AppiumInspector
from LOGIC.AppiumRecorder import AppiumRecorder
import base64
import cv2
import numpy as np
from PySide6.QtGui import QImage

def save_base64_to_png(base64_string, output_path):
    try:
        if not base64_string:
            print("⚠️ La cadena base64 está vacía o es None. No se puede guardar la imagen.")
            return
        image_data = base64.b64decode(base64_string)
        with open(output_path, "wb") as f:
            f.write(image_data)
        print(f"✅ Imagen guardada exitosamente en: {output_path}")
    except Exception as e:
        print(f"❌ Error al guardar la imagen: {e}")

def launch_dual_inspector(caps1: dict, caps2: dict):
    print("[INFO] Lanzando Dual Inspector con:")
    print("iOS Caps:", caps1)
    print("Android Caps:", caps2)

    try:
        opts1 = AppiumOptions()
        for k, v in caps1.items():
            opts1.set_capability(f"appium:{k}", v)

        opts2 = AppiumOptions()
        for k, v in caps2.items():
            opts2.set_capability(f"appium:{k}", v)

        driver1 = webdriver.Remote("http://localhost:4723", options=opts1)
        driver2 = webdriver.Remote("http://localhost:4723", options=opts2)

        app = QApplication(sys.argv)
        window = QWidget()
        window.setWindowTitle("Dual-Device Appium Inspector")

        main_layout = QVBoxLayout(window)
        window.setLayout(main_layout)

        btn_bar = QHBoxLayout()
        print_btn = QPushButton("Print All IDs (both)")
        refresh_btn = QPushButton("Refresh Screenshots")
        take_a_shot = QPushButton("Record Step")
        save_recording = QPushButton("Save Recording")
        btn_bar.addWidget(print_btn)
        btn_bar.addWidget(refresh_btn)
        btn_bar.addWidget(take_a_shot)
        btn_bar.addWidget(save_recording)
        main_layout.addLayout(btn_bar)

        splitter = QSplitter(Qt.Horizontal)
        panel1 = AppiumInspector(driver1, "iOS")
        panel2 = AppiumInspector(driver2, "Android")
        splitter.addWidget(panel1)
        splitter.addWidget(panel2)
        splitter.setSizes([400, 800])
        main_layout.addWidget(splitter)

        recorder = AppiumRecorder()
        
        def save_record():
            ios_elem = panel1.return_selected_elem()
            android_elem = panel2.return_selected_elem()

            if ios_elem is not None and android_elem is not None:
                ios_img_b64 = panel1.replay_element_click(ios_elem)
                android_img_b64 = panel2.replay_element_click(android_elem)
                save_base64_to_png(ios_img_b64, "ios_element.png")
                save_base64_to_png(android_img_b64, "android_element.png")

                recorder.record_dual_step(ios_elem, android_elem, ios_img_b64, android_img_b64)
                print("[✓] Paso sincronizado guardado.")
            else:
                print("⚠ Debes seleccionar un elemento en ambos dispositivos.")

        def on_print_all():
            iOSJSONvalues = panel1.print_all_ids()
            androidJSONvalues = panel2.print_all_ids()
            #eel.receive_overlay_jsons(iOSJSONvalues, androidJSONvalues)

        def refresh_screenshots():
            panel1.refresh_screenshot()
            panel2.refresh_screenshot()

        def save_steps():
            recorder.save_to_file()

        def qimage_to_numpy(qimage: QImage) -> np.ndarray:
            qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
            width = qimage.width()
            height = qimage.height()
            ptr = qimage.bits()
            arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 3))
            return arr

        def actua_testing():
            qimage = panel2.print_all_ids()
            img = qimage_to_numpy(qimage)
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            template = cv2.imread('android_element.png', 0)
            if template is None:
                print("Error: No se pudo cargar 'android_element.png'")
                return

            w, h = template.shape[::-1]

            res = cv2.matchTemplate(img_gray, template, cv2.TM_SQDIFF)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            top_left = min_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)
            bounds = [top_left[0], top_left[1], bottom_right[0], bottom_right[1]]
            print(bounds)
            panel2.tap_element_center(bounds)


        print_btn.clicked.connect(actua_testing)
        refresh_btn.clicked.connect(refresh_screenshots)
        take_a_shot.clicked.connect(save_record)
        save_recording.clicked.connect(save_steps)

        window.resize(1200, 800)
        window.show()
        app.exec()

    except Exception as e:
        print(f"[ERROR] No se pudo lanzar el inspector dual: {e}")

if __name__ == "__main__":
    launch_dual_inspector(
        caps1={
            "platformName": "iOS",
            "platformVersion": "18.2.1",
            "deviceName": "iPhone14ProMax",
            "automationName": "XCUITest",
            "udid": "00008120-0002346C2208201E",
            "includeSafariInWebviews": True,
            "newCommandTimeout": 3600,
            "connectHardwareKeyboard": True
        },
        caps2={
            "platformName": "ANDROID",
            "appPackage": "com.dexcom.g7",
            "automationName": "uiautomator2",
            "udid": "192.168.1.198:5555",
            "deviceName": "Galaxy S21 5G",
            "noReset": True,
            "fullReset": False,
            "newCommandTimeout": 3600
        }
    )