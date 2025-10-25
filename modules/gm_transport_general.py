from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
import os
import logging
from datetime import datetime
from .gm_facturacion1 import ir_a_facturacion
from .gm_salida import procesar_salida_viaje
from .gm_llegadayfactura2 import procesar_llegada_factura
from .parser import parse_xls
from viajes_log import registrar_viaje_fallido as log_viaje_fallido
# Importar módulos de mejora
from .screenshot_manager import ScreenshotManager
from .debug_logger import debug_logger

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instancia global del screenshot manager
screenshot_mgr = ScreenshotManager()

class GMTransportAutomation:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)
        self.datos_viaje = {}
        
    def registrar_error_viaje(self, tipo_error, detalle=""):
        """Registra errores en el log CSV"""
        prefactura = self.datos_viaje.get('prefactura', 'DESCONOCIDA')
        placa_tractor = self.datos_viaje.get('placa_tractor', 'DESCONOCIDA')
        placa_remolque = self.datos_viaje.get('placa_remolque', 'DESCONOCIDA')
        determinante = self.datos_viaje.get('clave_determinante', 'DESCONOCIDO')
        fecha_viaje = self.datos_viaje.get('fecha', '')
        importe = self.datos_viaje.get('importe', '')
        cliente_codigo = self.datos_viaje.get('cliente_codigo', '')
        
        try:
            motivo_completo = f"{tipo_error}"
            if detalle:
                motivo_completo += f" - {detalle}"
                
            exito_log = log_viaje_fallido(
                prefactura=prefactura,
                motivo_fallo=motivo_completo,
                determinante=determinante,
                fecha_viaje=fecha_viaje,
                placa_tractor=placa_tractor,
                placa_remolque=placa_remolque,
                importe=importe,
                cliente_codigo=cliente_codigo
            )
            
            if exito_log:
                logger.info("Error registrado en log CSV")
            else:
                logger.warning("Error registrando en log CSV")
                
        except Exception as e:
            logger.warning(f"Error registrando en log CSV: {e}")
        
        logger.error("VIAJE REQUIERE ATENCIÓN MANUAL")
        logger.error(f"PREFACTURA: {prefactura}")
        logger.error(f"PLACA TRACTOR: {placa_tractor}")
        logger.error(f"PLACA REMOLQUE: {placa_remolque}")
        logger.error(f"DETERMINANTE: {determinante}")
        logger.error(f"ERROR: {tipo_error}")
        if detalle:
            logger.error(f"DETALLE: {detalle}")
        logger.error("ACCIÓN REQUERIDA: Revisar y completar manualmente en GM Transport")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'prefactura': prefactura,
            'placa_tractor': placa_tractor,
            'placa_remolque': placa_remolque,
            'determinante': determinante,
            'tipo_error': tipo_error,
            'detalle': detalle
        }
    
    def registrar_determinante_faltante_csv(self, determinante_faltante):
        """Registra determinantes faltantes en CSV"""
        try:
            prefactura = self.datos_viaje.get('prefactura', 'DESCONOCIDA')
            fecha_viaje = self.datos_viaje.get('fecha', '')
            placa_tractor = self.datos_viaje.get('placa_tractor', '')
            placa_remolque = self.datos_viaje.get('placa_remolque', '')
            importe = self.datos_viaje.get('importe', '')
            cliente_codigo = self.datos_viaje.get('cliente_codigo', '')
            
            motivo_fallo = f"Determinante {determinante_faltante} no encontrada"
            
            exito_log = log_viaje_fallido(
                prefactura=prefactura,
                motivo_fallo=motivo_fallo,
                determinante=determinante_faltante,
                fecha_viaje=fecha_viaje,
                placa_tractor=placa_tractor,
                placa_remolque=placa_remolque,
                importe=importe,
                cliente_codigo=cliente_codigo
            )
            
            if exito_log:
                logger.error("DETERMINANTE FALTANTE REGISTRADA:")
                logger.error(f"Prefactura: {prefactura}")
                logger.error(f"Determinante faltante: {determinante_faltante}")
                logger.error(f"Placas: {placa_tractor} / {placa_remolque}")
                logger.error("ACCIÓN: Agregar determinante a clave_ruta_base.csv")
                return True
            else:
                logger.warning("Error registrando en log CSV")
                return False
                
        except Exception as e:
            logger.error(f"Error registrando determinante faltante: {e}")
            return False
    
    def obtener_ruta_y_base(self, determinante):
        """Obtiene la ruta GM y base origen desde el CSV"""
        csv_path = 'modules/clave_ruta_base.csv'
        
        logger.info(f"Buscando ruta para determinante: {determinante}")
        
        try:
            if not os.path.exists(csv_path):
                logger.error(f"No existe el archivo: {csv_path}")
                return None, None, "ARCHIVO_CSV_NO_EXISTE"
                
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                determinantes_disponibles = []
                
                for i, row in enumerate(reader):
                    determinantes_disponibles.append(row['determinante'])
                    
                    if row['determinante'] == str(determinante):
                        logger.info(f"Determinante {determinante} -> ruta {row['ruta_gm']}, base {row['base_origen']}")
                        return row['ruta_gm'], row['base_origen'], "ENCONTRADO"
                
                logger.error("DETERMINANTE NO ENCONTRADA")
                logger.error(f"Determinante buscada: {determinante}")
                logger.error("Esta determinante debe agregarse al archivo clave_ruta_base.csv")
                
                return None, None, "DETERMINANTE_NO_ENCONTRADA"
                        
        except Exception as e:
            logger.error(f"Error al leer CSV: {e}")
            return None, None, "ERROR_LECTURA_CSV"
    
    def llenar_fecha(self, id_input, fecha_valor, incluir_hora=True):
        """
        FUNCIÓN MEJORADA V2: Llena fecha usando JavaScript para EVITAR abrir calendarios

        Args:
            id_input: ID del campo de fecha
            fecha_valor: Fecha en formato DD/MM/YYYY
            incluir_hora: Si True, incluye hora (por defecto True para compatibilidad)

        Returns:
            bool: True si se insertó correctamente, False si falló
        """
        try:
            logger.info(f"Llenando {id_input} con fecha {fecha_valor} (hora={'sí' if incluir_hora else 'no'})")
            debug_logger.info(f"Llenando fecha {id_input} con valor {fecha_valor}, incluir_hora={incluir_hora}")

            # Verificar que el elemento existe
            try:
                elemento_existe = self.driver.find_element(By.ID, id_input)
            except Exception as e:
                logger.error(f"Elemento {id_input} NO ENCONTRADO: {e}")
                debug_logger.error(f"Campo {id_input} no encontrado: {e}")
                return False

            # Determinar si incluir hora
            if incluir_hora:
                # Obtener valor actual para extraer la hora (si existe)
                try:
                    valor_actual = self.driver.execute_script(f"return document.getElementById('{id_input}').value;")
                    if valor_actual and " " in valor_actual:
                        hora = valor_actual.split(" ")[1]
                    else:
                        hora = "14:00"
                except:
                    hora = "14:00"
                # Construir nuevo valor con fecha y hora
                nuevo_valor = f"{fecha_valor} {hora}"
            else:
                # Solo fecha, sin hora
                nuevo_valor = fecha_valor

            # MÉTODO MEJORADO: Usar JavaScript para evitar abrir calendarios
            for intento in range(3):
                try:
                    # PRIMERO: Cerrar cualquier alert que pueda estar bloqueando
                    try:
                        alert = self.driver.switch_to.alert
                        alert_text = alert.text
                        logger.warning(f"⚠️ Alert detectado ANTES de llenar campo: '{alert_text}' - Cerrando...")
                        debug_logger.warning(f"Alert previo en {id_input}: {alert_text}")
                        alert.accept()
                        logger.info("✅ Alert previo cerrado")
                        time.sleep(0.3)
                    except:
                        pass  # No había alert, continuamos normal

                    logger.info(f"Intento {intento + 1}/3 de llenar fecha con JavaScript")

                    # Usar JavaScript directo para llenar el campo SIN abrirlo
                    script = f"""
                    var campo = document.getElementById('{id_input}');
                    if (campo) {{
                        campo.value = '{nuevo_valor}';
                        campo.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        campo.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        campo.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        return true;
                    }}
                    return false;
                    """

                    resultado = self.driver.execute_script(script)

                    if not resultado:
                        logger.warning(f"Campo {id_input} no encontrado en intento {intento + 1}")
                        time.sleep(1)
                        continue

                    # Esperar un momento para que se procese
                    time.sleep(0.5)

                    # Verificar que se llenó correctamente
                    valor_final = self.driver.execute_script(f"return document.getElementById('{id_input}').value;")

                    if valor_final and fecha_valor in valor_final:
                        logger.info(f"✅ Fecha insertada correctamente con JavaScript: {valor_final}")
                        debug_logger.info(f"✅ Fecha {id_input} = {valor_final}")
                        return True
                    else:
                        logger.warning(f"⚠️ Verificación falló. Esperado: {nuevo_valor}, Actual: {valor_final}")
                        time.sleep(1)
                        continue

                except Exception as e:
                    # Manejar alerts de "Valor no válido" que bloquean la página
                    try:
                        alert = self.driver.switch_to.alert
                        alert_text = alert.text
                        logger.warning(f"⚠️ Alert detectado y cerrando: '{alert_text}'")
                        debug_logger.warning(f"Alert en {id_input}: {alert_text}")
                        alert.accept()  # Cerrar el alert
                        logger.info("✅ Alert cerrado - reintentando")
                        time.sleep(0.5)
                    except:
                        pass  # No había alert

                    logger.error(f"❌ Error en intento {intento + 1}: {str(e)[:100]}")
                    debug_logger.error(f"Error llenando fecha {id_input} intento {intento + 1}: {e}")
                    time.sleep(1)
                    continue

            # Si llegamos aquí, fallaron todos los intentos
            logger.error(f"❌ ERROR CRÍTICO: No se pudo insertar fecha después de 3 intentos")
            debug_logger.error(f"FALLO CRÍTICO llenando fecha {id_input} con valor {fecha_valor}")
            return False

        except Exception as e:
            logger.error(f"❌ Error en llenar_fecha: {e}")
            debug_logger.error(f"Excepción en llenar_fecha para {id_input}: {e}")
            import traceback
            debug_logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def llenar_campo_texto(self, id_input, valor, descripcion=""):
        """Llena un campo de texto de forma robusta"""
        try:
            campo = self.wait.until(EC.element_to_be_clickable((By.ID, id_input)))
            campo.click()
            campo.clear()
            campo.send_keys(str(valor))
            logger.info(f"{descripcion} '{valor}' insertado en {id_input}")
            return True
            
        except Exception as e:
            logger.error(f"Error al llenar {descripcion} en {id_input}: {e}")
            return False
    
    def seleccionar_base_origen(self, base_origen):
        """Selecciona la base origen del combo"""
        if not base_origen:
            logger.error("No se proporcionó base origen")
            return False
            
        try:
            base_origen_texto = f"BASE {base_origen.strip().upper()}"
            base_combo = self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATSUCURSALES")))
            self.driver.execute_script("arguments[0].click();", base_combo)
            time.sleep(0.5)
            
            opciones = base_combo.find_elements(By.TAG_NAME, "option")
            for option in opciones:
                if option.text.strip().upper() == base_origen_texto:
                    valor_encontrado = option.get_attribute("value")
                    script = f"""
                        var select = document.getElementById('COMBO_CATSUCURSALES');
                        select.value = '{valor_encontrado}';
                        var event = new Event('change', {{ bubbles: true }});
                        select.dispatchEvent(event);
                    """
                    self.driver.execute_script(script)
                    logger.info(f"Base origen '{base_origen_texto}' seleccionada")
                    return True
                    
            logger.error(f"No se encontró la opción '{base_origen_texto}'")
            return False
            
        except Exception as e:
            logger.error(f"Error al seleccionar base origen: {e}")
            return False
    
    def buscar_y_seleccionar_placa(self, tipo_placa, placa_valor):
        """Busca y selecciona una placa (remolque o tractor)"""
        try:
            logger.info(f"Buscando {tipo_placa}: {placa_valor}")
            
            if tipo_placa == 'remolque':
                btn_buscar = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_BUSCARCODIGOUNIDADCARGA1")))
            else:
                btn_buscar = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_BUSCARCODIGOUNIDADCAMION")))
            
            btn_buscar.click()
            time.sleep(1.5)
            logger.info(f"Buscador de {tipo_placa} abierto")
            
            try:
                checkbox_filtro = self.wait.until(EC.element_to_be_clickable((By.ID, "CBOX_FILTRARRENTADAS_1")))
                if checkbox_filtro.is_selected():
                    checkbox_filtro.click()
                    time.sleep(0.3)
                    logger.info(f"Filtro de unidades rentadas deshabilitado para {tipo_placa}")
            except Exception as e:
                logger.warning(f"No se pudo desmarcar filtro para {tipo_placa}: {e}")
            
            campo_busqueda = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_BUSQUEDA")))
            campo_busqueda.clear()
            campo_busqueda.send_keys(placa_valor)
            logger.info(f"Placa {placa_valor} ingresada en buscador")
            
            btn_aplicar = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@class='btnvalignmiddle' and contains(text(), 'Aplicar')]/..")))
            btn_aplicar.click()
            time.sleep(3)
            logger.info(f"Búsqueda aplicada para {tipo_placa}")
            
            try:
                btn_seleccionar = self.driver.find_element(By.ID, "BTN_SELECCIONAR")
                if not btn_seleccionar.is_enabled():
                    error_msg = f"Placa {tipo_placa} {placa_valor} no encontrada"
                    logger.error(error_msg)
                    try:
                        cerrar_btn = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Cerrar')]/..")
                        cerrar_btn.click()
                    except:
                        pass
                    return False, error_msg
                
                btn_seleccionar.click()
                time.sleep(1)
                logger.info(f"{tipo_placa.capitalize()} {placa_valor} seleccionado")
                return True, ""
                
            except Exception as e:
                error_msg = f"Placa {tipo_placa} {placa_valor} no encontrada"
                logger.error(error_msg)
                try:
                    cerrar_btn = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Cerrar')]/..")
                    cerrar_btn.click()
                except:
                    pass
                return False, error_msg
            
        except Exception as e:
            error_msg = f"Error buscando {tipo_placa} {placa_valor}"
            logger.error(error_msg)
            return False, error_msg
    
    def seleccionar_remolque(self):
        """Selecciona el remolque usando la placa"""
        placa_remolque = self.datos_viaje.get('placa_remolque')
        if not placa_remolque:
            logger.error("No se encontró placa_remolque en los datos")
            return False, "DATOS_INCOMPLETOS_PLACA_REMOLQUE"
            
        exito, error = self.buscar_y_seleccionar_placa('remolque', placa_remolque)
        return exito, error
    
    def seleccionar_tractor_y_operador(self):
        """Selecciona el tractor y verifica que tenga operador asignado"""
        placa_tractor = self.datos_viaje.get('placa_tractor')
        if not placa_tractor:
            logger.error("No se encontró placa_tractor en los datos")
            return False, "DATOS_INCOMPLETOS_PLACA_TRACTOR"
            
        try:
            asignar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ASIGNARCAMION")))
            asignar_btn.click()
            time.sleep(1.5)
            logger.info("Modal de asignación operador/camión abierto")
            
            exito, error = self.buscar_y_seleccionar_placa('tractor', placa_tractor)
            if not exito:
                return False, error

            fecha_valor = self.datos_viaje['fecha']
            # Estos campos del modal NO aceptan hora, solo fecha
            self.llenar_fecha("EDT_FECHACARGATRAYECTO", fecha_valor, incluir_hora=False)
            self.llenar_fecha("EDT_FECHAESTIMADACARGA", fecha_valor, incluir_hora=False)
            
            logger.info("Esperando asignación automática de operador...")
            time.sleep(5)
            
            operador_asignado = False
            
            try:
                posibles_ids_operador = [
                    "EDT_OPERADOR", 
                    "EDT_CHOFER", 
                    "EDT_CONDUCTOR",
                    "EDT_OPERADOR1",
                    "COMBO_OPERADOR",
                    "EDT_NOMBREOPERADOR",
                    "EDT_CODIGOOPERADOR"
                ]
                
                for id_operador in posibles_ids_operador:
                    try:
                        operador_campo = self.driver.find_element(By.ID, id_operador)
                        valor_operador = operador_campo.get_attribute("value")
                        
                        if valor_operador and valor_operador.strip() and valor_operador != "0" and len(valor_operador.strip()) > 2:
                            logger.info(f"Operador encontrado: {valor_operador}")
                            operador_asignado = True
                            break
                            
                    except:
                        continue
                
                if not operador_asignado:
                    try:
                        elementos_operador = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Operador') or contains(text(), 'OPERADOR') or contains(text(), 'Chofer') or contains(text(), 'CHOFER')]")
                        for elem in elementos_operador:
                            try:
                                texto_parent = elem.find_element(By.XPATH, "..").text
                                
                                if ":" in texto_parent:
                                    nombre_operador = texto_parent.split(":")[-1].strip()
                                    if len(nombre_operador) > 3 and not nombre_operador.isdigit():
                                        logger.info(f"Operador detectado: {nombre_operador}")
                                        operador_asignado = True
                                        break
                            except:
                                continue
                    except:
                        pass
                
                if not operador_asignado:
                    try:
                        todos_inputs = self.driver.find_elements(By.XPATH, "//input[@type='text']")
                        for input_elem in todos_inputs:
                            try:
                                valor = input_elem.get_attribute("value")
                                if valor and len(valor) > 5 and " " in valor and not valor.isdigit():
                                    logger.info(f"Posible operador encontrado: {valor}")
                                    operador_asignado = True
                                    break
                            except:
                                continue
                    except:
                        pass
                        
            except Exception as e:
                logger.warning(f"Error verificando operador: {e}")
                
            if not operador_asignado:
                logger.error("PLACA SIN OPERADOR ASIGNADO")
                logger.error(f"Placa: {placa_tractor} no tiene operador disponible")
                
                try:
                    posibles_botones_cerrar = ["BTN_CANCELAR", "BTN_CERRAR", "BTN_CANCELARTRAYECTO"]
                    for btn_id in posibles_botones_cerrar:
                        try:
                            cancelar_btn = self.driver.find_element(By.ID, btn_id)
                            self.driver.execute_script("arguments[0].click();", cancelar_btn)
                            time.sleep(1)
                            logger.info(f"Modal cerrado con {btn_id}")
                            break
                        except:
                            continue
                    else:
                        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                        logger.info("Modal cerrado con Escape")
                except Exception as e:
                    logger.warning(f"Error cerrando modal: {e}")
                
                return False, "Sin operador asignado"
            
            logger.info("Operador asignado correctamente")
            
            try:
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTARTRAYECTO")))
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", aceptar_btn)
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", aceptar_btn)
                logger.info("Tractor y operador asignados exitosamente")
                return True, ""
                
            except Exception as e:
                logger.error(f"Error al aceptar modal: {e}")
                return False, "ERROR_ACEPTAR_MODAL"
                
        except Exception as e:
            logger.error(f"Error al seleccionar tractor: {e}")
            return False, "ERROR_SELECCION_TRACTOR"
    
    def fill_viaje_form(self):
        """Función principal para llenar formulario de viaje CON LOGGING Y SCREENSHOTS MEJORADOS"""
        paso_actual = "Inicialización"
        try:
            logger.info("Iniciando llenado de formulario de viaje")
            debug_logger.info("Iniciando fill_viaje_form")

            if not self.datos_viaje:
                logger.error("ERROR CRÍTICO: No hay datos del viaje")
                debug_logger.error("ERROR CRÍTICO: No hay datos del viaje")
                return False

            campos_requeridos = ['fecha', 'prefactura', 'cliente_codigo', 'importe', 'clave_determinante', 'placa_tractor', 'placa_remolque']
            campos_faltantes = [campo for campo in campos_requeridos if not self.datos_viaje.get(campo)]

            if campos_faltantes:
                logger.error(f"ERROR CRÍTICO: Campos faltantes: {campos_faltantes}")
                debug_logger.error(f"Campos faltantes en datos_viaje: {campos_faltantes}")
                return False

            logger.info("Datos del viaje validados correctamente")
            debug_logger.info(f"Datos del viaje validados: {self.datos_viaje.get('prefactura')}")
            
            paso_actual = "Navegación a crear viaje"
            debug_logger.debug(f"Paso actual: {paso_actual}")

            from .navigate_to_create_viaje import navigate_to_create_viaje
            logger.info("Navegando al módulo de creación de viajes...")
            if not navigate_to_create_viaje(self.driver):
                logger.error("Error al navegar al módulo de viajes")
                debug_logger.error(f"Error en {paso_actual}")
                # Capturar screenshot del error
                try:
                    screenshot_mgr.capturar_con_html(
                        self.driver,
                        prefactura=self.datos_viaje.get('prefactura', 'UNKNOWN'),
                        modulo="gm_transport_general",
                        detalle_error=f"{paso_actual}: No se pudo navegar"
                    )
                except:
                    pass
                return False
            
            fecha_valor = self.datos_viaje['fecha']
            prefactura_valor = self.datos_viaje['prefactura']
            cliente_codigo = self.datos_viaje['cliente_codigo']
            total_factura_valor = str(self.datos_viaje['importe'])
            clave_determinante = self.datos_viaje['clave_determinante']
            
            logger.info(f"Procesando viaje REAL: Prefactura {prefactura_valor}")
            
            self.llenar_campo_texto("EDT_NOVIAJECLIENTE", prefactura_valor, "Prefactura")
            self.llenar_campo_texto("EDT_NUMEROCLIENTE", cliente_codigo, "Cliente")
            
            fechas_con_hora = [
                "EDT_FECHA",
                "EDT_FECHAESTATUS", 
                "EDT_FECHACARGA",
            ]
            
            logger.info("Llenando fechas 1-3 con hora...")
            for i, fecha_id in enumerate(fechas_con_hora, 1):
                self.llenar_fecha(fecha_id, fecha_valor)
            
            logger.info("Llenando fecha 4/4: EDT_FECHAENTREGA SIN hora")
            try:
                self.driver.execute_script("""
                    var campo = document.getElementById('EDT_FECHAENTREGA');
                    if (campo) {
                        campo.value = arguments[0];
                        campo.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                """, fecha_valor)
                logger.info(f"Fecha 4 completada: {fecha_valor} (sin hora)")
            except Exception as e:
                logger.error(f"Error en fecha 4: {e}")
            
            time.sleep(1)
            
            paso_actual = "Llenado de fechas del viaje"
            debug_logger.debug(f"Paso actual: {paso_actual}")

            logger.info("Moviendo foco al campo de ruta...")
            try:
                campo_ruta = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_FOLIORUTA")))
                campo_ruta.click()
                time.sleep(0.5)
                logger.info("Enfoque movido al campo de ruta")
            except Exception as e:
                logger.warning(f"No se pudo hacer clic en campo de ruta: {e}")
                debug_logger.warning(f"No se pudo hacer clic en campo de ruta: {e}")

            paso_actual = "Obtención de ruta y determinante"
            debug_logger.debug(f"Paso actual: {paso_actual}")

            logger.info("Obteniendo ruta GM...")
            ruta_gm, base_origen, estado_determinante = self.obtener_ruta_y_base(clave_determinante)
            
            if estado_determinante == "DETERMINANTE_NO_ENCONTRADA":
                logger.error("DETERMINANTE NO ENCONTRADA - REGISTRANDO ERROR Y TERMINANDO VIAJE")
                
                if self.registrar_determinante_faltante_csv(clave_determinante):
                    logger.error("Error registrado exitosamente en log CSV")
                else:
                    logger.error("Error registrando en log CSV")
                
                logger.error("RETORNANDO FALSE - El sistema continuará con el siguiente viaje")
                return False
            
            elif estado_determinante in ["ARCHIVO_CSV_NO_EXISTE", "ERROR_LECTURA_CSV"]:
                logger.error(f"ERROR CRÍTICO EN DETERMINANTES: {estado_determinante}")
                self.registrar_error_viaje(
                    estado_determinante,
                    f"Error técnico con archivo clave_ruta_base.csv"
                )
                return False
            
            elif estado_determinante == "ENCONTRADO":
                logger.info(f"Determinante válida: {clave_determinante} -> Ruta: {ruta_gm}, Base: {base_origen}")
                
                self.llenar_campo_texto("EDT_FOLIORUTA", ruta_gm, "Ruta GM")
                
                time.sleep(0.5)
                script = """
                    var input = document.getElementById('EDT_FOLIORUTA');
                    if (input) {
                        var event = new Event('change', { bubbles: true });
                        input.dispatchEvent(event);
                    }
                """
                self.driver.execute_script(script)
                time.sleep(1)
                logger.info("Evento change disparado para ruta")
                
                self.seleccionar_base_origen(base_origen)
            
            paso_actual = "Selección de remolque"
            debug_logger.debug(f"Paso actual: {paso_actual}")

            logger.info("Seleccionando remolque...")
            exito_remolque, error_remolque = self.seleccionar_remolque()
            if not exito_remolque:
                debug_logger.error(f"Error en {paso_actual}: {error_remolque}")
                self.registrar_error_viaje(error_remolque, f"No se pudo seleccionar remolque {self.datos_viaje.get('placa_remolque')}")
                logger.error("Error al seleccionar remolque - Viaje marcado para revisión manual")
                # Capturar screenshot del error
                try:
                    screenshot_mgr.capturar_con_html(
                        self.driver,
                        prefactura=self.datos_viaje.get('prefactura', 'UNKNOWN'),
                        modulo="gm_transport_general",
                        detalle_error=f"{paso_actual}: {error_remolque}"
                    )
                except:
                    pass
                return False
            
            paso_actual = "Selección de tractor y operador"
            debug_logger.debug(f"Paso actual: {paso_actual}")

            logger.info("Seleccionando tractor y verificando operador...")
            exito_tractor, error_tractor = self.seleccionar_tractor_y_operador()

            if not exito_tractor:
                debug_logger.error(f"Error en {paso_actual}: {error_tractor}")
                if error_tractor == "Sin operador asignado":
                    self.registrar_error_viaje("Sin operador asignado", f"Tractor {self.datos_viaje.get('placa_tractor')} no tiene operador asignado")
                    logger.error("VIAJE CANCELADO: Placa sin operador - Requiere asignación manual")
                    # Capturar screenshot
                    try:
                        screenshot_mgr.capturar_con_html(
                            self.driver,
                            prefactura=self.datos_viaje.get('prefactura', 'UNKNOWN'),
                            modulo="gm_transport_general",
                            detalle_error=f"{paso_actual}: Sin operador"
                        )
                    except:
                        pass
                    return False
                else:
                    self.registrar_error_viaje(error_tractor, f"Error con tractor {self.datos_viaje.get('placa_tractor')}")
                    logger.error("VIAJE CANCELADO: Error en selección de tractor")
                    # Capturar screenshot
                    try:
                        screenshot_mgr.capturar_con_html(
                            self.driver,
                            prefactura=self.datos_viaje.get('prefactura', 'UNKNOWN'),
                            modulo="gm_transport_general",
                            detalle_error=f"{paso_actual}: {error_tractor}"
                        )
                    except:
                        pass
                    return False
            
            logger.info("Ejecutando facturación inicial...")
            try:
                resultado_facturacion = ir_a_facturacion(self.driver, total_factura_valor, self.datos_viaje)
                if resultado_facturacion:
                    logger.info("Facturación inicial completada")
                else:
                    logger.warning("Problema en facturación inicial - continuando...")
            except Exception as e:
                logger.warning(f"Error en facturación inicial: {e} - continuando...")
            
            logger.info("Ejecutando proceso de SALIDA...")
            try:
                resultado_salida = procesar_salida_viaje(self.driver, self.datos_viaje, configurar_filtros=True)
                if resultado_salida == "OPERADOR_OCUPADO":
                    logger.error("OPERADOR OCUPADO detectado en proceso de salida")
                    logger.error("Error ya registrado en CSV por gm_salida.py")
                    return "OPERADOR_OCUPADO"
                elif not resultado_salida:
                    logger.error("Error en proceso de salida - Este viaje necesita revisión manual")
                    logger.error(f"VIAJE PARA REVISIÓN: Prefactura {prefactura_valor} - Error en salida")
                    return False
            except Exception as e:
                logger.error(f"Error crítico en salida: {e}")
                logger.error(f"VIAJE PARA REVISIÓN: Prefactura {prefactura_valor} - Error crítico en salida")
                return False
            
            logger.info("Ejecutando proceso de LLEGADA y FACTURACIÓN FINAL...")
            try:
                resultado_llegada = procesar_llegada_factura(self.driver, self.datos_viaje)
                if not resultado_llegada:
                    logger.error("Error en proceso de llegada y facturación - Este viaje necesita revisión manual")
                    logger.error(f"VIAJE PARA REVISIÓN: Prefactura {prefactura_valor} - Error en llegada/facturación")
                    return False
            except Exception as e:
                logger.error(f"Error crítico en llegada: {e}")
                logger.error(f"VIAJE PARA REVISIÓN: Prefactura {prefactura_valor} - Error crítico en llegada")
                return False
            
            logger.info("Proceso completo de automatización GM Transport exitoso")
            logger.info(f"VIAJE COMPLETADO: Prefactura {prefactura_valor} - Placa Tractor: {self.datos_viaje.get('placa_tractor')} - Placa Remolque: {self.datos_viaje.get('placa_remolque')}")
            return True

        except Exception as e:
            import traceback
            logger.error(f"Error general en fill_viaje_form - PASO: {paso_actual}")
            logger.error(f"Detalles del error: {e}")
            logger.error(f"Traceback completo:\n{traceback.format_exc()}")

            # Logging detallado con debug_logger
            debug_logger.error(f"Error en fill_viaje_form - Paso: {paso_actual}")
            debug_logger.error(f"Excepción: {str(e)}")
            debug_logger.error(f"Traceback: {traceback.format_exc()}")

            # Capturar screenshot del error
            try:
                prefactura = self.datos_viaje.get('prefactura', 'UNKNOWN')
                screenshot_mgr.capturar_con_html(
                    self.driver,
                    prefactura=prefactura,
                    modulo="gm_transport_general",
                    detalle_error=f"{paso_actual}: {str(e)[:50]}"
                )
            except:
                pass  # Si falla la captura, no detener el proceso

            return False

def fill_viaje_form(driver):
    """Función de compatibilidad con el código anterior"""
    logger.error("ERROR: Esta función ya no debe usarse directamente")
    return False

def procesar_viaje_completo(driver):
    """Función principal para procesar un viaje completo"""
    logger.error("ERROR: Esta función ya no debe usarse directamente")
    return False

if __name__ == "__main__":
    logger.error("Este módulo no debe ejecutarse directamente")