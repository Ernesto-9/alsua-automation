import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from datetime import datetime
from .pdf_extractor import extraer_datos_automatico

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcesadorLlegadaFactura:
    def __init__(self, driver, datos_viaje):
        self.driver = driver
        self.datos_viaje = datos_viaje
        self.wait = WebDriverWait(driver, 20)
        
    def procesar_llegada_y_factura(self):
        """Proceso principal de llegada y facturación CON EXTRACCIÓN AUTOMÁTICA"""
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
        """Método ROBUSTO para llenar fecha de llegada"""
        try:
            logger.info(f"🎯 Llenando fecha en {id_input} con valor: {fecha_valor}")
            
            campo = self.wait.until(EC.element_to_be_clickable((By.ID, id_input)))
            
            # Verificar valor actual
            valor_actual = campo.get_attribute("value")
            logger.info(f"📋 Valor actual en {id_input}: '{valor_actual}'")
            
            # DOBLE CLIC
            logger.info(f"🖱️ Haciendo primer clic en {id_input}")
            campo.click()
            time.sleep(0.3)
            logger.info(f"🖱️ Haciendo segundo clic en {id_input}")
            campo.click()
            time.sleep(0.2)
            
            # Limpiar campo completamente
            logger.info(f"🧹 Limpiando campo {id_input}")
            campo.send_keys(Keys.HOME)
            for _ in range(15):
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
            logger.info("📅 Procesando datos de llegada...")
            
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
                time.sleep(1)
                
                # VERIFICAR SELECCIÓN
                status_select_verificacion = Select(self.driver.find_element(By.ID, "COMBO_CATESTATUSVIAJE"))
                seleccionado = status_select_verificacion.first_selected_option
                logger.info(f"✅ Status seleccionado: {seleccionado.text} (valor: {seleccionado.get_attribute('value')})")
                
            except Exception as e:
                logger.error(f"❌ Error al seleccionar status TERMINADO: {e}")
                return False
            
            # Hacer clic en "Aceptar"
            try:
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTAR")))
                
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
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error buscando BTN_ACEPTAR: {e}")
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
                alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                
                alert_text = alert.text
                logger.info(f"📋 Alerta detectada: '{alert_text}'")
                
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
                return True
            
        except Exception as e:
            logger.error(f"❌ Error al autorizar viaje: {e}")
            return False
    
    def _procesar_facturacion(self):
        """Proceso completo de facturación CON EXTRACCIÓN AUTOMÁTICA"""
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
                time.sleep(2)
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
                time.sleep(4)
                logger.info("✅ Confirmación 'Sí' para timbrado clickeada")
            except Exception as e:
                logger.error(f"❌ Error al confirmar timbrado: {e}")
                return False
            
            # Procesar impresión y extracción de folio
            if not self._procesar_impresion_y_extraccion_automatica():
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de facturación: {e}")
            return False
    
    def _procesar_impresion_y_extraccion_automatica(self):
        """NUEVA FUNCIÓN: Procesar impresión y extraer folio fiscal AUTOMÁTICAMENTE"""
        try:
            logger.info("🖨️ Procesando impresión y extracción automática de datos...")
            
            # Hacer clic en "Regresar" si está disponible
            try:
                regresar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_REGRESAR")))
                self.driver.execute_script("arguments[0].click();", regresar_btn)
                time.sleep(1)
                logger.info("✅ Botón 'Regresar' clickeado")
            except Exception as e:
                logger.warning(f"⚠️ Botón 'Regresar' no encontrado: {e}")
            
            # Hacer clic en "Imprimir" y extraer datos automáticamente
            try:
                imprimir_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_IMPRIMIR")))
                
                logger.info("🚨" * 20)
                logger.info("🚨 INICIANDO EXTRACCIÓN AUTOMÁTICA DE DATOS")
                logger.info("🚨 Configurando descarga automática y extrayendo PDF...")
                logger.info("🚨" * 20)
                
                # Configurar descarga automática antes de hacer clic
                from .pdf_extractor import PDFExtractor
                extractor = PDFExtractor("pdfs_temporales")
                extractor.configurar_descarga_chrome(self.driver)
                
                # Hacer clic en "Imprimir" para que se descargue el PDF
                self.driver.execute_script("arguments[0].click();", imprimir_btn)
                logger.info("✅ Botón 'Imprimir' clickeado - Iniciando descarga automática")
                
                # Esperar y extraer datos automáticamente
                logger.info("⏳ Esperando descarga del PDF...")
                datos_extraidos = extraer_datos_automatico(self.driver, "pdfs_temporales", timeout=20)
                
                # Verificar extracción
                uuid_extraido = datos_extraidos.get("uuid")
                viajegm_extraido = datos_extraidos.get("viaje_gm")
                
                logger.info(f"✅ Datos extraídos automáticamente:")
                logger.info(f"   🆔 UUID: {uuid_extraido}")
                logger.info(f"   🚛 VIAJEGM: {viajegm_extraido}")
                
                # Guardar los datos extraídos en datos_viaje
                if uuid_extraido:
                    self.datos_viaje['uuid'] = uuid_extraido
                else:
                    logger.warning("⚠️ No se pudo extraer UUID del PDF")
                    
                if viajegm_extraido:
                    self.datos_viaje['viajegm'] = viajegm_extraido
                else:
                    logger.warning("⚠️ No se pudo extraer VIAJEGM del PDF")
                
                # 🚀 NUEVO: REGISTRAR VIAJE EXITOSO COMPLETO EN MYSQL
                logger.info("💾 Registrando viaje exitoso completo en MySQL...")
                if not self._registrar_viaje_exitoso_completo():
                    logger.warning("⚠️ Error registrando en MySQL - continuando proceso")
                
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Imprimir' o extraer datos: {e}")
                return False
            
            # Cerrar ventana de impresión
            try:
                # Buscar botón de cerrar
                cerrar_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@class='btnvalignmiddle' and normalize-space(text())='']/..")))
                self.driver.execute_script("arguments[0].click();", cerrar_btn)
                time.sleep(1)
                logger.info("✅ Ventana de impresión cerrada")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo cerrar ventana de impresión automáticamente: {e}")
                # Intentar con Escape
                try:
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
            
            logger.info("✅ Proceso de impresión y extracción automática completado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de impresión y extracción automática: {e}")
            return False
    
    def _registrar_viaje_exitoso_completo(self):
        """
        🚀 NUEVA FUNCIÓN: Registra viaje exitoso con TODOS los datos disponibles en MySQL
        """
        try:
            logger.info("📊 Preparando registro completo de viaje exitoso...")
            
            # Extraer TODOS los datos disponibles
            prefactura = self.datos_viaje.get('prefactura')
            fecha_viaje = self.datos_viaje.get('fecha')
            uuid = self.datos_viaje.get('uuid')
            viajegm = self.datos_viaje.get('viajegm')
            placa_tractor = self.datos_viaje.get('placa_tractor')
            placa_remolque = self.datos_viaje.get('placa_remolque')
            
            # Log de datos que se van a registrar
            logger.info("📋 DATOS COMPLETOS PARA MYSQL:")
            logger.info(f"   📋 Prefactura: {prefactura}")
            logger.info(f"   📅 Fecha: {fecha_viaje}")
            logger.info(f"   🆔 UUID: {uuid}")
            logger.info(f"   🚛 Viaje GM: {viajegm}")
            logger.info(f"   🚗 Placa Tractor: {placa_tractor}")
            logger.info(f"   🚚 Placa Remolque: {placa_remolque}")
            logger.info(f"   💰 Importe: {self.datos_viaje.get('importe', 'No disponible')}")
            logger.info(f"   👤 Cliente: {self.datos_viaje.get('cliente_codigo', 'No disponible')}")
            logger.info(f"   🎯 Determinante: {self.datos_viaje.get('clave_determinante', 'No disponible')}")
            
            # Validar datos críticos
            if not prefactura:
                logger.error("❌ Error crítico: No hay prefactura para registrar")
                return False
                
            if not fecha_viaje:
                logger.error("❌ Error crítico: No hay fecha para registrar")
                return False
            
            # Importar y registrar en MySQL
            try:
                from .mysql_simple import registrar_viaje_exitoso
                
                exito_mysql = registrar_viaje_exitoso(
                    prefactura=prefactura,
                    fecha_viaje=fecha_viaje,
                    uuid=uuid,
                    viajegm=viajegm,
                    placa_tractor=placa_tractor,
                    placa_remolque=placa_remolque
                )
                
                if exito_mysql:
                    logger.info("🎉 VIAJE EXITOSO REGISTRADO COMPLETAMENTE EN MYSQL:")
                    logger.info(f"   ✅ Prefactura: {prefactura}")
                    logger.info(f"   ✅ Fecha: {fecha_viaje}")
                    logger.info(f"   ✅ UUID: {uuid or 'No extraído'}")
                    logger.info(f"   ✅ Viaje GM: {viajegm or 'No extraído'}")
                    logger.info(f"   ✅ Placas: {placa_tractor}/{placa_remolque}")
                    logger.info("💾 Base de datos actualizada exitosamente")
                    return True
                else:
                    logger.warning("⚠️ MySQL no disponible - registro guardado en archivo fallback")
                    return False
                    
            except ImportError as e:
                logger.error(f"❌ Error importando mysql_simple: {e}")
                return False
            except Exception as e:
                logger.error(f"❌ Error registrando en MySQL: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error general en registro MySQL: {e}")
            return False
    
    def obtener_datos_extraidos(self):
        """Retorna los datos extraídos (UUID y VIAJEGM)"""
        return {
            'uuid': self.datos_viaje.get('uuid'),
            'viajegm': self.datos_viaje.get('viajegm')
        }


