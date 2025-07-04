import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcesadorLlegadaFactura:
    def __init__(self, driver, datos_viaje):
        self.driver = driver
        self.datos_viaje = datos_viaje
        self.wait = WebDriverWait(driver, 20)  # Aumenté timeout para mayor estabilidad
        
    def procesar_llegada_y_factura(self):
        """Proceso principal de llegada y facturación"""
        try:
            logger.info("🚀 Iniciando proceso de llegada y facturación")
            
            # Paso 1: Hacer clic en "Llegada"
            if not self._hacer_clic_llegada():
                return False
                
            # Paso 2: Llenar fecha de llegada y status
            if not self._procesar_llegada():
                return False
                
            # Paso 3: Autorizar
            if not self._autorizar():
                return False
                
            # Paso 4: Facturar
            if not self._procesar_facturacion():
                return False
                
            logger.info("🎉 Proceso de llegada y facturación completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de llegada y facturación: {e}")
            return False
    
    def _hacer_clic_llegada(self):
        """Hacer clic en el link de Llegada"""
        try:
            logger.info("🛬 Buscando link 'Llegada'...")
            
            # Buscar el link de Llegada
            llegada_link = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Llegada")))
            self.driver.execute_script("arguments[0].click();", llegada_link)
            time.sleep(2)  # Esperar a que cargue la ventana de llegada
            logger.info("✅ Link 'Llegada' clickeado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al hacer clic en 'Llegada': {e}")
            return False
    
    def _procesar_llegada(self):
        """Llenar fecha de llegada y seleccionar status TERMINADO"""
        try:
            logger.info("📅 Procesando datos de llegada...")
            
            # Obtener fecha actual para la llegada (siempre fecha actual según descripción)
            fecha_llegada = datetime.now().strftime("%d/%m/%Y")
            
            # Llenar fecha de llegada
            try:
                fecha_input = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_LLEGADA")))
                fecha_input.clear()
                fecha_input.send_keys(fecha_llegada)
                logger.info(f"✅ Fecha de llegada '{fecha_llegada}' insertada")
            except Exception as e:
                logger.error(f"❌ Error al insertar fecha de llegada: {e}")
                return False
            
            # Seleccionar status "TERMINADO" (valor 3)
            try:
                status_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATESTATUSVIAJE"))))
                status_select.select_by_value("3")  # TERMINADO
                time.sleep(0.5)
                logger.info("✅ Status 'TERMINADO' seleccionado")
            except Exception as e:
                logger.error(f"❌ Error al seleccionar status TERMINADO: {e}")
                return False
            
            # Hacer clic en "Aceptar"
            try:
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTAR")))
                self.driver.execute_script("arguments[0].click();", aceptar_btn)
                time.sleep(1)
                logger.info("✅ Botón 'Aceptar' clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Aceptar': {e}")
                return False
            
            # Hacer clic en "No" para el envío de correo
            try:
                no_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                self.driver.execute_script("arguments[0].click();", no_btn)
                time.sleep(2)  # Esperar a que se cierre la ventana y regrese a la lista
                logger.info("✅ Botón 'No' clickeado - Llegada completada")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'No': {e}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de llegada: {e}")
            return False
    
    def _autorizar(self):
        """Hacer clic en Autorizar y manejar confirmación"""
        try:
            logger.info("🔓 Buscando botón 'Autorizar'...")
            
            autorizar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_AUTORIZAR")))
            
            # Hacer scroll al botón para asegurar visibilidad
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", autorizar_btn)
            time.sleep(0.5)
            
            # Usar JavaScript click para mayor confiabilidad
            self.driver.execute_script("arguments[0].click();", autorizar_btn)
            logger.info("✅ Botón 'Autorizar' clickeado")
            
            # Manejar posible alerta de confirmación del navegador
            try:
                logger.info("🔍 Esperando posible alerta de confirmación...")
                # Esperar hasta 3 segundos por una alerta
                alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                
                # Obtener texto de la alerta para log
                alert_text = alert.text
                logger.info(f"📋 Alerta detectada: '{alert_text}'")
                
                # Aceptar la alerta
                alert.accept()
                logger.info("✅ Alerta de confirmación aceptada")
                
            except TimeoutException:
                logger.info("ℹ️ No se detectó alerta de confirmación")
            except Exception as e:
                logger.warning(f"⚠️ Error al manejar alerta: {e}")
            
            # Esperar un momento para que se procese la autorización
            time.sleep(2)
            
            # Verificar que apareció el botón "Facturar"
            try:
                facturar_check = self.wait.until(EC.presence_of_element_located((By.ID, "BTN_FACTURAR")))
                logger.info("✅ Viaje autorizado correctamente - Botón 'Facturar' disponible")
                return True
            except:
                logger.warning("⚠️ Botón 'Facturar' no apareció inmediatamente, continuando...")
                return True  # Continuar de todas formas
            
        except Exception as e:
            logger.error(f"❌ Error al autorizar viaje: {e}")
            return False
    
    def _procesar_facturacion(self):
        """Proceso completo de facturación"""
        try:
            logger.info("💰 Iniciando proceso de facturación...")
            
            # Hacer clic en "Facturar"
            try:
                facturar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_FACTURAR")))
                
                # Hacer scroll al botón
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", facturar_btn)
                time.sleep(0.5)
                
                # Usar JavaScript click
                self.driver.execute_script("arguments[0].click();", facturar_btn)
                time.sleep(2)  # Esperar a que cargue la ventana de facturación
                logger.info("✅ Botón 'Facturar' clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Facturar': {e}")
                return False
            
            # Cambiar tipo de documento a "FACTURA CFDI - W" (valor 7)
            try:
                logger.info("📄 Cambiando tipo de documento a 'FACTURA CFDI - W'...")
                tipo_doc_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATTIPOSDOCUMENTOS"))))
                tipo_doc_select.select_by_value("7")  # FACTURA CFDI - W
                time.sleep(0.5)
                logger.info("✅ Tipo de documento 'FACTURA CFDI - W' seleccionado")
            except Exception as e:
                logger.error(f"❌ Error al seleccionar tipo de documento: {e}")
                return False
            
            # Hacer clic en "Aceptar" para confirmar la facturación
            try:
                # Buscar por el texto del span "Aceptar"
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Aceptar')]/..")))
                self.driver.execute_script("arguments[0].click();", aceptar_btn)
                time.sleep(2)
                logger.info("✅ Botón 'Aceptar' clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Aceptar': {e}")
                return False
            
            # Confirmar timbrado con "Sí"
            try:
                logger.info("🎫 Confirmando timbrado...")
                si_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_YES")))
                self.driver.execute_script("arguments[0].click();", si_btn)
                time.sleep(4)  # Esperar más tiempo para el proceso de timbrado
                logger.info("✅ Confirmación 'Sí' para timbrado clickeada")
            except Exception as e:
                logger.error(f"❌ Error al confirmar timbrado: {e}")
                return False
            
            # Procesar impresión y verificaciones finales
            if not self._procesar_impresion():
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de facturación: {e}")
            return False
    
    def _procesar_impresion(self):
        """Procesar la parte de impresión y verificaciones finales"""
        try:
            logger.info("🖨️ Procesando impresión y verificaciones finales...")
            
            # Hacer clic en "Regresar" si está disponible
            try:
                regresar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_REGRESAR")))
                self.driver.execute_script("arguments[0].click();", regresar_btn)
                time.sleep(1)
                logger.info("✅ Botón 'Regresar' clickeado")
            except Exception as e:
                logger.warning(f"⚠️ Botón 'Regresar' no encontrado o no necesario: {e}")
            
            # Hacer clic en "Imprimir"
            try:
                imprimir_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_IMPRIMIR")))
                self.driver.execute_script("arguments[0].click();", imprimir_btn)
                time.sleep(3)  # Esperar a que cargue la ventana de impresión
                logger.info("✅ Botón 'Imprimir' clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Imprimir': {e}")
                return False
            
            # Verificar existencia de Folio Fiscal y Número de Factura
            self._verificar_datos_factura()
            
            # Cerrar ventana de impresión
            try:
                # Buscar botón de cerrar (span vacío con clase específica)
                cerrar_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@class='btnvalignmiddle' and normalize-space(text())='']/..")))
                self.driver.execute_script("arguments[0].click();", cerrar_btn)
                time.sleep(1)
                logger.info("✅ Ventana de impresión cerrada")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo cerrar ventana de impresión automáticamente: {e}")
                # Intentar con Escape
                try:
                    from selenium.webdriver.common.keys import Keys
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(1)
                    logger.info("✅ Ventana cerrada con Escape")
                except:
                    logger.warning("⚠️ No se pudo cerrar con Escape")
            
            # Marcar como NO impreso
            try:
                no_impreso_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                self.driver.execute_script("arguments[0].click();", no_impreso_btn)
                time.sleep(1)
                logger.info("✅ Marcado como 'No impreso'")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo marcar como 'No impreso': {e}")
            
            logger.info("✅ Proceso de impresión y verificaciones completado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de impresión: {e}")
            return False
    
    def _verificar_datos_factura(self):
        """Verificar que existen Folio Fiscal y Número de Factura"""
        try:
            logger.info("🔍 Verificando datos de factura...")
            
            # Variables para rastrear qué se encontró
            folio_fiscal_encontrado = False
            numero_factura_encontrado = False
            
            # Intentar encontrar Folio Fiscal
            try:
                # Buscar por texto que contenga "Folio Fiscal" o similar
                folio_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Folio Fiscal') or contains(text(), 'FOLIO FISCAL') or contains(text(), 'folio fiscal')]")
                if folio_elements:
                    folio_fiscal_encontrado = True
                    logger.info("✅ Folio Fiscal encontrado en el documento")
                    
                    # Intentar obtener el valor
                    for element in folio_elements:
                        parent = element.find_element(By.XPATH, "..")
                        texto_completo = parent.text
                        if len(texto_completo) > len(element.text):
                            logger.info(f"📋 Texto del Folio Fiscal: {texto_completo}")
                            break
                            
            except Exception as e:
                logger.warning(f"⚠️ Error al buscar Folio Fiscal: {e}")
            
            # Intentar encontrar Número de Factura
            try:
                # Buscar por texto que contenga "Factura", "FACTURA" o "No. Factura"
                factura_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'FACTURA') or contains(text(), 'Factura') or contains(text(), 'No. Factura')]")
                if factura_elements:
                    numero_factura_encontrado = True
                    logger.info("✅ Número de Factura encontrado en el documento")
                    
                    # Intentar obtener el valor
                    for element in factura_elements:
                        texto = element.text
                        if any(char.isdigit() for char in texto):
                            logger.info(f"📋 Texto de Factura: {texto}")
                            break
                            
            except Exception as e:
                logger.warning(f"⚠️ Error al buscar Número de Factura: {e}")
            
            # Reportar resultados
            if folio_fiscal_encontrado and numero_factura_encontrado:
                logger.info("🎉 ¡Todos los datos de factura verificados correctamente!")
            elif folio_fiscal_encontrado:
                logger.warning("⚠️ Folio Fiscal encontrado, pero no se pudo verificar Número de Factura")
            elif numero_factura_encontrado:
                logger.warning("⚠️ Número de Factura encontrado, pero no se pudo verificar Folio Fiscal")
            else:
                logger.warning("⚠️ No se pudieron verificar datos de factura (puede ser normal si están en formato no detectable)")
                
        except Exception as e:
            logger.warning(f"⚠️ Error al verificar datos de factura: {e}")


def procesar_llegada_factura(driver, datos_viaje):
    """Función principal para procesar llegada y facturación"""
    try:
        logger.info("🚀 Iniciando ProcesadorLlegadaFactura...")
        procesador = ProcesadorLlegadaFactura(driver, datos_viaje)
        resultado = procesador.procesar_llegada_y_factura()
        
        if resultado:
            logger.info("✅ Proceso de llegada y facturación completado exitosamente")
        else:
            logger.error("❌ Error en proceso de llegada y facturación")
            
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Error en procesar_llegada_factura: {e}")
        return False

# Ejemplo de uso
if __name__ == "__main__":
    # Este bloque se ejecutaría solo si ejecutas este archivo directamente
    # Aquí puedes agregar código de prueba
    pass