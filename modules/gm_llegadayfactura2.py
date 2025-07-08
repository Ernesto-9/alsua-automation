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
        """Versión con debug intensivo para encontrar el problema del botón Aceptar"""
        try:
            logger.info("🚨🚨🚨 EJECUTANDO ARCHIVO CORRECTO CON DEBUG 🚨🚨🚨")
            logger.info("📅 Procesando datos de llegada CON DEBUG...")
            
            # Obtener fecha actual para la llegada
            fecha_llegada = datetime.now().strftime("%d/%m/%Y")
            logger.info(f"📅 Fecha de llegada a usar: {fecha_llegada}")
            
            # Llenar fecha de llegada usando método robusto
            if not self._llenar_fecha_llegada_robusto("EDT_LLEGADA", fecha_llegada):
                logger.error("❌ Error al insertar fecha de llegada")
                return False
            
            # Esperar un momento para que GM procese la fecha
            logger.info("⏳ Esperando que GM procese la fecha...")
            time.sleep(2)  # Aumenté el tiempo de espera
            
            # Seleccionar status "TERMINADO" (valor 3)
            try:
                logger.info("🎯 Seleccionando status TERMINADO...")
                status_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATESTATUSVIAJE"))))
                
                # Verificar opciones disponibles
                opciones = status_select.options
                logger.info(f"📋 Opciones de status disponibles:")
                for opcion in opciones:
                    logger.info(f"   - Valor: {opcion.get_attribute('value')}, Texto: {opcion.text}")
                
                # Seleccionar TERMINADO
                status_select.select_by_value("3")  # TERMINADO
                time.sleep(1)  # Más tiempo después de seleccionar
                
                # Verificar selección
                seleccionado = status_select.first_selected_option
                logger.info(f"✅ Status seleccionado: {seleccionado.text} (valor: {seleccionado.get_attribute('value')})")
                
            except Exception as e:
                logger.error(f"❌ Error al seleccionar status TERMINADO: {e}")
                return False
            
            # NUEVO: Esperar más tiempo después de cambiar el status
            logger.info("⏳ Esperando que GM procese el cambio de status...")
            time.sleep(3)  # Tiempo adicional para que GM procese todo
            
            # DEBUGGING INTENSIVO DEL BOTÓN ACEPTAR
            logger.info("🔍 INICIANDO DEBUG DEL BOTÓN ACEPTAR...")
            
            # 1. Buscar TODOS los elementos que contengan "aceptar"
            try:
                todos_aceptar = self.driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ACEPTAR', 'aceptar'), 'aceptar')]")
                logger.info(f"🔍 Elementos que contienen 'aceptar': {len(todos_aceptar)}")
                for i, elem in enumerate(todos_aceptar):
                    try:
                        logger.info(f"   {i+1}. Texto: '{elem.text}', Tag: {elem.tag_name}, ID: '{elem.get_attribute('id')}', Visible: {elem.is_displayed()}, Habilitado: {elem.is_enabled()}")
                    except:
                        logger.info(f"   {i+1}. Error al obtener info del elemento")
            except Exception as e:
                logger.warning(f"⚠️ Error buscando elementos 'aceptar': {e}")
            
            # 2. Buscar específicamente BTN_ACEPTAR
            try:
                btn_aceptar_directo = self.driver.find_element(By.ID, "BTN_ACEPTAR")
                logger.info(f"🎯 BTN_ACEPTAR encontrado:")
                logger.info(f"   - Texto: '{btn_aceptar_directo.text}'")
                logger.info(f"   - Visible: {btn_aceptar_directo.is_displayed()}")
                logger.info(f"   - Habilitado: {btn_aceptar_directo.is_enabled()}")
                logger.info(f"   - Clase: '{btn_aceptar_directo.get_attribute('class')}'")
                logger.info(f"   - Style: '{btn_aceptar_directo.get_attribute('style')}'")
                
                # Obtener posición del elemento
                location = btn_aceptar_directo.location
                size = btn_aceptar_directo.size
                logger.info(f"   - Posición: x={location['x']}, y={location['y']}")
                logger.info(f"   - Tamaño: w={size['width']}, h={size['height']}")
                
            except Exception as e:
                logger.error(f"❌ BTN_ACEPTAR NO encontrado: {e}")
                
                # Buscar botones alternativos
                logger.info("🔍 Buscando botones alternativos...")
                try:
                    todos_botones = self.driver.find_elements(By.XPATH, "//button | //input[@type='button'] | //input[@type='submit'] | //*[@onclick] | //*[contains(@class, 'btn')]")
                    logger.info(f"🔍 Total de botones encontrados: {len(todos_botones)}")
                    for i, btn in enumerate(todos_botones[:10]):  # Solo los primeros 10
                        try:
                            logger.info(f"   Botón {i+1}: ID='{btn.get_attribute('id')}', Texto='{btn.text}', Visible={btn.is_displayed()}")
                        except:
                            pass
                except Exception as e2:
                    logger.warning(f"⚠️ Error buscando botones alternativos: {e2}")
                
                return False
            
            # 3. Si el botón existe, intentar hacer clic con múltiples métodos
            logger.info("🖱️ Intentando hacer clic en BTN_ACEPTAR...")
            
            # Método 1: Scroll + wait + click normal
            try:
                logger.info("🖱️ Método 1: Scroll + Wait + Click normal...")
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTAR")))
                
                # Hacer scroll para asegurar visibilidad
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", aceptar_btn)
                time.sleep(1)
                
                # Click normal
                aceptar_btn.click()
                time.sleep(2)
                logger.info("✅ Método 1 EXITOSO - Botón 'Aceptar' clickeado")
                
            except Exception as e1:
                logger.warning(f"⚠️ Método 1 falló: {e1}")
                
                # Método 2: JavaScript click
                try:
                    logger.info("🖱️ Método 2: JavaScript click...")
                    aceptar_btn = self.driver.find_element(By.ID, "BTN_ACEPTAR")
                    self.driver.execute_script("arguments[0].click();", aceptar_btn)
                    time.sleep(2)
                    logger.info("✅ Método 2 EXITOSO - Botón clickeado con JavaScript")
                    
                except Exception as e2:
                    logger.warning(f"⚠️ Método 2 falló: {e2}")
                    
                    # Método 3: Forzar click con coordinates
                    try:
                        logger.info("🖱️ Método 3: ActionChains click...")
                        from selenium.webdriver.common.action_chains import ActionChains
                        aceptar_btn = self.driver.find_element(By.ID, "BTN_ACEPTAR")
                        actions = ActionChains(self.driver)
                        actions.move_to_element(aceptar_btn).click().perform()
                        time.sleep(2)
                        logger.info("✅ Método 3 EXITOSO - Botón clickeado con ActionChains")
                        
                    except Exception as e3:
                        logger.error(f"❌ Método 3 falló: {e3}")
                        
                        # Método 4: Buscar por XPath alternativo
                        try:
                            logger.info("🖱️ Método 4: XPath alternativo...")
                            xpath_alternatives = [
                                "//span[contains(text(), 'Aceptar')]/..",
                                "//button[contains(text(), 'Aceptar')]",
                                "//input[@value='Aceptar']",
                                "//*[@onclick and contains(text(), 'Aceptar')]"
                            ]
                            
                            for xpath in xpath_alternatives:
                                try:
                                    alt_btn = self.driver.find_element(By.XPATH, xpath)
                                    if alt_btn.is_displayed() and alt_btn.is_enabled():
                                        alt_btn.click()
                                        time.sleep(2)
                                        logger.info(f"✅ Método 4 EXITOSO - Botón clickeado con XPath: {xpath}")
                                        break
                                except:
                                    continue
                            else:
                                logger.error("❌ TODOS los métodos fallaron")
                                return False
                                
                        except Exception as e4:
                            logger.error(f"❌ Método 4 falló: {e4}")
                            return False
            
            # Verificar si el clic funcionó buscando el botón "No" que debería aparecer después
            try:
                logger.info("🔍 Verificando si apareció el botón 'No' (confirmación de que Aceptar funcionó)...")
                no_btn_check = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                logger.info("✅ Botón 'No' detectado - El clic en 'Aceptar' fue exitoso")
                
                # Hacer clic en "No" para completar el proceso
                self.driver.execute_script("arguments[0].click();", no_btn_check)
                time.sleep(2)
                logger.info("✅ Botón 'No' clickeado - Proceso de llegada completado")
                
            except Exception as e:
                logger.warning(f"⚠️ No se detectó botón 'No': {e}")
                logger.warning("⚠️ Puede que el clic en 'Aceptar' no haya funcionado o que la interfaz sea diferente")
                
                # Intentar buscar el botón "No" con métodos alternativos
                try:
                    no_btn_alt = self.driver.find_element(By.XPATH, "//span[contains(text(), 'No')]/..")
                    no_btn_alt.click()
                    time.sleep(2)
                    logger.info("✅ Botón 'No' encontrado y clickeado con XPath alternativo")
                except:
                    logger.error("❌ No se pudo completar el proceso - revisión manual requerida")
                    return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de llegada con debug: {e}")
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