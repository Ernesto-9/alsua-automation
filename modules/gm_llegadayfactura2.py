import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
        self.wait = WebDriverWait(driver, 20)
        
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
    
    def _llenar_fecha_llegada_robusto(self, id_input, fecha_valor):
        """Método ROBUSTO para llenar fecha de llegada - usa el método que SÍ funciona"""
        try:
            logger.info(f"🎯 Llenando fecha en {id_input} con valor: {fecha_valor}")
            
            # Método que funciona en gm_transport_general.py
            campo = self.wait.until(EC.element_to_be_clickable((By.ID, id_input)))
            
            # Verificar valor actual
            valor_actual = campo.get_attribute("value")
            logger.info(f"📋 Valor actual en {id_input}: '{valor_actual}'")
            
            # DOBLE CLIC como en el método que funciona
            logger.info(f"🖱️ Haciendo primer clic en {id_input}")
            campo.click()
            time.sleep(0.3)
            logger.info(f"🖱️ Haciendo segundo clic en {id_input}")
            campo.click()
            time.sleep(0.2)
            
            # Limpiar campo completamente
            logger.info(f"🧹 Limpiando campo {id_input}")
            campo.send_keys(Keys.HOME)
            for _ in range(15):  # Más borrado para asegurar limpieza
                campo.send_keys(Keys.DELETE)
                
            # Obtener hora actual si existe, sino usar hora por defecto
            if valor_actual and " " in valor_actual:
                hora = valor_actual.split(" ")[1]
                logger.info(f"🕒 Hora encontrada: {hora}")
            else:
                hora = "14:00"
                logger.info(f"🕒 Usando hora por defecto: {hora}")
                
            # Insertar nueva fecha con hora
            nuevo_valor = f"{fecha_valor} {hora}"
            logger.info(f"⌨️ Escribiendo en {id_input}: '{nuevo_valor}'")
            campo.send_keys(nuevo_valor)
            time.sleep(0.5)
            
            # Verificar que se insertó correctamente
            valor_final = campo.get_attribute("value")
            logger.info(f"✅ Fecha final en {id_input}: '{valor_final}'")
            
            # Hacer ENTER para confirmar
            campo.send_keys(Keys.ENTER)
            time.sleep(0.3)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al llenar fecha en {id_input}: {e}")
            return False
    
    def _procesar_llegada(self):
        """Procesa llegada con enfoque DIRECTO al botón Aceptar"""
        try:
            logger.info("🚨🚨🚨 EJECUTANDO ARCHIVO CORRECTO CON DEBUG 🚨🚨🚨")
            logger.info("📅 Procesando datos de llegada - ENFOQUE DIRECTO...")
            
            # Obtener fecha actual para la llegada
            fecha_llegada = datetime.now().strftime("%d/%m/%Y")
            logger.info(f"📅 Fecha de llegada a usar: {fecha_llegada}")
            
            # Llenar fecha de llegada usando método robusto
            if not self._llenar_fecha_llegada_robusto("EDT_LLEGADA", fecha_llegada):
                logger.error("❌ Error al insertar fecha de llegada")
                return False
            
            # Esperar un momento para que GM procese la fecha
            logger.info("⏳ Esperando que GM procese la fecha...")
            time.sleep(2)
            
            # Seleccionar status "TERMINADO" (valor 3) - CON PROTECCIÓN ANTI-STALE
            try:
                logger.info("🎯 Seleccionando status TERMINADO...")
                
                # BUSCAR EL ELEMENTO DE NUEVO para evitar stale element
                status_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATESTATUSVIAJE"))))
                
                # Verificar opciones disponibles
                opciones = status_select.options
                logger.info(f"📋 Opciones de status disponibles:")
                for opcion in opciones:
                    logger.info(f"   - Valor: {opcion.get_attribute('value')}, Texto: {opcion.text}")
                
                # PROTECCIÓN ANTI-STALE: Volver a buscar el select después de leer opciones
                logger.info("🔄 Reobteniendo elemento select para evitar stale element...")
                status_select = Select(self.driver.find_element(By.ID, "COMBO_CATESTATUSVIAJE"))
                
                # Seleccionar TERMINADO
                status_select.select_by_value("3")  # TERMINADO
                time.sleep(1)
                
                # VERIFICAR SELECCIÓN con elemento fresco
                logger.info("✅ Verificando selección...")
                status_select_verificacion = Select(self.driver.find_element(By.ID, "COMBO_CATESTATUSVIAJE"))
                seleccionado = status_select_verificacion.first_selected_option
                logger.info(f"✅ Status seleccionado: {seleccionado.text} (valor: {seleccionado.get_attribute('value')})")
                
            except Exception as e:
                logger.error(f"❌ Error al seleccionar status TERMINADO: {e}")
                
                # RETRY: Intentar una vez más con elemento completamente fresco
                try:
                    logger.info("🔄 RETRY: Intentando seleccionar status TERMINADO de nuevo...")
                    time.sleep(2)  # Esperar un poco más
                    
                    # Buscar elemento completamente fresco
                    combo_element = self.driver.find_element(By.ID, "COMBO_CATESTATUSVIAJE")
                    status_select_retry = Select(combo_element)
                    
                    # Seleccionar TERMINADO
                    status_select_retry.select_by_value("3")
                    time.sleep(1)
                    
                    # Verificar
                    seleccionado_retry = status_select_retry.first_selected_option
                    logger.info(f"✅ RETRY exitoso - Status: {seleccionado_retry.text}")
                    
                except Exception as retry_error:
                    logger.error(f"❌ RETRY también falló: {retry_error}")
                    return False
            
            # NUEVO: IR DIRECTAMENTE AL BOTÓN ACEPTAR sin esperar
            logger.info("🎯 Status cambiado - yendo DIRECTAMENTE al botón Aceptar...")
            time.sleep(1)  # Solo 1 segundo para que GM registre el cambio
            
            # SALTAR TODO EL DEBUG Y IR DIRECTO AL BOTÓN
            logger.info("🖱️ Buscando y haciendo clic en BTN_ACEPTAR INMEDIATAMENTE...")
            
            try:
                # Buscar el botón Aceptar directamente
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTAR")))
                
                # Verificar que está disponible
                if aceptar_btn.is_displayed() and aceptar_btn.is_enabled():
                    logger.info("✅ BTN_ACEPTAR encontrado y disponible")
                    
                    # Hacer scroll para asegurar visibilidad
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", aceptar_btn)
                    time.sleep(0.5)
                    
                    # Click directo con JavaScript
                    self.driver.execute_script("arguments[0].click();", aceptar_btn)
                    time.sleep(2)
                    logger.info("✅ BTN_ACEPTAR clickeado exitosamente")
                    
                    # Buscar el botón "No" que debería aparecer después
                    try:
                        no_btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                        logger.info("✅ Botón 'No' detectado - Aceptar funcionó")
                        
                        # Hacer clic en "No"
                        self.driver.execute_script("arguments[0].click();", no_btn)
                        time.sleep(2)
                        logger.info("✅ Botón 'No' clickeado - Proceso completado")
                        return True
                        
                    except Exception as no_error:
                        logger.warning(f"⚠️ No se detectó botón 'No': {no_error}")
                        # Intentar con XPath alternativo
                        try:
                            no_btn_alt = self.driver.find_element(By.XPATH, "//span[contains(text(), 'No')]/..")
                            no_btn_alt.click()
                            time.sleep(2)
                            logger.info("✅ Botón 'No' clickeado con XPath alternativo")
                            return True
                        except:
                            logger.error("❌ No se pudo encontrar botón 'No'")
                            return False
                else:
                    logger.warning("⚠️ BTN_ACEPTAR encontrado pero no disponible")
                    logger.warning(f"   - Visible: {aceptar_btn.is_displayed()}")
                    logger.warning(f"   - Habilitado: {aceptar_btn.is_enabled()}")
                    
                    # Si no está habilitado, hacer debug rápido
                    logger.info("🔍 Debug rápido del botón...")
                    logger.info(f"   - Texto: '{aceptar_btn.text}'")
                    logger.info(f"   - Clase: '{aceptar_btn.get_attribute('class')}'")
                    logger.info(f"   - Style: '{aceptar_btn.get_attribute('style')}'")
                    
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error buscando BTN_ACEPTAR: {e}")
                
                # Solo si no se encuentra, hacer debug básico
                logger.info("🔍 BTN_ACEPTAR no encontrado - debug básico...")
                try:
                    todos_botones = self.driver.find_elements(By.XPATH, "//button | //input[@type='button'] | //*[@onclick]")
                    logger.info(f"🔍 Botones disponibles: {len(todos_botones)}")
                    for i, btn in enumerate(todos_botones[:5]):
                        try:
                            btn_id = btn.get_attribute('id')
                            btn_text = btn.text
                            btn_visible = btn.is_displayed()
                            logger.info(f"   {i+1}. ID: {btn_id}, Texto: '{btn_text}', Visible: {btn_visible}")
                        except:
                            pass
                except Exception as debug_error:
                    logger.warning(f"⚠️ Error en debug: {debug_error}")
                
                return False
            
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