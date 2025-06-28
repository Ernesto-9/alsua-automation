from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os

# Ruta al chromedriver (ajústala si la cambiaste)
chromedriver_path = r"C:\Users\ernes\OneDrive\Documentos\AgencIA\Alsua\chromedriver\chromedriver-win64\chromedriver.exe"

# URL del CRM
crm_url = "https://gmterpv8-41.gmtransport.co/GMTERPV8/PAGE_Dashboard/uDAAAJfpewMIAA"

# Crear una carpeta de perfil temporal aislada
user_data_dir = os.path.join(os.getcwd(), "chrome_temp_profile")

# Opciones de Chrome
options = Options()
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument("--start-maximized")  # Opcional
options.add_argument("--disable-infobars")  # Limpia advertencias
options.add_argument("--disable-extensions")

# Crear servicio y abrir navegador
service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

# Ir al CRM
driver.get(crm_url)

input("Presiona ENTER para cerrar el navegador...")