def procesar_llegada_factura(driver, datos_viaje):
    """Función principal para procesar llegada y facturación CON EXTRACCIÓN AUTOMÁTICA"""
    try:
        logger.info("🚀 Iniciando ProcesadorLlegadaFactura CON EXTRACCIÓN AUTOMÁTICA...")
        procesador = ProcesadorLlegadaFactura(driver, datos_viaje)
        resultado = procesador.procesar_llegada_y_factura()
        
        if resultado:
            logger.info("✅ Proceso de llegada y facturación completado exitosamente")
            
            # Retornar también los datos extraídos
            datos_extraidos = procesador.obtener_datos_extraidos()
            logger.info(f"📊 Datos extraídos: {datos_extraidos}")
            
            # Actualizar datos_viaje con la información extraída
            if datos_extraidos['uuid']:
                datos_viaje['uuid'] = datos_extraidos['uuid']
            if datos_extraidos['viajegm']:
                datos_viaje['viajegm'] = datos_extraidos['viajegm']
                
        else:
            logger.error("❌ Error en proceso de llegada y facturación")
            
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Error en procesar_llegada_factura: {e}")
        return False

# Ejemplo de uso
if __name__ == "__main__":
    # Este bloque se ejecutaría solo si ejecutas este archivo directamente
    pass