from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def ir_a_facturacion(driver, total_factura_valor, datos_viaje=None):
    """Función para ir a la pestaña de Conceptos Facturación y llenar el total"""
    wait = WebDriverWait(driver, 15)

    # Ir a pestaña Conceptos Facturación
    try:
        conceptos_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Conceptos Facturación")))
        driver.execute_script("arguments[0].click();", conceptos_link)
        print("✅ Pestaña Conceptos Facturación abierta")
        time.sleep(1.5)
    except Exception as e:
        print(f"❌ Error al abrir pestaña Conceptos Facturación: {e}")
        return False

    # Insertar Total del viaje
    try:
        total_input = wait.until(EC.element_to_be_clickable((By.ID, "zrl_1_EDT_IMPORTECONCEPTOFACTURACION1")))
        total_input.click()
        time.sleep(0.3)
        total_input.send_keys(Keys.CONTROL + "a")  # Selecciona todo
        total_input.send_keys(Keys.DELETE)         # Borra lo anterior
        total_input.send_keys(str(total_factura_valor))
        print(f"✅ Total del viaje '{total_factura_valor}' insertado")
        
        # 🔧 SECUENCIA CORRECTA PARA FORZAR RECÁLCULO 🔧
        print("🔧 Ejecutando secuencia para forzar recálculo...")
        
        # Paso 1: Doble clic para seleccionar la cajita del monto
        print("🔧 Paso 1: Doble clic para seleccionar cajita...")
        total_input.click()
        time.sleep(0.2)
        total_input.click()
        time.sleep(0.5)
        print("✅ Doble clic completado")
        
        # Paso 2: TAB para procesar el cambio
        print("🔧 Paso 2: TAB para procesar el cambio...")
        total_input.send_keys(Keys.TAB)
        time.sleep(1)  # Tiempo extra para que aparezca la cajita de Chrome
        print("✅ TAB enviado - esperando cajita de Chrome...")
        
        # Paso 3: La cajita de Chrome debería aparecer y ser aceptada automáticamente
        # (esto lo maneja la automatización existente)
        time.sleep(1)  # Tiempo para que se procese todo
        print("✅ Secuencia de recálculo completada")
        
    except Exception as e:
        print(f"❌ Error al insertar total de factura: {e}")
        return False

    # Clic en botón Aceptar para documentar
    try:
        aceptar_btn = wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTAR")))
        driver.execute_script("arguments[0].click();", aceptar_btn)
        print("✅ Botón 'Aceptar' clickeado")
        time.sleep(1)
    except Exception as e:
        print(f"❌ Error al hacer clic en 'Aceptar': {e}")
        return False

    # Responder "No" a la caja de pregunta
    try:
        no_btn = wait.until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
        driver.execute_script("arguments[0].click();", no_btn)
        print("✅ Botón 'No' clickeado")
        time.sleep(1)
    except Exception as e:
        print(f"❌ Error al hacer clic en 'No': {e}")
        return False

    # Clic en botón Regresar
    try:
        regresar_btn = wait.until(EC.element_to_be_clickable((By.ID, "BTN_REGRESAR")))
        driver.execute_script("arguments[0].click();", regresar_btn)
        print("✅ Botón 'Regresar' clickeado")
        time.sleep(2)  # Esperar a que regrese a la pantalla principal
        
        print("✅ Facturación inicial completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al hacer clic en 'Regresar': {e}")
        return False