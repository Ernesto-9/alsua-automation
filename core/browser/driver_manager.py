"""
Módulo de gestión del driver de Selenium
Maneja creación, validación y detección de errores del driver
"""
import time
import logging

logger = logging.getLogger(__name__)

class DriverManager:
    """Gestiona el ciclo de vida del driver de Selenium"""

    def __init__(self, login_function):
        """
        Args:
            login_function: Función que realiza el login y retorna un driver
        """
        self.driver = None
        self.login_function = login_function
        self.ultimo_error_driver = None

    def crear_driver_nuevo(self):
        """Crea un nuevo driver cerrando el anterior si existe"""
        try:
            logger.info("Creando nuevo driver...")

            if self.driver:
                try:
                    self.driver.quit()
                    time.sleep(2)
                except:
                    pass
                finally:
                    self.driver = None

            self.driver = self.login_function()

            if self.driver:
                logger.info("Nuevo driver creado exitosamente")
                self.ultimo_error_driver = None
                return True
            else:
                logger.error("Error en login GM")
                self.ultimo_error_driver = Exception("Login GM falló sin excepción específica")
                return False

        except Exception as e:
            logger.error(f"Error crítico creando driver: {e}")
            self.driver = None
            self.ultimo_error_driver = e
            return False

    def validar_driver(self):
        """
        Valida que el driver esté en una página correcta
        Returns:
            bool: True si el driver está válido, False si necesita recrearse
        """
        if not self.driver:
            return False

        try:
            current_url = self.driver.current_url
            if "softwareparatransporte.com" not in current_url:
                logger.warning("Driver en página incorrecta, necesita recrearse")
                return False
            return True
        except Exception as e:
            logger.warning(f"Driver corrupto detectado: {e}")
            return False

    def detectar_tipo_error(self, error):
        """
        Detecta el tipo de error basado en el mensaje

        Args:
            error: Exception o string con el error

        Returns:
            str: Tipo de error ('DRIVER_CORRUPTO', 'LOGIN_LIMIT', etc.)
        """
        error_str = str(error).lower()

        if any(keyword in error_str for keyword in [
            'invalid session', 'chrome not reachable', 'no such window',
            'session deleted', 'connection refused', 'stacktrace',
            'gethandleverifier', 'basethreadinitthunk', 'devtools'
        ]):
            return 'DRIVER_CORRUPTO'

        if any(keyword in error_str for keyword in [
            'limite de usuarios', 'user limit', 'maximum users',
            'máximo de usuarios', 'conexiones simultáneas'
        ]):
            return 'LOGIN_LIMIT'

        return 'DRIVER_CORRUPTO'

    def limpiar_driver(self):
        """Cierra y limpia el driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            finally:
                self.driver = None

    def obtener_driver(self):
        """Obtiene el driver actual, creándolo si no existe"""
        if not self.driver:
            self.crear_driver_nuevo()
        return self.driver
