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
        
        # TODO: Aquí se integrará MySQL y notificaciones web
        # Por ahora, guardar en archivo temporal
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
    
    def obtener_ruta_y_base(self, determinante):
        """Obtiene la ruta GM y base origen desde el CSV"""
        csv_path = 'modules/clave_ruta_base.csv'
        
        logger.info(f"🔍 Buscando ruta para determinante: {determinante}")
        logger.info(f"📁 Archivo CSV: {csv_path}")
        
        try:
            if not os.path.exists(csv_path):
                logger.error(f"❌ No existe el archivo: {csv_path}")
                logger.error(f"📂 Directorio actual: {os.getcwd()}")
                logger.error(f"📂 Archivos en modules/: {os.listdir('modules/') if os.path.exists('modules/') else 'modules/ no existe'}")
                return None, None
                
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                logger.info(f"📋 Columnas en CSV: {reader.fieldnames}")
                
                for i, row in enumerate(reader):
                    logger.info(f"📄 Fila {i}: {row}")
                    if row['determinante'] == str(determinante):
                        logger.info(f"✅ ENCONTRADO: determinante {determinante} -> ruta {row['ruta_gm']}, base {row['base_origen']}")
                        return row['ruta_gm'], row['base_origen']
                        
                logger.warning(f"⚠️ No se encontró determinante {determinante} en el CSV")
                        
        except Exception as e:
            logger.error(f"❌ Error al leer CSV: {e}")
            
        return None, None
    
    def llenar_fecha(self, id_input, fecha_valor):
        """Llena un campo de fecha de forma robusta"""
        try:
            logger.info(f"🎯 Intentando llenar {id_input} con fecha {fecha_valor}")
            
            # NUEVO: Verificar si el elemento existe antes de intentar hacer clic
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
                # Para tractor, usar el ID específico del botón
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
        """Selecciona el tractor, lo que automáticamente asigna el operador"""
        placa_tractor = self.datos_viaje.get('placa_tractor')
        if not placa_tractor:
            logger.error("❌ No se encontró placa_tractor en los datos")
            return False
            
        try:
            # Abrir modal de asignación de operador/camión
            asignar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ASIGNARCAMION")))
            asignar_btn.click()
            time.sleep(1.5)
            logger.info("✅ Modal de asignación operador/camión abierto")
            
            # Buscar y seleccionar tractor
            exito, error = self.buscar_y_seleccionar_placa('tractor', placa_tractor)
            if not exito:
                return False
            
            # Llenar fechas dentro del modal
            fecha_valor = self.datos_viaje['fecha']
            self.llenar_fecha("EDT_FECHACARGATRAYECTO", fecha_valor)
            self.llenar_fecha("EDT_FECHAESTIMADACARGA", fecha_valor)
            
            # Aceptar para cerrar modal
            aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTARTRAYECTO")))
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", aceptar_btn)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", aceptar_btn)
            logger.info("✅ Tractor seleccionado y operador asignado automáticamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al seleccionar tractor y operador: {e}")
            return False
    
    def fill_viaje_form(self):
        """Función principal para llenar el formulario de viaje"""
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
            
            # NUEVO: Después de llenar fechas, hacer clic en el campo de ruta para continuar
            logger.info("🎯 Moviendo foco al campo de ruta...")
            try:
                campo_ruta = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_FOLIORUTA")))
                campo_ruta.click()
                time.sleep(0.5)
                logger.info("✅ Enfoque movido al campo de ruta")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo hacer clic en campo de ruta: {e}")
            
            # Obtener y configurar ruta GM
            logger.info("🗺️ Obteniendo ruta GM...")
            ruta_gm, base_origen = self.obtener_ruta_y_base(clave_determinante)
            
            if ruta_gm and base_origen:
                logger.info(f"✅ Ruta encontrada: {ruta_gm}, Base: {base_origen}")
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
            else:
                # NUEVO: Registrar error y continuar
                error_msg = f"DETERMINANTE_NO_ENCONTRADO"
                detalle = f"Determinante {clave_determinante} no existe en clave_ruta_base.csv"
                self.registrar_error_viaje(error_msg, detalle)
                
                logger.warning("⚠️ Determinante no encontrado - continuando sin ruta y base")
                logger.warning("📝 Se requerirá configuración manual de ruta y base en GM Transport")
                
                # Continuar sin poner ruta ni base - GM Transport lo requerirá manualmente
            
            # Seleccionar remolque con manejo de errores
            logger.info("🚛 Seleccionando remolque...")
            exito_remolque, error_remolque = self.seleccionar_remolque()
            if not exito_remolque:
                self.registrar_error_viaje(error_remolque, f"No se pudo seleccionar remolque {self.datos_viaje.get('placa_remolque')}")
                logger.error("❌ Error al seleccionar remolque - Viaje marcado para revisión manual")
                return False
            
            # Seleccionar tractor y asignar operador automáticamente  
            logger.info("🚗 Seleccionando tractor y asignando operador...")
            if not self.seleccionar_tractor_y_operador():
                self.registrar_error_viaje("OPERADOR_NO_ASIGNADO", f"Tractor {self.datos_viaje.get('placa_tractor')} sin operador automático")
                logger.warning("⚠️ No se pudo asignar operador automáticamente")
                logger.info("📝 Continuando sin operador - se requerirá asignación manual")
                # No retornar False, continuar con el proceso
            
            # **NUEVO FLUJO**: Usar gm_facturacion1 para la parte inicial
            logger.info("💰 Ejecutando facturación inicial...")
            try:
                resultado_facturacion = ir_a_facturacion(self.driver, total_factura_valor, self.datos_viaje)
                if resultado_facturacion:
                    logger.info("✅ Facturación inicial completada")
                else:
                    logger.warning("⚠️ Problema en facturación inicial - continuando...")
            except Exception as e:
                logger.warning(f"⚠️ Error en facturación inicial: {e} - continuando...")
            
            # **NUEVO FLUJO**: Procesar Salida
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
            
            # **NUEVO FLUJO**: Procesar Llegada y Facturación Final
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