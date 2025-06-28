from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

# Credenciales y URL
EMPRESA = "TSU9608131A7"
USUARIO = "ERNESTOU"
CONTRASENA = "eRN#$TO.#\"/2025"
CRM_URL = "https://gmterpv8-41.gmtransport.co/GMTERPV8/"

# Ruta al chromedriver y carpeta de perfil temporal
CHROMEDRIVER_PATH = r"C:\Users\MONITOR3\Documents\ROBOTS\VACIO\chromedriver-win64\\chromedriver.exe"
USER_DATA_DIR = os.path.join(os.getcwd(), "chrome_temp_profile")

def launch_driver():
    options = Options()
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def login(driver):
    driver.get(CRM_URL)
    time.sleep(3)

    try:
        empresa_input = driver.find_element(By.ID, "EDT_EMPRESA")
        usuario_input = driver.find_element(By.ID, "EDT_USUARIO")
        contrasena_input = driver.find_element(By.ID, "EDT_CONTRASENA")
        login_button = driver.find_element(By.XPATH, "//span[text()='INICIAR SESIÓN']")

        empresa_input.clear()
        empresa_input.send_keys(EMPRESA)
        usuario_input.clear()
        usuario_input.send_keys(USUARIO)
        contrasena_input.clear()
        contrasena_input.send_keys(CONTRASENA)

        login_button.click()
        print("🕒 Esperando post-login...")
        time.sleep(5)

        # Manejo de alerta por sesión duplicada
        try:
            alert = driver.switch_to.alert
            print(f"⚠️ Alerta detectada: {alert.text}")
            alert.accept()
            print("✅ Alerta aceptada")
            time.sleep(5)
        except:
            print("🟢 No hubo alerta de sesión duplicada")

        # Manejo de popup molesto de bienvenida
        try:
            print("🔍 Buscando popup de bienvenida...")
            popup_checkbox = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.ID, "CBOX_CHECKBOX1_1"))
            )
            popup_checkbox.click()
            print("☑️ Casilla 'No volver a mostrar' marcada")

            ok_button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "btnvalignmiddle"))
            )
            ok_button.click()
            print("✅ Popup cerrado correctamente")
            time.sleep(2)
        except:
            print("🟢 No apareció popup de bienvenida")

        # Confirmación de login exitoso
        try:
            driver.find_element(By.XPATH, "//img[contains(@src, 'TRAFICO')]")
            print("✅ Login exitoso detectado")
            return True
        except:
            print("⚠️ No se detectó menú de tráfico. Posible fallo en login.")
            return False

    except Exception as e:
        print(f"❌ Error en login: {e}")
        return False

def login_to_gm():
    print("🚀 Iniciando login con perfil temporal...")
    try:
        driver = launch_driver()
        print("✅ Chrome lanzado")
    except Exception as e:
        print(f"❌ Error al lanzar Chrome: {e}")
        return None

    print("🔐 Realizando login...")
    success = login(driver)
    if success:
        print("🎉 Login exitoso y sesión iniciada")
        return driver
    else:
        print("❌ Falló el login")
        driver.quit()
        return None

# -------------------------------------------------------------------
# PRUEBA FINAL: login + navegación a creación de viaje
# -------------------------------------------------------------------
if __name__ == "__main__":
    from navigate_to_create_viaje import navigate_to_create_viaje

    driver = login_to_gm()
    if driver:
        navigate_to_create_viaje(driver)
        input("🟢 Presiona ENTER cuando termines de revisar la pantalla...")
