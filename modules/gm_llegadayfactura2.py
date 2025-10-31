import logging
import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from datetime import datetime
from .pdf_extractor import extraer_datos_automatico
# SIMPLIFICADO: Solo importar sistema de log CSV
from viajes_log import registrar_viaje_exitoso as log_viaje_exitoso, registrar_viaje_fallido as log_viaje_fallido
# Importar nuevos módulos de mejora
from modules.screenshot_manager import ScreenshotManager
from modules.debug_logger import debug_logger

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instancia global del screenshot manager
screenshot_mgr = ScreenshotManager()

class ProcesadorLlegadaFactura:
    def __init__(self, driver, datos_viaje):
        self.driver = driver
        self.datos_viaje = datos_viaje
        self.wait = WebDriverWait(driver, 20)
        
    def procesar_llegada_y_factura(self):
        """Proceso principal de llegada y facturación CON EXTRACCIÓN AUTOMÁTICA"""
        paso_actual = "Inicialización"
        try:
            logger.info(" Iniciando proceso de llegada y facturación")
            debug_logger.info("Iniciando proceso de llegada y facturación")

            # Paso 1: Hacer clic en "Llegada"
            paso_actual = "Clic en link 'Llegada'"
            debug_logger.debug(f"Paso actual: {paso_actual}")
            if not self._hacer_clic_llegada():
                return False

            # Paso 2: Llenar fecha de llegada y status
            paso_actual = "Procesamiento de llegada (fecha y status)"
            debug_logger.debug(f"Paso actual: {paso_actual}")
            if not self._procesar_llegada():
                return False

            # Paso 3: Autorizar
            paso_actual = "Autorización del viaje"
            debug_logger.debug(f"Paso actual: {paso_actual}")
            if not self._autorizar():
                return False

            # Paso 4: Facturar
            paso_actual = "Proceso de facturación"
            debug_logger.debug(f"Paso actual: {paso_actual}")
            if not self._procesar_facturacion():
                return False

            logger.info(" Proceso de llegada y facturación completado exitosamente")
            return True

        except Exception as e:
            logger.error(f" Error en proceso de llegada y facturación - PASO: {paso_actual}")
            logger.error(f" Detalles del error: {e}")
            debug_logger.error(f"Error en paso '{paso_actual}': {e}")
            debug_logger.error(f"Traceback: {traceback.format_exc()}")

            # Capturar screenshot del error
            try:
                prefactura = self.datos_viaje.get('prefactura', 'UNKNOWN')
                screenshot_mgr.capturar_con_html(
                    self.driver,
                    prefactura=prefactura,
                    modulo="gm_llegadayfactura2",
                    detalle_error=f"{paso_actual}: {str(e)[:50]}"
                )
            except:
                pass  # Si falla la captura, no detener el proceso

            return False
    
    def _hacer_clic_llegada(self):
        """Hacer clic en el link de Llegada"""
        try:
            logger.info(" Procesando llegada...")
            
            # Buscar el link de Llegada
            llegada_link = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Llegada")))
            self.driver.execute_script("arguments[0].click();", llegada_link)
            time.sleep(2)  # Esperar a que cargue la ventana de llegada
            logger.info(" Link 'Llegada' clickeado")
            return True
            
        except Exception as e:
            logger.error(f" Error al hacer clic en 'Llegada': {e}")
            return False
    
    def _llenar_fecha_llegada_robusto(self, id_input, fecha_valor):
        """Método ROBUSTO para llenar fecha de llegada"""
        try:
            logger.info(f" Llenando fecha en {id_input}: {fecha_valor}")
            
            campo = self.wait.until(EC.element_to_be_clickable((By.ID, id_input)))
            
            # Verificar valor actual
            valor_actual = campo.get_attribute("value")
            
            # DOBLE CLIC
            campo.click()
            time.sleep(0.3)
            campo.click()
            time.sleep(0.2)
            
            # Limpiar campo completamente
            campo.send_keys(Keys.HOME)
            for _ in range(15):
                campo.send_keys(Keys.DELETE)
                
            # Obtener hora actual si existe, sino usar hora por defecto
            if valor_actual and " " in valor_actual:
                hora = valor_actual.split(" ")[1]
            else:
                hora = "14:00"
                
            # Insertar nueva fecha con hora
            nuevo_valor = f"{fecha_valor} {hora}"
            campo.send_keys(nuevo_valor)
            time.sleep(0.5)
            
            # Verificar que se insertó correctamente
            valor_final = campo.get_attribute("value")
            logger.info(f" Fecha insertada: {fecha_valor}")
            
            # Hacer ENTER para confirmar
            campo.send_keys(Keys.ENTER)
            time.sleep(0.3)
            
            return True
            
        except Exception as e:
            logger.error(f" Error al llenar fecha en {id_input}: {e}")
            return False
    
    def _procesar_llegada(self):
        """Procesa llegada con enfoque DIRECTO al botón Aceptar"""
        try:
            logger.info(" Procesando datos de llegada...")
            
            # Obtener fecha actual para la llegada
            fecha_llegada = datetime.now().strftime("%d/%m/%Y")
            
            # Llenar fecha de llegada usando método robusto
            if not self._llenar_fecha_llegada_robusto("EDT_LLEGADA", fecha_llegada):
                logger.error(" Error al insertar fecha de llegada")
                return False
            
            # Esperar un momento para que GM procese la fecha
            time.sleep(2)
            
            # Seleccionar status "TERMINADO" (valor 3)
            try:
                logger.info(" Seleccionando status TERMINADO...")
                
                status_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATESTATUSVIAJE"))))
                
                # Seleccionar TERMINADO
                status_select.select_by_value("3")  # TERMINADO
                time.sleep(1)
                
                # VERIFICAR SELECCIÓN
                status_select_verificacion = Select(self.driver.find_element(By.ID, "COMBO_CATESTATUSVIAJE"))
                seleccionado = status_select_verificacion.first_selected_option
                logger.info(f" Status seleccionado: {seleccionado.text}")
                
            except Exception as e:
                logger.error(f" Error al seleccionar status TERMINADO: {e}")
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
                logger.info(" BTN_ACEPTAR clickeado exitosamente")
                
                # Buscar el botón "No" que debería aparecer después
                try:
                    no_btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                    logger.info(" Botón 'No' detectado - Aceptar funcionó")
                    
                    # Hacer clic en "No"
                    self.driver.execute_script("arguments[0].click();", no_btn)
                    time.sleep(2)
                    logger.info(" Botón 'No' clickeado - Proceso completado")
                    return True
                    
                except Exception as no_error:
                    logger.warning(f" No se detectó botón 'No': {no_error}")
                    return False
                    
            except Exception as e:
                logger.error(f" Error buscando BTN_ACEPTAR: {e}")
                return False
            
        except Exception as e:
            logger.error(f" Error en proceso de llegada: {e}")
            return False
    
    def _autorizar(self):
        """Hacer clic en Autorizar y manejar confirmación"""
        try:
            logger.info(" Autorizando viaje...")
            
            autorizar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_AUTORIZAR")))
            
            # Hacer scroll al botón para asegurar visibilidad
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", autorizar_btn)
            time.sleep(0.5)
            
            # Usar JavaScript click para mayor confiabilidad
            self.driver.execute_script("arguments[0].click();", autorizar_btn)
            logger.info(" Botón 'Autorizar' clickeado")
            
            # Manejar posible alerta de confirmación del navegador
            try:
                alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                alert_text = alert.text
                logger.info(f" Alerta detectada: '{alert_text}'")
                alert.accept()
                logger.info(" Alerta de confirmación aceptada")
                
            except TimeoutException:
                pass
            except Exception as e:
                logger.warning(f" Error al manejar alerta: {e}")
            
            # Esperar un momento para que se procese la autorización
            time.sleep(2)
            
            # Verificar que apareció el botón "Facturar"
            try:
                facturar_check = self.wait.until(EC.presence_of_element_located((By.ID, "BTN_FACTURAR")))
                logger.info(" Viaje autorizado correctamente")
                return True
            except:
                logger.warning(" Botón 'Facturar' no apareció inmediatamente, continuando...")
                return True
            
        except Exception as e:
            logger.error(f" Error al autorizar viaje: {e}")
            return False
    
    def _procesar_facturacion(self):
        """Proceso completo de facturación CON EXTRACCIÓN AUTOMÁTICA"""
        try:
            logger.info(" Iniciando proceso de facturación...")
            
            # Hacer clic en "Facturar"
            try:
                facturar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_FACTURAR")))
                
                # Hacer scroll al botón
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", facturar_btn)
                time.sleep(0.5)
                
                # Usar JavaScript click
                self.driver.execute_script("arguments[0].click();", facturar_btn)
                time.sleep(2)
                logger.info(" Botón 'Facturar' clickeado")
            except Exception as e:
                logger.error(f" Error al hacer clic en 'Facturar': {e}")
                return False
            
            # Cambiar tipo de documento a "FACTURA CFDI - W"
            try:
                logger.info(" Cambiando tipo de documento a 'FACTURA CFDI - W'...")
                debug_logger.info("Intentando cambiar tipo de documento a FACTURA CFDI - W")

                # Esperar a que el combo esté disponible
                tipo_doc_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATTIPOSDOCUMENTOS"))))

                # Mostrar selección actual (por defecto)
                seleccionado_actual = tipo_doc_select.first_selected_option
                logger.info(f" Tipo documento por defecto: '{seleccionado_actual.text}' (valor: {seleccionado_actual.get_attribute('value')})")
                debug_logger.info(f"Tipo documento por defecto: {seleccionado_actual.text}")

                # Seleccionar directamente "FACTURA CFDI - W" (valor 8)
                logger.info(" Seleccionando 'FACTURA CFDI - W' (valor: 8)...")
                tipo_doc_select.select_by_value("8")
                time.sleep(1)

                # Verificar selección
                seleccionado = tipo_doc_select.first_selected_option
                logger.info(f" Tipo de documento seleccionado: '{seleccionado.text}' (valor: 8)")
                debug_logger.info(f"Tipo documento seleccionado: {seleccionado.text} (valor: 8)")

            except Exception as e:
                logger.error(f" Error al seleccionar tipo de documento: {e}")
                debug_logger.error(f"Error seleccionando tipo documento: {e}")
                debug_logger.error(f"Traceback: {traceback.format_exc()}")
                return False
            
            # Hacer clic en "Aceptar" para confirmar la facturación
            try:
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Aceptar')]/..")))
                self.driver.execute_script("arguments[0].click();", aceptar_btn)
                time.sleep(2)
                logger.info(" Botón 'Aceptar' clickeado")
            except Exception as e:
                logger.error(f" Error al hacer clic en 'Aceptar': {e}")
                return False
            
            # Confirmar timbrado con "Sí"
            try:
                logger.info(" Confirmando timbrado...")
                si_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_YES")))
                self.driver.execute_script("arguments[0].click();", si_btn)
                time.sleep(4)
                logger.info(" Confirmación 'Sí' para timbrado clickeada")
            except Exception as e:
                logger.error(f" Error al confirmar timbrado: {e}")
                return False
            
            # Procesar impresión y extracción de folio
            if not self._procesar_impresion_y_extraccion_automatica():
                return False
                
            return True
            
        except Exception as e:
            logger.error(f" Error en proceso de facturación: {e}")
            return False
    
    def _procesar_impresion_y_extraccion_automatica(self):
        """Procesar impresión y extraer folio fiscal AUTOMÁTICAMENTE"""
        try:
            logger.info(" Procesando impresión y extracción automática...")
            
            # Hacer clic en "Regresar" si está disponible
            try:
                regresar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_REGRESAR")))
                self.driver.execute_script("arguments[0].click();", regresar_btn)
                time.sleep(1)
                logger.info(" Botón 'Regresar' clickeado")
            except Exception as e:
                logger.warning(f" Botón 'Regresar' no encontrado: {e}")
            
            # Hacer clic en "Imprimir" y extraer datos automáticamente
            try:
                imprimir_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_IMPRIMIR")))
                
                logger.info(" INICIANDO EXTRACCIÓN AUTOMÁTICA DE DATOS")
                
                # Configurar descarga automática antes de hacer clic
                from .pdf_extractor import PDFExtractor
                extractor = PDFExtractor("pdfs_temporales")
                extractor.configurar_descarga_chrome(self.driver)
                
                # Hacer clic en "Imprimir" para que se descargue el PDF
                self.driver.execute_script("arguments[0].click();", imprimir_btn)
                logger.info(" Botón 'Imprimir' clickeado - Iniciando descarga automática")
                
                # Esperar y extraer datos automáticamente
                datos_extraidos = extraer_datos_automatico(self.driver, "pdfs_temporales", timeout=20)
                
                # Verificar extracción
                uuid_extraido = datos_extraidos.get("uuid")
                viajegm_extraido = datos_extraidos.get("viaje_gm")
                numero_factura_extraido = datos_extraidos.get("numero_factura")
                
                logger.info(f" Datos extraídos: UUID={uuid_extraido}, VIAJEGM={viajegm_extraido}")
                
                # Guardar los datos extraídos en datos_viaje
                if uuid_extraido:
                    self.datos_viaje['uuid'] = uuid_extraido
                else:
                    logger.warning(" No se pudo extraer UUID del PDF")
                    
                if viajegm_extraido:
                    self.datos_viaje['viajegm'] = viajegm_extraido
                else:
                    logger.warning(" No se pudo extraer VIAJEGM del PDF")
                
                if numero_factura_extraido:
                    self.datos_viaje['numero_factura'] = numero_factura_extraido
                else:
                    logger.warning(" No se pudo extraer número de factura del PDF")
                
                # SIMPLIFICADO: REGISTRAR VIAJE EXITOSO SOLO EN CSV
                logger.info(" Registrando viaje exitoso en log CSV...")
                if not self._registrar_viaje_exitoso_csv():
                    logger.warning(" Error registrando en log CSV - continuando proceso")
                
            except Exception as e:
                logger.error(f" Error al hacer clic en 'Imprimir' o extraer datos: {e}")
                return False
            
            # Cerrar ventana de impresión
            try:
                # Buscar botón de cerrar
                cerrar_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@class='btnvalignmiddle' and normalize-space(text())='']/..")))
                self.driver.execute_script("arguments[0].click();", cerrar_btn)
                time.sleep(1)
                logger.info(" Ventana de impresión cerrada")
            except Exception as e:
                logger.warning(f" No se pudo cerrar ventana de impresión automáticamente: {e}")
                # Intentar con Escape
                try:
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(1)
                    logger.info(" Ventana cerrada con Escape")
                except:
                    logger.warning(" No se pudo cerrar con Escape")
            
            # Marcar como NO impreso
            try:
                no_impreso_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                self.driver.execute_script("arguments[0].click();", no_impreso_btn)
                time.sleep(1)
                logger.info(" Marcado como 'No impreso'")
            except Exception as e:
                logger.warning(f" No se pudo marcar como 'No impreso': {e}")
            
            logger.info(" Proceso de impresión y extracción automática completado")
            return True
            
        except Exception as e:
            logger.error(f" Error en proceso de impresión y extracción automática: {e}")
            return False
    
    def _registrar_viaje_exitoso_csv(self):
        """
        FUNCIÓN SIMPLIFICADA: Registra viaje exitoso SOLO en CSV
        """
        try:
            logger.info(" Registrando viaje exitoso en CSV...")
            
            # Extraer datos básicos
            prefactura = self.datos_viaje.get('prefactura')
            fecha_viaje = self.datos_viaje.get('fecha')
            uuid = self.datos_viaje.get('uuid')
            viajegm = self.datos_viaje.get('viajegm')
            numero_factura = self.datos_viaje.get('numero_factura')
            placa_tractor = self.datos_viaje.get('placa_tractor')
            placa_remolque = self.datos_viaje.get('placa_remolque')
            determinante = self.datos_viaje.get('clave_determinante')
            importe = self.datos_viaje.get('importe')
            cliente_codigo = self.datos_viaje.get('cliente_codigo')
            
            # Validaciones básicas
            if not prefactura:
                logger.error(" Error crítico: No hay prefactura para registrar")
                return False
                
            if not fecha_viaje:
                logger.error(" Error crítico: No hay fecha para registrar")
                return False
            
            # Registrar en log CSV unificado
            try:
                exito_csv = log_viaje_exitoso(
                    prefactura=prefactura,
                    determinante=determinante,
                    fecha_viaje=fecha_viaje,
                    placa_tractor=placa_tractor,
                    placa_remolque=placa_remolque,
                    uuid=uuid,
                    viajegm=viajegm,
                    numero_factura=numero_factura,
                    importe=importe,
                    cliente_codigo=cliente_codigo
                )
                
                if exito_csv:
                    logger.info(f" Viaje EXITOSO registrado: {prefactura}")
                    logger.info(f"    UUID: {uuid or 'No extraído'}")
                    logger.info(f"    Viaje GM: {viajegm or 'No extraído'}")
                    return True
                else:
                    logger.error(" Error registrando en log CSV")
                    return False
                    
            except Exception as e:
                logger.error(f" Error registrando en log CSV: {e}")
                return False
                
        except Exception as e:
            logger.error(f" Error general en registro CSV: {e}")
            return False
    
    def obtener_datos_extraidos(self):
        """Retorna los datos extraídos (UUID y VIAJEGM)"""
        return {
            'uuid': self.datos_viaje.get('uuid'),
            'viajegm': self.datos_viaje.get('viajegm')
        }


