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

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GMTransportAutomation:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)
        self.datos_viaje = self.cargar_datos_viaje()
        
    def cargar_datos_viaje(self):
        """Carga los datos del viaje desde el archivo XLS o usa datos por defecto"""
        # Datos por defecto (incluyendo placas para pruebas)
        datos_default = {
            'fecha': '01/07/2025',
            'prefactura': '7996845',  
            'cliente_codigo': '040512',
            'importe': '310.75',  
            'clave_determinante': '2899',
            'placa_remolque': '852YH6',
            'placa_tractor': '94BB1F'
        }
        
        archivo_prueba = "tests/ejemplo.xls"
        
        try:
            if os.path.exists(archivo_prueba):
                logger.info(f"📄 Leyendo archivo: {archivo_prueba}")
                parsed = parse_xls(archivo_prueba, determinante_from_asunto="8121")
                
                if isinstance(parsed, dict):
                    if "error" not in parsed:
                        datos_default.update(parsed)
                        logger.info("✅ Datos cargados exitosamente desde archivo")
                    else:
                        logger.warning(f"⚠️ Error al parsear archivo: {parsed['error']}")
                else:
                    logger.warning("⚠️ Formato inesperado desde parser")
            else:
                logger.warning(f"⚠️ No se encontró archivo: {archivo_prueba}")
                
        except Exception as e:
            logger.error(f"❌ Error al cargar datos: {e}")
            
        return datos_default
    
    def registrar_error_viaje(self, tipo_error, detalle=""):
        """Registra errores específicos del viaje para revisión manual"""
        prefactura = self.datos_viaje.get('prefactura', 'DESCONOCIDA')
        placa_tractor = self.datos_viaje.get('placa_tractor', 'DESCONOCIDA')
        placa_remolque = self.datos_viaje.get('placa_remolque', 'DESCONOCIDA')
        determinante = self.datos_viaje.get('clave_determinante', 'DESCONOCIDO')
        
        # Log específico para operadores
        logger.error("=" * 80)
        logger.error("🚨 VIAJE REQUIERE ATENCIÓN MANUAL")
        logger.error(f"📋 PREFACTURA: {prefactura}")
        logger.error(f"🚛 PLACA TRACTOR: {placa_tractor}")
        logger.error(f"🚚 PLACA REMOLQUE: {placa_remolque}")
        logger.error(f"🎯 DETERMINANTE: {determinante}")
        logger.error(f"❌ ERROR: {tipo_error}")
        if detalle:
            logger.error(f"📝 DETALLE: {detalle}")
        logger.error("🔧 ACCIÓN REQUERIDA: Revisar y completar manualmente en GM Transport")
        logger.error("=" * 80)
        
        # Guardar en archivo temporal
        try:
            error_file = "errores_viajes.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(error_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp}|{prefactura}|{placa_tractor}|{placa_remolque}|{determinante}|{tipo_error}|{detalle}\n")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo guardar error en archivo: {e}")
            
        return {
            'timestamp': datetime.now().isoformat(),
            'prefactura': prefactura,
            'placa_tractor': placa_tractor,
            'placa_remolque': placa_remolque,
            'determinante': determinante,
            'tipo_error': tipo_error,
            'detalle': detalle
        }
    
    def registrar_determinante_faltante_mysql(self, determinante_faltante):
        """
        NUEVA FUNCIÓN: Registra específicamente determinantes faltantes en MySQL
        """
        try:
            from .mysql_simple import registrar_viaje_fallido
            
            prefactura = self.datos_viaje.get('prefactura', 'DESCONOCIDA')
            fecha_viaje = self.datos_viaje.get('fecha', '')
            placa_tractor = self.datos_viaje.get('placa_tractor', '')
            placa_remolque = self.datos_viaje.get('placa_remolque', '')
            
            # Motivo específico para determinantes faltantes
            motivo_fallo = f"Determinante {determinante_faltante} no encontrada en clave_ruta_base.csv"
            
            # Registrar en MySQL
            exito_mysql = registrar_viaje_fallido(
                prefactura=prefactura,
                fecha_viaje=fecha_viaje, 
                motivo_fallo=motivo_fallo,
                placa_tractor=placa_tractor,
                placa_remolque=placa_remolque
            )
            
            if exito_mysql:
                logger.error("🚨 DETERMINANTE FALTANTE REGISTRADA EN MySQL:")
                logger.error(f"   📋 Prefactura: {prefactura}")
                logger.error(f"   🎯 Determinante faltante: {determinante_faltante}")
                logger.error(f"   🚛 Placas: {placa_tractor} / {placa_remolque}")
                logger.error(f"   💾 Estado: Registrado en base de datos")
                logger.error("   🔧 ACCIÓN: Agregar determinante a clave_ruta_base.csv")
                return True
            else:
                logger.warning("⚠️ MySQL no disponible - registrado en archivo fallback")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error registrando determinante faltante en MySQL: {e}")
            return False
    
    def obtener_ruta_y_base(self, determinante):
        """
        FUNCIÓN MODIFICADA: Obtiene la ruta GM y base origen desde el CSV
        Ahora retorna estado específico para determinantes faltantes
        """
        csv_path = 'modules/clave_ruta_base.csv'
        
        logger.info(f"🔍 Buscando ruta para determinante: {determinante}")
        logger.info(f"📁 Archivo CSV: {csv_path}")
        
        try:
            if not os.path.exists(csv_path):
                logger.error(f"❌ No existe el archivo: {csv_path}")
                logger.error(f"📂 Directorio actual: {os.getcwd()}")
                logger.error(f"📂 Archivos en modules/: {os.listdir('modules/') if os.path.exists('modules/') else 'modules/ no existe'}")
                return None, None, "ARCHIVO_CSV_NO_EXISTE"
                
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                logger.info(f"📋 Columnas en CSV: {reader.fieldnames}")
                
                # Lista para logging de determinantes disponibles
                determinantes_disponibles = []
                
                for i, row in enumerate(reader):
                    logger.info(f"📄 Fila {i}: {row}")
                    determinantes_disponibles.append(row['determinante'])
                    
                    if row['determinante'] == str(determinante):
                        logger.info(f"✅ ENCONTRADO: determinante {determinante} -> ruta {row['ruta_gm']}, base {row['base_origen']}")
                        return row['ruta_gm'], row['base_origen'], "ENCONTRADO"
                
                # NUEVO: Si llegamos aquí, la determinante NO existe
                logger.error("🚨 DETERMINANTE NO ENCONTRADA EN LISTA")
                logger.error(f"🎯 Determinante buscada: {determinante}")
                logger.error(f"📋 Determinantes disponibles: {determinantes_disponibles}")
                logger.error("💡 Esta determinante debe agregarse al archivo clave_ruta_base.csv")
                
                return None, None, "DETERMINANTE_NO_ENCONTRADA"
                        
        except Exception as e:
            logger.error(f"❌ Error al leer CSV: {e}")
            return None, None, "ERROR_LECTURA_CSV"
    
    def llenar_fecha(self, id_input, fecha_valor):
        """Llena un campo de fecha de forma robusta"""
        try:
            logger.info(f"🎯 Intentando llenar {id_input} con fecha {fecha_valor}")
            
            # Verificar si el elemento existe antes de intentar hacer clic
            try:
                elemento_existe = self.driver.find_element(By.ID, id_input)
                logger.info(f"✅ Elemento {id_input} encontrado: {elemento_existe.tag_name}")
                logger.info(f"📋 Visible: {elemento_existe.is_displayed()}")
                logger.info(f"📋 Habilitado: {elemento_existe.is_enabled()}")
                logger.info(f"📋 Clase: {elemento_existe.get_attribute('class')}")
            except Exception as e:
                logger.error(f"❌ Elemento {id_input} NO ENCONTRADO: {e}")
                return False
            
            campo = self.wait.until(EC.element_to_be_clickable((By.ID, id_input)))
            
            # Verificar valor actual
            valor_actual = campo.get_attribute("value")
            logger.info(f"📋 Valor actual en {id_input}: '{valor_actual}'")
            
            # SIEMPRE llenar, incluso si ya tiene la fecha correcta
            logger.info(f"🖱️ Haciendo primer clic en {id_input}")
            campo.click()
            time.sleep(0.3)
            logger.info(f"🖱️ Haciendo segundo clic en {id_input}")
            campo.click()
            time.sleep(0.2)
            
            # Limpiar campo
            logger.info(f"🧹 Limpiando campo {id_input}")
            campo.send_keys(Keys.HOME)
            for _ in range(10):
                campo.send_keys(Keys.DELETE)
                
            # Obtener hora actual si existe
            if valor_actual and " " in valor_actual:
                hora = valor_actual.split(" ")[1]
            else:
                hora = "14:00"
                
            # Insertar nueva fecha
            nuevo_valor = f"{fecha_valor} {hora}"
            logger.info(f"⌨️ Escribiendo en {id_input}: '{nuevo_valor}'")
            campo.send_keys(nuevo_valor)
            time.sleep(0.3)
            
            # Verificar que se insertó
            valor_final = campo.get_attribute("value")
            logger.info(f"✅ Fecha insertada en {id_input}: '{valor_final}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al llenar fecha en {id_input}: {e}")
            logger.error(f"🔍 Detalles del error: {type(e).__name__}")
            return False
    
    def llenar_campo_texto(self, id_input, valor, descripcion=""):
        """Llena un campo de texto de forma robusta"""
        try:
            campo = self.wait.until(EC.element_to_be_clickable((By.ID, id_input)))
            campo.click()
            campo.clear()
            campo.send_keys(str(valor))
            logger.info(f"✅ {descripcion} '{valor}' insertado en {id_input}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al llenar {descripcion} en {id_input}: {e}")
            return False
    
    def seleccionar_base_origen(self, base_origen):
        """Selecciona la base origen del combo"""
        if not base_origen:
            logger.error("❌ No se proporcionó base origen")
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
                    logger.info(f"✅ Base origen '{base_origen_texto}' seleccionada")
                    return True
                    
            logger.error(f"❌ No se encontró la opción '{base_origen_texto}'")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al seleccionar base origen: {e}")
            return False
    
    def buscar_y_seleccionar_placa(self, tipo_placa, placa_valor):
        """
        Busca y selecciona una placa (remolque o tractor)
        tipo_placa: 'remolque' o 'tractor'
        Retorna: (éxito: bool, error_mensaje: str)
        """
        try:
            logger.info(f"🔍 Buscando {tipo_placa}: {placa_valor}")
            
            # Hacer clic en los 3 puntitos para abrir buscador
            if tipo_placa == 'remolque':
                btn_buscar = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_BUSCARCODIGOUNIDADCARGA1")))
            else:  # tractor
                btn_buscar = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_BUSCARCODIGOUNIDADCAMION")))
            
            btn_buscar.click()
            time.sleep(1.5)
            logger.info(f"✅ Buscador de {tipo_placa} abierto")
            
            # Desmarcar checkbox "No visualizar Unidades Rentadas"
            try:
                checkbox_filtro = self.wait.until(EC.element_to_be_clickable((By.ID, "CBOX_FILTRARRENTADAS_1")))
                if checkbox_filtro.is_selected():
                    checkbox_filtro.click()
                    time.sleep(0.3)
                    logger.info(f"✅ Filtro de unidades rentadas deshabilitado para {tipo_placa}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo desmarcar filtro para {tipo_placa}: {e}")
            
            # Buscar el campo de búsqueda y pegar la placa
            campo_busqueda = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_BUSQUEDA")))
            campo_busqueda.clear()
            campo_busqueda.send_keys(placa_valor)
            logger.info(f"✅ Placa {placa_valor} ingresada en buscador")
            
            # Hacer clic en "Aplicar"
            btn_aplicar = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@class='btnvalignmiddle' and contains(text(), 'Aplicar')]/..")))
            btn_aplicar.click()
            time.sleep(3)  # Esperar que cargue la búsqueda
            logger.info(f"✅ Búsqueda aplicada para {tipo_placa}")
            
            # Verificar si se encontraron resultados
            try:
                # Buscar si aparece el botón "Seleccionar" (significa que hay resultados)
                btn_seleccionar = self.driver.find_element(By.ID, "BTN_SELECCIONAR")
                if not btn_seleccionar.is_enabled():
                    error_msg = f"PLACA_{tipo_placa.upper()}_NO_ENCONTRADA"
                    logger.error(f"❌ {tipo_placa.capitalize()} {placa_valor} no encontrado en GM Transport")
                    # Cerrar ventana de búsqueda
                    try:
                        cerrar_btn = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Cerrar')]/..")
                        cerrar_btn.click()
                    except:
                        pass
                    return False, error_msg
                
                # Hacer clic en "Seleccionar"
                btn_seleccionar.click()
                time.sleep(1)
                logger.info(f"✅ {tipo_placa.capitalize()} {placa_valor} seleccionado")
                return True, ""
                
            except Exception as e:
                error_msg = f"PLACA_{tipo_placa.upper()}_NO_ENCONTRADA"
                logger.error(f"❌ {tipo_placa.capitalize()} {placa_valor} no encontrado: {e}")
                # Cerrar ventana de búsqueda
                try:
                    cerrar_btn = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Cerrar')]/..")
                    cerrar_btn.click()
                except:
                    pass
                return False, error_msg
            
        except Exception as e:
            error_msg = f"ERROR_BUSQUEDA_{tipo_placa.upper()}"
            logger.error(f"❌ Error al buscar {tipo_placa} {placa_valor}: {e}")
            return False, error_msg
    
    def seleccionar_remolque(self):
        """Selecciona el remolque usando la placa"""
        placa_remolque = self.datos_viaje.get('placa_remolque')
        if not placa_remolque:
            logger.error("❌ No se encontró placa_remolque en los datos")
            return False, "DATOS_INCOMPLETOS_PLACA_REMOLQUE"
            
        exito, error = self.buscar_y_seleccionar_placa('remolque', placa_remolque)
        return exito, error
    
    def seleccionar_tractor_y_operador(self):
        """Selecciona el tractor y VERIFICA que tenga operador asignado"""
        placa_tractor = self.datos_viaje.get('placa_tractor')
        if not placa_tractor:
            logger.error("❌ No se encontró placa_tractor en los datos")
            return False, "DATOS_INCOMPLETOS_PLACA_TRACTOR"
            
        try:
            # Abrir modal de asignación de operador/camión
            asignar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ASIGNARCAMION")))
            asignar_btn.click()
            time.sleep(1.5)
            logger.info("✅ Modal de asignación operador/camión abierto")
            
            # Buscar y seleccionar tractor
            exito, error = self.buscar_y_seleccionar_placa('tractor', placa_tractor)
            if not exito:
                return False, error
            
            # Llenar fechas dentro del modal
            fecha_valor = self.datos_viaje['fecha']
            self.llenar_fecha("EDT_FECHACARGATRAYECTO", fecha_valor)
            self.llenar_fecha("EDT_FECHAESTIMADACARGA", fecha_valor)
            
            # CRÍTICO: Dar tiempo suficiente para que GM asigne operador automáticamente
            logger.info("⏳ Esperando que GM asigne operador automáticamente...")
            time.sleep(5)  # Tiempo generoso para que GM procese la asignación
            
            # Verificar si se asignó operador automáticamente
            operador_asignado = False
            
            try:
                # Método 1: Buscar campo de operador por varios IDs posibles
                posibles_ids_operador = [
                    "EDT_OPERADOR", 
                    "EDT_CHOFER", 
                    "EDT_CONDUCTOR",
                    "EDT_OPERADOR1",
                    "COMBO_OPERADOR",
                    "EDT_NOMBREOPERADOR",
                    "EDT_CODIGOOPERADOR"
                ]
                
                logger.info("🔍 Buscando campos de operador...")
                for id_operador in posibles_ids_operador:
                    try:
                        operador_campo = self.driver.find_element(By.ID, id_operador)
                        valor_operador = operador_campo.get_attribute("value")
                        
                        logger.info(f"📋 Campo {id_operador}: '{valor_operador}'")
                        
                        if valor_operador and valor_operador.strip() and valor_operador != "0" and len(valor_operador.strip()) > 2:
                            logger.info(f"✅ Operador encontrado en {id_operador}: {valor_operador}")
                            operador_asignado = True
                            break
                            
                    except:
                        continue
                
                # Método 2: Buscar por texto que indique operador asignado
                if not operador_asignado:
                    logger.info("🔍 Buscando operador por texto en la página...")
                    try:
                        elementos_operador = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Operador') or contains(text(), 'OPERADOR') or contains(text(), 'Chofer') or contains(text(), 'CHOFER')]")
                        for elem in elementos_operador:
                            try:
                                texto_parent = elem.find_element(By.XPATH, "..").text
                                logger.info(f"📋 Texto operador encontrado: {texto_parent}")
                                
                                # Buscar si hay un nombre después de "Operador:" o similar
                                if ":" in texto_parent:
                                    nombre_operador = texto_parent.split(":")[-1].strip()
                                    if len(nombre_operador) > 3 and not nombre_operador.isdigit():
                                        logger.info(f"✅ Operador detectado por texto: {nombre_operador}")
                                        operador_asignado = True
                                        break
                            except:
                                continue
                    except:
                        pass
                
                # Método 3: Verificar elementos visibles con nombres
                if not operador_asignado:
                    logger.info("🔍 Buscando nombres de operador visibles...")
                    try:
                        # Buscar todos los inputs con valores que podrían ser nombres
                        todos_inputs = self.driver.find_elements(By.XPATH, "//input[@type='text']")
                        for input_elem in todos_inputs:
                            try:
                                valor = input_elem.get_attribute("value")
                                if valor and len(valor) > 5 and " " in valor and not valor.isdigit():
                                    # Puede ser un nombre (tiene espacios, más de 5 chars, no es número)
                                    logger.info(f"✅ Posible operador encontrado: {valor}")
                                    operador_asignado = True
                                    break
                            except:
                                continue
                    except:
                        pass
                        
            except Exception as e:
                logger.warning(f"⚠️ Error verificando operador: {e}")
                
            # DECISIÓN CRÍTICA basada en si tiene operador
            if not operador_asignado:
                logger.error("❌ PLACA SIN OPERADOR ASIGNADO")
                logger.error(f"🚛 Placa: {placa_tractor} no tiene operador disponible")
                logger.error("🚨 Cerrando modal y registrando error")
                
                # Cerrar el modal sin aceptar
                try:
                    # Buscar botón Cancelar/Cerrar
                    posibles_botones_cerrar = ["BTN_CANCELAR", "BTN_CERRAR", "BTN_CANCELARTRAYECTO"]
                    for btn_id in posibles_botones_cerrar:
                        try:
                            cancelar_btn = self.driver.find_element(By.ID, btn_id)
                            self.driver.execute_script("arguments[0].click();", cancelar_btn)
                            time.sleep(1)
                            logger.info(f"✅ Modal cerrado con {btn_id}")
                            break
                        except:
                            continue
                    else:
                        # Si no hay botón cancelar, intentar Escape
                        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                        logger.info("✅ Modal cerrado con Escape")
                except Exception as e:
                    logger.warning(f"⚠️ Error cerrando modal: {e}")
                
                return False, "PLACA_SIN_OPERADOR_ASIGNADO"
            
            # Si llegamos aquí, SÍ tiene operador asignado
            logger.info("✅ Operador asignado correctamente")
            
            # Aceptar para cerrar modal
            try:
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTARTRAYECTO")))
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", aceptar_btn)
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", aceptar_btn)
                logger.info("✅ Tractor y operador asignados exitosamente")
                return True, ""
                
            except Exception as e:
                logger.error(f"❌ Error al aceptar modal: {e}")
                return False, "ERROR_ACEPTAR_MODAL"
                
        except Exception as e:
            logger.error(f"❌ Error al seleccionar tractor: {e}")
            return False, "ERROR_SELECCION_TRACTOR"
    
    def fill_viaje_form(self):
        """
        FUNCIÓN PRINCIPAL MODIFICADA: Maneja determinantes faltantes
        """
        try:
            logger.info("🚀 Iniciando llenado de formulario de viaje")
            
            # Navegar al módulo de creación de viajes automáticamente
            from .navigate_to_create_viaje import navigate_to_create_viaje
            logger.info("🧭 Navegando al módulo de creación de viajes...")
            if not navigate_to_create_viaje(self.driver):
                logger.error("❌ Error al navegar al módulo de viajes")
                return False
            
            # Extraer datos
            fecha_valor = self.datos_viaje['fecha']
            prefactura_valor = self.datos_viaje['prefactura']
            cliente_codigo = self.datos_viaje['cliente_codigo']
            total_factura_valor = str(self.datos_viaje['importe'])
            clave_determinante = self.datos_viaje['clave_determinante']
            
            logger.info(f"📋 Datos a procesar: {self.datos_viaje}")
            
            # Llenar campos básicos
            self.llenar_campo_texto("EDT_NOVIAJECLIENTE", prefactura_valor, "Prefactura")
            self.llenar_campo_texto("EDT_NUMEROCLIENTE", cliente_codigo, "Cliente")
            
            # Llenar fechas - método simplificado
            fechas_con_hora = [
                "EDT_FECHA",         # Fecha 1 - Embarque
                "EDT_FECHAESTATUS",  # Fecha 2 - Estatus
                "EDT_FECHACARGA",    # Fecha 3 - Carga
            ]
            
            # Llenar primeras 3 fechas que SÍ llevan hora
            logger.info(f"📅 Llenando fechas 1-3 con hora...")
            for i, fecha_id in enumerate(fechas_con_hora, 1):
                logger.info(f"📅 Fecha {i}/3: {fecha_id}")
                self.llenar_fecha(fecha_id, fecha_valor)
            
            # Llenar cuarta fecha que NO lleva hora
            logger.info("📅 Llenando fecha 4/4: EDT_FECHAENTREGA SIN hora")
            try:
                self.driver.execute_script("""
                    var campo = document.getElementById('EDT_FECHAENTREGA');
                    if (campo) {
                        campo.value = arguments[0];
                        campo.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                """, fecha_valor)  # Solo fecha, sin hora
                logger.info(f"✅ Fecha 4 completada: {fecha_valor} (sin hora)")
            except Exception as e:
                logger.error(f"❌ Error en fecha 4: {e}")
            
            # Pausa antes de continuar
            time.sleep(1)
            
            # Hacer clic en el campo de ruta para continuar
            logger.info("🎯 Moviendo foco al campo de ruta...")
            try:
                campo_ruta = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_FOLIORUTA")))
                campo_ruta.click()
                time.sleep(0.5)
                logger.info("✅ Enfoque movido al campo de ruta")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo hacer clic en campo de ruta: {e}")
            
            # 🚨 NUEVA LÓGICA: Obtener y validar determinante
            logger.info("🗺️ Obteniendo ruta GM...")
            ruta_gm, base_origen, estado_determinante = self.obtener_ruta_y_base(clave_determinante)
            
            # 🚨 MANEJO CRÍTICO: Determinante no encontrada
            if estado_determinante == "DETERMINANTE_NO_ENCONTRADA":
                logger.error("🚨 DETERMINANTE NO ENCONTRADA - REGISTRANDO ERROR Y TERMINANDO VIAJE")
                
                # Registrar específicamente en MySQL
                if self.registrar_determinante_faltante_mysql(clave_determinante):
                    logger.error("✅ Error registrado exitosamente en MySQL")
                else:
                    logger.error("❌ Error registrado en archivo fallback")
                
                # Registrar también en el sistema de errores local
                self.registrar_error_viaje(
                    "DETERMINANTE_NO_ENCONTRADA", 
                    f"Determinante {clave_determinante} no existe en clave_ruta_base.csv - Debe agregarse manualmente"
                )
                
                logger.error("🔄 RETORNANDO FALSE - El sistema continuará con el siguiente viaje")
                return False  # ← IMPORTANTE: Retorna False para que continúe con siguiente viaje
            
            # 🚨 OTROS ERRORES DE DETERMINANTE
            elif estado_determinante in ["ARCHIVO_CSV_NO_EXISTE", "ERROR_LECTURA_CSV"]:
                logger.error(f"🚨 ERROR CRÍTICO EN DETERMINANTES: {estado_determinante}")
                self.registrar_error_viaje(
                    estado_determinante,
                    f"Error técnico con archivo clave_ruta_base.csv"
                )
                return False  # ← También continúa con siguiente viaje
            
            # ✅ DETERMINANTE ENCONTRADA - CONTINUAR NORMALMENTE
            elif estado_determinante == "ENCONTRADO":
                logger.info(f"✅ Determinante válida: {clave_determinante} -> Ruta: {ruta_gm}, Base: {base_origen}")
                
                # Llenar ruta GM
                self.llenar_campo_texto("EDT_FOLIORUTA", ruta_gm, "Ruta GM")
                
                # Disparar evento change con pausa
                time.sleep(0.5)
                script = """
                    var input = document.getElementById('EDT_FOLIORUTA');
                    if (input) {
                        var event = new Event('change', { bubbles: true });
                        input.dispatchEvent(event);
                    }
                """
                self.driver.execute_script(script)
                time.sleep(1)  # Pausa para que GM procese
                logger.info("✅ Evento change disparado para ruta")
                
                # Seleccionar base origen
                self.seleccionar_base_origen(base_origen)
            
            # Seleccionar remolque con manejo de errores
            logger.info("🚛 Seleccionando remolque...")
            exito_remolque, error_remolque = self.seleccionar_remolque()
            if not exito_remolque:
                self.registrar_error_viaje(error_remolque, f"No se pudo seleccionar remolque {self.datos_viaje.get('placa_remolque')}")
                logger.error("❌ Error al seleccionar remolque - Viaje marcado para revisión manual")
                return False
            
            # Seleccionar tractor y verificar operador automáticamente  
            logger.info("🚗 Seleccionando tractor y verificando operador...")
            exito_tractor, error_tractor = self.seleccionar_tractor_y_operador()
            
            if not exito_tractor:
                if error_tractor == "PLACA_SIN_OPERADOR_ASIGNADO":
                    # Error específico: placa sin operador
                    self.registrar_error_viaje("PLACA_SIN_OPERADOR", f"Tractor {self.datos_viaje.get('placa_tractor')} no tiene operador asignado")
                    logger.error("❌ VIAJE CANCELADO: Placa sin operador - Requiere asignación manual")
                    return False
                else:
                    # Otros errores de tractor
                    self.registrar_error_viaje(error_tractor, f"Error con tractor {self.datos_viaje.get('placa_tractor')}")
                    logger.error("❌ VIAJE CANCELADO: Error en selección de tractor")
                    return False
            
            # **FLUJO**: Usar gm_facturacion1 para la parte inicial
            logger.info("💰 Ejecutando facturación inicial...")
            try:
                resultado_facturacion = ir_a_facturacion(self.driver, total_factura_valor, self.datos_viaje)
                if resultado_facturacion:
                    logger.info("✅ Facturación inicial completada")
                else:
                    logger.warning("⚠️ Problema en facturación inicial - continuando...")
            except Exception as e:
                logger.warning(f"⚠️ Error en facturación inicial: {e} - continuando...")
            
            # **FLUJO**: Procesar Salida
            logger.info("🚛 Ejecutando proceso de SALIDA...")
            try:
                resultado_salida = procesar_salida_viaje(self.driver, self.datos_viaje, configurar_filtros=True)
                if not resultado_salida:
                    logger.error("❌ Error en proceso de salida - Este viaje necesita revisión manual")
                    logger.error(f"🔍 VIAJE PARA REVISIÓN: Prefactura {prefactura_valor} - Error en salida")
                    return False
            except Exception as e:
                logger.error(f"❌ Error crítico en salida: {e}")
                logger.error(f"🔍 VIAJE PARA REVISIÓN: Prefactura {prefactura_valor} - Error crítico en salida")
                return False
            
            # **FLUJO**: Procesar Llegada y Facturación Final
            logger.info("🛬 Ejecutando proceso de LLEGADA y FACTURACIÓN FINAL...")
            try:
                resultado_llegada = procesar_llegada_factura(self.driver, self.datos_viaje)
                if not resultado_llegada:
                    logger.error("❌ Error en proceso de llegada y facturación - Este viaje necesita revisión manual")
                    logger.error(f"🔍 VIAJE PARA REVISIÓN: Prefactura {prefactura_valor} - Error en llegada/facturación")
                    return False
            except Exception as e:
                logger.error(f"❌ Error crítico en llegada: {e}")
                logger.error(f"🔍 VIAJE PARA REVISIÓN: Prefactura {prefactura_valor} - Error crítico en llegada")
                return False
            
            logger.info("🎉 Proceso completo de automatización GM Transport exitoso")
            logger.info(f"✅ VIAJE COMPLETADO: Prefactura {prefactura_valor} - Placa Tractor: {self.datos_viaje.get('placa_tractor')} - Placa Remolque: {self.datos_viaje.get('placa_remolque')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error general en fill_viaje_form: {e}")
            return False

# Función legacy para compatibilidad
def fill_viaje_form(driver):
    """Función de compatibilidad con el código anterior"""
    automation = GMTransportAutomation(driver)
    return automation.fill_viaje_form()

# Función principal para ser llamada desde otros módulos
def procesar_viaje_completo(driver):
    """Función principal para procesar un viaje completo"""
    automation = GMTransportAutomation(driver)
    return automation.fill_viaje_form()

# Ejemplo de uso
if __name__ == "__main__":
    # Este bloque se ejecutaría solo si ejecutas este archivo directamente
    # Aquí puedes agregar código de prueba
    pass