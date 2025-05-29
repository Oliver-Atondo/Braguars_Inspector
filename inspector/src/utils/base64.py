import base64

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