def procesar_llegada_factura(driver, datos_viaje):
    """
    FUNCIÓN MEJORADA: Procesar llegada y facturación CON REGISTRO AUTOMÁTICO DE ERRORES
    """
    try:
        logger.info(" Iniciando ProcesadorLlegadaFactura...")
        procesador = ProcesadorLlegadaFactura(driver, datos_viaje)
        resultado = procesador.procesar_llegada_y_factura()
        
        prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA') if datos_viaje else 'DESCONOCIDA'
        
        if resultado:
            logger.info(f" VIAJE {prefactura}: Llegada y facturación completada exitosamente")
            
            # Retornar también los datos extraídos
            datos_extraidos = procesador.obtener_datos_extraidos()
            
            # Actualizar datos_viaje con la información extraída
            if datos_extraidos['uuid']:
                datos_viaje['uuid'] = datos_extraidos['uuid']
            if datos_extraidos['viajegm']:
                datos_viaje['viajegm'] = datos_extraidos['viajegm']
                
        else:  # resultado == False - CUALQUIER ERROR
            # Intentar extraer detalles del error del debug.log
            detalle_error = "Error en llegada y facturación"
            try:
                with open('debug.log', 'r', encoding='utf-8') as f:
                    ultimas_lineas = f.readlines()[-30:]
                    for linea in reversed(ultimas_lineas):
                        if prefactura in linea:
                            if 'FALLO CRÍTICO' in linea or 'ERROR' in linea:
                                # Extraer descripción del error
                                if 'BTN_' in linea or 'EDT_' in linea:
                                    elemento = linea.split('BTN_')[1].split()[0] if 'BTN_' in linea else linea.split('EDT_')[1].split()[0]
                                    detalle_error = f"Error en llegada - Elemento {elemento} no accesible"
                                elif 'not clickable' in linea:
                                    detalle_error = "Error en llegada - Elemento no clickable"
                                elif 'Timeout' in linea:
                                    detalle_error = "Error en llegada - Timeout esperando elemento"
                                elif 'PDF' in linea or 'pdf' in linea:
                                    detalle_error = "Error en llegada - Problema con PDF"
                                break
            except:
                pass  # Si no se puede leer debug.log, usar mensaje genérico

            logger.error(f" VIAJE {prefactura} FALLÓ: {detalle_error}")

            # Registrar error con detalles específicos en CSV
            if datos_viaje:
                try:
                    log_viaje_fallido(
                        prefactura=datos_viaje.get('prefactura', 'DESCONOCIDA'),
                        motivo_fallo=detalle_error,
                        determinante=datos_viaje.get('clave_determinante', ''),
                        fecha_viaje=datos_viaje.get('fecha', ''),
                        placa_tractor=datos_viaje.get('placa_tractor', ''),
                        placa_remolque=datos_viaje.get('placa_remolque', ''),
                        importe=datos_viaje.get('importe', ''),
                        cliente_codigo=datos_viaje.get('cliente_codigo', '')
                    )
                    logger.info(" Error de GM_LLEGADAYFACTURA2 registrado en CSV")
                except Exception as log_error:
                    logger.error(f" Error registrando fallo en CSV: {log_error}")
            
        return resultado
        
    except Exception as e:
        # Crear mensaje de error específico con la excepción
        prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA') if datos_viaje else 'DESCONOCIDA'
        error_detallado = f"Error en llegada - {str(e)[:100]}"
        logger.error(f" Error en procesar_llegada_factura: {error_detallado}")
        logger.error(f" VIAJE {prefactura} FALLÓ: {error_detallado}")

        # Registrar errores de excepción general con detalles específicos
        if datos_viaje:
            try:
                log_viaje_fallido(
                    prefactura=datos_viaje.get('prefactura', 'DESCONOCIDA'),
                    motivo_fallo=error_detallado,
                    determinante=datos_viaje.get('clave_determinante', ''),
                    fecha_viaje=datos_viaje.get('fecha', ''),
                    placa_tractor=datos_viaje.get('placa_tractor', ''),
                    placa_remolque=datos_viaje.get('placa_remolque', ''),
                    importe=datos_viaje.get('importe', ''),
                    cliente_codigo=datos_viaje.get('cliente_codigo', '')
                )
                logger.info(" Excepción de GM_LLEGADAYFACTURA2 registrada en CSV")
            except Exception as log_error:
                logger.error(f" Error registrando excepción en CSV: {log_error}")
        
        return False

# Ejemplo de uso
if __name__ == "__main__":
    # Este bloque se ejecutaría solo si ejecutas este archivo directamente
    pass