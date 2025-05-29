from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import Qt
import base64
import json
from base64 import b64encode
import io

class AppiumIDPrinter:
    def __init__(self, image, elements):
        self.image = image
        self.elements = elements
        self.class_colors = {}
        self.color_palette = [
            QColor("red"), QColor("green"), QColor("blue"), QColor("purple"),
            QColor("darkorange"), QColor("teal"), QColor("brown"), QColor("magenta")
        ]

    def export_json_only(self, output_path):
      buffer = io.BytesIO()
      self.image.save(buffer, "PNG")
      b64_image = b64encode(buffer.getvalue()).decode("utf-8")

      simplified_elements = [
          {
              "x": x,
              "y": y,
              "w": w,
              "h": h,
              "class": elem.attrib.get("class") or elem.tag,
              "name": elem.attrib.get("resource-id") or elem.attrib.get("name") or "---"
          }
          for x, y, w, h, elem in self.elements
      ]

      with open(output_path, "w", encoding="utf-8") as f:
          json.dump({
              "base64": f"data:image/png;base64,{b64_image}",
              "elements": simplified_elements
          }, f, indent=2)

    def get_color_for_class(self, class_name):
        if class_name not in self.class_colors:
            color = self.color_palette[len(self.class_colors) % len(self.color_palette)]
            self.class_colors[class_name] = color.name()
        return self.class_colors[class_name]

    def export_html_overlay(self):
        temp_path = "_temp_export_overlay.png"
        self.image.save(temp_path)

        with open(temp_path, "rb") as f:
            image_data = f.read()
        b64_image = base64.b64encode(image_data).decode("utf-8")
        b64_string = f"data:image/png;base64,{b64_image}"

        simplified_elements = []
        for x, y, w, h, elem in self.elements:
            simplified_elements.append({
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "class": elem.attrib.get("class") or elem.tag,
                "name": elem.attrib.get("resource-id") or elem.attrib.get("name") or "---"
            })

        export_data = {
            "elements": simplified_elements,
            "image": b64_string
        }

        return json.dumps(export_data, indent=2)
