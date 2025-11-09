"""
Sistema de Capturas de Pantalla Automáticas para Alsua Automation

Funcionalidades:
- Captura screenshots automáticamente cuando hay errores
- Guarda HTML de la página para análisis profundo
- Nombres descriptivos: TIMESTAMP_PREFACTURA_MODULO_ERROR.png
- Rotación automática: mantiene máximo 50 screenshots
"""

import os
from datetime import datetime
from pathlib import Path


class ScreenshotManager:
    """Gestiona la captura y rotación de screenshots de errores"""

    def __init__(self, carpeta="screenshots_errores", max_screenshots=50):
        """
        Inicializa el gestor de screenshots

        Args:
            carpeta: Carpeta donde guardar screenshots (default: screenshots_errores/)
            max_screenshots: Cantidad máxima de screenshots a mantener (default: 50)
        """
        self.carpeta = os.path.abspath(carpeta)
        self.max_screenshots = max_screenshots

        # Crear carpeta si no existe
        Path(self.carpeta).mkdir(parents=True, exist_ok=True)

    def capturar_error(self, driver, prefactura, modulo, detalle_error):
        """
        Captura screenshot cuando ocurre un error

        Args:
            driver: WebDriver de Selenium
            prefactura: Número de prefactura (ej: "8086992")
            modulo: Módulo donde ocurrió el error (ej: "gm_salida")
            detalle_error: Descripción del error

        Returns:
            str: Ruta completa del screenshot capturado
        """
        # Timestamp para el nombre
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Limpiar detalle_error para nombre de archivo
        nombre_safe = detalle_error[:50].replace(" ", "_").replace("/", "-").replace("\\", "-")
        nombre_safe = nombre_safe.replace(":", "-").replace("*", "-").replace("?", "-")
        nombre_safe = nombre_safe.replace('"', "").replace("<", "").replace(">", "").replace("|", "")

        # Nombre descriptivo del archivo
        filename = f"{timestamp}_{prefactura}_{modulo}_{nombre_safe}.png"
        ruta = os.path.join(self.carpeta, filename)

        try:
            # Capturar screenshot
            driver.save_screenshot(ruta)
            print(f"📸 Screenshot capturado: {filename}")

            # Rotar screenshots antiguos
            self.rotar_screenshots()

            return ruta
        except Exception as e:
            print(f"⚠️ Error al capturar screenshot: {e}")
            return None

    def capturar_con_html(self, driver, prefactura, modulo, detalle_error):
        """
        Captura screenshot Y el HTML source de la página

        Args:
            driver: WebDriver de Selenium
            prefactura: Número de prefactura
            modulo: Módulo donde ocurrió el error
            detalle_error: Descripción del error

        Returns:
            tuple: (ruta_screenshot, ruta_html)
        """
        # Capturar screenshot primero
        screenshot_path = self.capturar_error(driver, prefactura, modulo, detalle_error)

        if screenshot_path is None:
            return None, None

        # Guardar HTML con el mismo nombre
        html_path = screenshot_path.replace(".png", ".html")

        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"💾 HTML guardado: {os.path.basename(html_path)}")
            return screenshot_path, html_path
        except Exception as e:
            print(f"⚠️ Error al guardar HTML: {e}")
            return screenshot_path, None

    def rotar_screenshots(self):
        """
        Mantiene máximo N screenshots, eliminando los más antiguos
        Elimina también los archivos .html asociados
        """
        try:
            # Obtener todos los .png ordenados por fecha de modificación
            archivos = sorted(
                Path(self.carpeta).glob("*.png"),
                key=lambda x: x.stat().st_mtime
            )

            # Si hay más de max_screenshots, eliminar los más viejos
            if len(archivos) > self.max_screenshots:
                for archivo in archivos[:-self.max_screenshots]:
                    # Eliminar .png
                    archivo.unlink()

                    # Eliminar .html asociado si existe
                    html_file = archivo.with_suffix(".html")
                    if html_file.exists():
                        html_file.unlink()

                eliminados = len(archivos) - self.max_screenshots
                print(f"🗑️ Rotación: eliminados {eliminados} screenshots antiguos")
        except Exception as e:
            print(f"⚠️ Error en rotación de screenshots: {e}")


# Instancia global para uso fácil
_screenshot_manager_instance = None

def get_screenshot_manager():
    """Obtiene la instancia global del ScreenshotManager"""
    global _screenshot_manager_instance
    if _screenshot_manager_instance is None:
        _screenshot_manager_instance = ScreenshotManager()
    return _screenshot_manager_instance


# Funciones de conveniencia para importación directa
def capturar_screenshot(driver, prefactura, modulo, detalle_error):
    """Captura screenshot (wrapper para la instancia global)"""
    manager = get_screenshot_manager()
    return manager.capturar_error(driver, prefactura, modulo, detalle_error)


def capturar_screenshot_con_html(driver, prefactura, modulo, detalle_error):
    """Captura screenshot + HTML (wrapper para la instancia global)"""
    manager = get_screenshot_manager()
    return manager.capturar_con_html(driver, prefactura, modulo, detalle_error)


if __name__ == "__main__":
    print("Screenshot Manager - Sistema de Capturas Automáticas")
    print("=" * 60)
    print(f"Carpeta de screenshots: screenshots_errores/")
    print(f"Máximo de screenshots: 50")
    print(f"Formato: TIMESTAMP_PREFACTURA_MODULO_ERROR.png")
    print("=" * 60)
