"""
Utilidades de interfaz de usuario para GM Transport
Manejo de alerts, calendarios, y elementos comunes de UI
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)


def cerrar_todos_los_alerts(driver, max_intentos=5):
    """
    Cierra todos los alerts/modals abiertos en la página

    Args:
        driver: WebDriver de Selenium
        max_intentos: Número máximo de alerts a cerrar

    Returns:
        int: Número de alerts cerrados
    """
    alerts_cerrados = 0
    for i in range(max_intentos):
        try:
            alert = driver.switch_to.alert
            alert.accept()
            alerts_cerrados += 1
            time.sleep(0.2)
        except:
            break
    return alerts_cerrados


def cerrar_calendarios_abiertos(driver):
    """
    Cierra calendarios abiertos enviando ESC

    Args:
        driver: WebDriver de Selenium
    """
    try:
        for _ in range(3):
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.3)
    except:
        pass


def reset_formulario(driver):
    """
    Resetea el formulario cerrando popups y navegando a crear viaje

    Args:
        driver: WebDriver de Selenium

    Returns:
        bool: True si el reset fue exitoso
    """
    try:
        cerrar_todos_los_alerts(driver)
        cerrar_calendarios_abiertos(driver)

        for _ in range(3):
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)

        # Import local para evitar circular
        from ..navigate_to_create_viaje import navigate_to_create_viaje
        time.sleep(1)
        navigate_to_create_viaje(driver)
        return True

    except Exception as e:
        logger.error(f"Error en reset_formulario: {e}")
        return False


def verificar_estado_pagina(driver):
    """
    Verifica que la página esté completamente cargada

    Args:
        driver: WebDriver de Selenium
    """
    try:
        estado_pagina = driver.execute_script("return document.readyState")
        if estado_pagina != "complete":
            time.sleep(1)
    except:
        pass
