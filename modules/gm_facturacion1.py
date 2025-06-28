from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from gm_salida import procesar_salida_viaje

def ir_a_facturacion(driver, total_factura_valor, datos_viaje=None):
    wait = WebDriverWait(driver, 15)

    # Ir a pestaña Conceptos Facturación
    try:
        conceptos_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Conceptos Facturación")))
        driver.execute_script("arguments[0].click();", conceptos_link)
        print("✅ Pestaña Conceptos Facturación abierta")
        time.sleep(1.5)
    except Exception as e:
        print(f"❌ Error al abrir pestaña Conceptos Facturación: {e}")
        return

    # Insertar Total del viaje
    try:
        total_input = wait.until(EC.element_to_be_clickable((By.ID, "zrl_1_EDT_IMPORTECONCEPTOFACTURACION1")))
        total_input.click()
        time.sleep(0.3)
        total_input.send_keys(Keys.CONTROL + "a")  # Selecciona todo
        total_input.send_keys(Keys.DELETE)         # Borra lo anterior
        total_input.send_keys(str(total_factura_valor))
        total_input.send_keys(Keys.ENTER)
        print(f"✅ Total del viaje '{total_factura_valor}' insertado")
    except Exception as e:
        print(f"❌ Error al insertar total de factura: {e}")
        return

    # Clic en botón Aceptar para documentar
    try:
        aceptar_btn = wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTAR")))
        driver.execute_script("arguments[0].click();", aceptar_btn)
        print("✅ Botón 'Aceptar' clickeado")
        time.sleep(1)
    except Exception as e:
        print(f"❌ Error al hacer clic en 'Aceptar': {e}")
        return

    # Responder "No" a la caja de pregunta
    try:
        no_btn = wait.until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
        driver.execute_script("arguments[0].click();", no_btn)
        print("✅ Botón 'No' clickeado")
        time.sleep(1)
    except Exception as e:
        print(f"❌ Error al hacer clic en 'No': {e}")

    # Clic en botón Regresar
    try:
        regresar_btn = wait.until(EC.element_to_be_clickable((By.ID, "BTN_REGRESAR")))
        driver.execute_script("arguments[0].click();", regresar_btn)
        print("✅ Botón 'Regresar' clickeado")
        
        # Llamar al proceso de salida
        print("🚀 Iniciando proceso de salida del viaje...")
        resultado_salida = procesar_salida_viaje(driver, datos_viaje)
        
        if resultado_salida:
            print("✅ Proceso de salida completado exitosamente")
        else:
            print("❌ Error en proceso de salida")
            
    except Exception as e:
        print(f"❌ Error al hacer clic en 'Regresar': {e}")