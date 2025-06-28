from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

# Ruta al chromedriver
ruta_driver = r"C:\Users\ernes\OneDrive\Documentos\AgencIA\Alsua\chromedriver\chromedriver-win64\chromedriver.exe"
servicio = Service(ruta_driver)

# Iniciar el navegador
driver = webdriver.Chrome(service=servicio)

# Abrir Google como prueba
driver.get("https://www.google.com")
print("✅ Chrome se abrió correctamente")

# Esperar unos segundos para que lo veas abierto
time.sleep(5)

# Cerrar navegador
driver.quit()
