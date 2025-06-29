from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
import os
import logging
from gm_facturacion1 import ir_a_facturacion
from parser import parse_xls

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
            'fecha': '21/06/2025',
            'prefactura': '7651236',
            'cliente_codigo': '040512',
            'importe': '126.35',
            'clave_determinante': '2380',
            'placa_remolque': '41UG1N',  # Placa de remolque real
            'placa_tractor': '73BB1F'    # Placa de tractor real
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
    
    def obtener_ruta_y_base(self, determinante):
        """Obtiene la ruta GM y base origen desde el CSV"""
        csv_path = 'modules/clave_ruta_base.csv'
        
        try:
            if not os.path.exists(csv_path):
                logger.error(f"❌ No existe el archivo: {csv_path}")
                return None, None
                
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['determinante'] == determinante:
                        return row['ruta_gm'], row['base_origen']
                        
        except Exception as e:
            logger.error(f"❌ Error al leer CSV: {e}")
            
        return None, None
    
    def llenar_fecha(self, id_input, fecha_valor):
        """Llena un campo de fecha de forma robusta"""
        try:
            campo = self.wait.until(EC.element_to_be_clickable((By.ID, id_input)))
            campo.click()
            time.sleep(0.3)
            campo.click()
            time.sleep(0.2)
            
            # Limpiar campo
            campo.send_keys(Keys.HOME)
            for _ in range(10):
                campo.send_keys(Keys.DELETE)
                
            # Obtener hora actual si existe
            valor_actual = campo.get_attribute("value")
            if valor_actual and " " in valor_actual:
                hora = valor_actual.split(" ")[1]
            else:
                hora = "14:00"
                
            # Insertar nueva fecha
            nuevo_valor = f"{fecha_valor} {hora}"
            campo.send_keys(nuevo_valor)
            time.sleep(0.2)
            campo.send_keys(Keys.ENTER)
            time.sleep(0.2)
            
            logger.info(f"✅ Fecha '{nuevo_valor}' insertada en {id_input}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al llenar fecha en {id_input}: {e}")
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
            time.sleep(2)  # Esperar que cargue la búsqueda
            logger.info(f"✅ Búsqueda aplicada para {tipo_placa}")
            
            # Hacer clic en "Seleccionar"
            btn_seleccionar = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_SELECCIONAR")))
            btn_seleccionar.click()
            time.sleep(1)
            logger.info(f"✅ {tipo_placa.capitalize()} {placa_valor} seleccionado")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al buscar {tipo_placa} {placa_valor}: {e}")
            return False
    
    def seleccionar_remolque(self):
        """Selecciona el remolque usando la placa"""
        placa_remolque = self.datos_viaje.get('placa_remolque')
        if not placa_remolque:
            logger.error("❌ No se encontró placa_remolque en los datos")
            return False
            
        return self.buscar_y_seleccionar_placa('remolque', placa_remolque)
    
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
            if not self.buscar_y_seleccionar_placa('tractor', placa_tractor):
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
            
            # Llenar fechas
            fechas_ids = [
                "EDT_FECHA",         # Fecha 1 - Embarque
                "EDT_FECHAESTATUS",  # Fecha 2 - Estatus
                "EDT_FECHACARGA",    # Fecha 3 - Carga
                "EDT_FECHAENTREGA"   # Fecha 4 - Entrega
            ]
            
            for fecha_id in fechas_ids:
                self.llenar_fecha(fecha_id, fecha_valor)
            
            # Obtener y configurar ruta GM
            ruta_gm, base_origen = self.obtener_ruta_y_base(clave_determinante)
            
            if ruta_gm:
                self.llenar_campo_texto("EDT_FOLIORUTA", ruta_gm, "Ruta GM")
                # Disparar evento change
                script = """
                    var input = document.getElementById('EDT_FOLIORUTA');
                    var event = new Event('change', { bubbles: true });
                    input.dispatchEvent(event);
                """
                self.driver.execute_script(script)
            else:
                logger.error(f"❌ No se encontró ruta para determinante {clave_determinante}")
            
            # Seleccionar base origen
            self.seleccionar_base_origen(base_origen)
            
            # NUEVO: Seleccionar remolque
            logger.info("🚛 Seleccionando remolque...")
            if not self.seleccionar_remolque():
                logger.error("❌ Error al seleccionar remolque")
                return False
            
            # NUEVO: Seleccionar tractor y asignar operador automáticamente  
            logger.info("🚗 Seleccionando tractor y asignando operador...")
            if not self.seleccionar_tractor_y_operador():
                logger.error("❌ Error al seleccionar tractor y operador")
                return False
            
            # Proceder a facturación
            logger.info("🎯 Procediendo a facturación...")
            ir_a_facturacion(self.driver, total_factura_valor, self.datos_viaje)
            
            logger.info("✅ Proceso completado exitosamente")
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