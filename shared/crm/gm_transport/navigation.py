# navigate_to_create_viaje.py

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def navigate_to_create_viaje(driver):
    try:
        print("🧭 Navegando al módulo de viajes...")

        # Clic en el menú TRÁFICO
        trafico_xpath = "//img[contains(@src, 'TRAFICO1.jpg')]"
        trafico_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, trafico_xpath))
        )
        trafico_element.click()
        print("🟡 Clic en TRÁFICO")

        # Esperar a que aparezca la opción VIAJES y hacer clic
        viajes_xpath = "//img[contains(@src, 'VIAJES1.jpg')]"
        viajes_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, viajes_xpath))
        )
        viajes_element.click()
        print("🟢 Clic en VIAJES")

        # Esperar a que cargue el botón "Viaje" y hacer clic
        viaje_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "BTN_AGREGARVIAJES"))
        )
        viaje_btn.click()
        print("🟢 Botón 'Viaje' clickeado - Listo para llenar formulario")
        
        return True

    except Exception as e:
        print(f"❌ Error al navegar al módulo de viajes: {e}")
        return False