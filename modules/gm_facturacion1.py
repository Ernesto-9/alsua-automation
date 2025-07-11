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
        
        # 🔧 FORZAR RECÁLCULO EN GM TRANSPORT 🔧
        print("🔧 Forzando recálculo del sistema...")
        
        # Método 1: TAB para que GM procese el cambio
        total_input.send_keys(Keys.TAB)
        time.sleep(0.5)
        print("✅ TAB enviado para forzar recálculo")
        
        # Método 2: Doble clic en el campo para asegurar procesamiento
        total_input.click()
        time.sleep(0.2)
        total_input.click()
        time.sleep(0.5)
        print("✅ Doble clic realizado para confirmar procesamiento")
        
        # 🚨 PAUSA PARA DEBUGGING 🚨
        print("🔍" * 50)
        print("🔍 PAUSA PARA DEBUGGING DEL IMPORTE")
        print(f"🔍 Importe que se insertó: {total_factura_valor}")
        print(f"🔍 Tipo de dato: {type(total_factura_valor)}")
        print("🔍 REVISA EN PANTALLA:")
        print("🔍 1. ¿Se insertó correctamente el importe?")
        print("🔍 2. ¿Está en el formato correcto?")
        print("🔍 3. ¿GM lo acepta sin errores?")
        print("🔍 4. ¿Hay algún mensaje de error?")
        print("🔍")
        
        # Obtener valor actual del campo para verificación
        try:
            valor_actual = total_input.get_attribute("value")
            print(f"🔍 Valor actual en el campo: '{valor_actual}'")
        except Exception as e:
            print(f"🔍 No se pudo leer valor actual: {e}")
            
        # Información adicional del viaje para contexto
        if datos_viaje:
            print(f"🔍 DATOS DEL VIAJE:")
            print(f"🔍   Prefactura: {datos_viaje.get('prefactura', 'N/A')}")
            print(f"🔍   Fecha: {datos_viaje.get('fecha', 'N/A')}")
            print(f"🔍   Placa Tractor: {datos_viaje.get('placa_tractor', 'N/A')}")
            print(f"🔍   Placa Remolque: {datos_viaje.get('placa_remolque', 'N/A')}")
            print(f"🔍   Determinante: {datos_viaje.get('clave_determinante', 'N/A')}")
            
        print("🔍" * 50)
        print("🔍 Presiona ENTER para continuar con la automatización...")
        input()  # PAUSA - Espera ENTER del usuario
        print("🔍 Continuando automatización...")
        print("🔍" * 50)
        
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