from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from datetime import datetime, timedelta
import time
import csv
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GMSalidaAutomation:
    def __init__(self, driver, datos_viaje=None):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)
        self.datos_viaje = datos_viaje or {}
        
    def obtener_sucursal_por_determinante(self, clave_determinante):
        """Obtiene la sucursal correspondiente a la clave determinante"""
        csv_path = 'modules/clave_ruta_base.csv'
        
        # Mapeo de base_origen a valores del select (solo las que usamos)
        mapeo_sucursales = {
            'HERMOSILLO': '6',    # BASE HERMOSILLO
            'OBREGON': '7'        # BASE OBREGON
        }
        
        try:
            if os.path.exists(csv_path):
                with open(csv_path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if row['determinante'] == str(clave_determinante):
                            base_origen = row['base_origen'].upper()
                            valor_select = mapeo_sucursales.get(base_origen, '1')  # Default: TODAS
                            logger.info(f"✅ Determinante {clave_determinante} -> Base: {base_origen} -> Valor: {valor_select}")
                            return valor_select
            else:
                logger.warning(f"⚠️ No se encontró archivo: {csv_path}")
                
        except Exception as e:
            logger.error(f"❌ Error al obtener sucursal: {e}")
            
        return '1'  # Default: TODAS
    
    def calcular_fecha_anterior(self, fecha_str):
        """Calcula el día anterior a la fecha dada"""
        try:
            fecha_obj = datetime.strptime(fecha_str, '%d/%m/%Y')
            fecha_anterior = fecha_obj - timedelta(days=1)
            return fecha_anterior.strftime('%d/%m/%Y')
        except Exception as e:
            logger.error(f"❌ Error al calcular fecha anterior: {e}")
            return fecha_str
    
    def configurar_filtros_busqueda(self):
        """Configura los filtros de búsqueda (solo si es sesión nueva)"""
        try:
            # Abrir configuración de Búsqueda General
            busqueda_link = self.wait.until(EC.element_to_be_clickable((By.ID, "LINK_BUSQUEDAGENERAL")))
            busqueda_link.click()
            time.sleep(1)
            logger.info("✅ Configuración de Búsqueda General abierta")
            
            # Desmarcar checkboxes 1 y 2
            for checkbox_id in ["_1_TABLE_BUSQUEDAGENERAL_1", "_2_TABLE_BUSQUEDAGENERAL_1"]:
                try:
                    checkbox = self.driver.find_element(By.ID, checkbox_id)
                    if checkbox.is_selected():
                        checkbox.click()
                        logger.info(f"✅ Checkbox {checkbox_id} desmarcado")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo desmarcar {checkbox_id}: {e}")
            
            # Marcar checkboxes 5, 7 y 8 con manejo especial
            checkboxes_a_marcar = ["_5_TABLE_BUSQUEDAGENERAL_1", "_7_TABLE_BUSQUEDAGENERAL_1", "_8_TABLE_BUSQUEDAGENERAL_1"]
            
            for checkbox_id in checkboxes_a_marcar:
                try:
                    # Esperar a que el checkbox esté presente y sea clickeable
                    checkbox = self.wait.until(EC.element_to_be_clickable((By.ID, checkbox_id)))
                    
                    # Hacer scroll al elemento para asegurarse de que esté visible
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", checkbox)
                    time.sleep(0.3)
                    
                    # Verificar si ya está seleccionado
                    if not checkbox.is_selected():
                        # Intentar clic normal primero
                        try:
                            checkbox.click()
                            time.sleep(0.2)
                        except Exception:
                            # Si falla, usar JavaScript click
                            self.driver.execute_script("arguments[0].click();", checkbox)
                            time.sleep(0.2)
                        
                        # Verificar que realmente se marcó
                        if checkbox.is_selected():
                            logger.info(f"✅ Checkbox {checkbox_id} marcado correctamente")
                        else:
                            logger.warning(f"⚠️ Checkbox {checkbox_id} no se pudo marcar")
                    else:
                        logger.info(f"✅ Checkbox {checkbox_id} ya estaba marcado")
                        
                except Exception as e:
                    logger.error(f"❌ Error al marcar {checkbox_id}: {e}")
            
            # Hacer clic en "Seleccionar" para aplicar la configuración de filtros
            try:
                seleccionar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_SELECCIONARBUSQUEDAGENERAL")))
                seleccionar_btn.click()
                time.sleep(1)
                logger.info("✅ Botón 'Seleccionar' clickeado - Filtros configurados")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Seleccionar': {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al configurar filtros de búsqueda: {e}")
            return False
    
    def ajustar_fecha_desde(self, fecha_viaje):
        """Ajusta la fecha 'desde' al día anterior del viaje"""
        try:
            fecha_desde = self.calcular_fecha_anterior(fecha_viaje)
            
            campo_fecha = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_DESDE")))
            campo_fecha.click()
            time.sleep(0.3)
            
            # Limpiar campo
            campo_fecha.send_keys(Keys.CONTROL + "a")
            campo_fecha.send_keys(Keys.DELETE)
            
            # Insertar nueva fecha
            campo_fecha.send_keys(fecha_desde)
            campo_fecha.send_keys(Keys.ENTER)
            time.sleep(0.2)
            
            logger.info(f"✅ Fecha 'desde' ajustada a: {fecha_desde}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al ajustar fecha desde: {e}")
            return False
    
    def seleccionar_sucursal(self, clave_determinante):
        """Selecciona la sucursal correcta basada en la clave determinante"""
        try:
            valor_sucursal = self.obtener_sucursal_por_determinante(clave_determinante)
            
            select_sucursal = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATSUCURSALES"))))
            select_sucursal.select_by_value(valor_sucursal)
            time.sleep(0.5)
            
            # Obtener texto de la opción seleccionada
            opcion_seleccionada = select_sucursal.first_selected_option.text
            logger.info(f"✅ Sucursal seleccionada: {opcion_seleccionada}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al seleccionar sucursal: {e}")
            return False
    
    def buscar_viaje(self, prefactura):
        """Busca el viaje por prefactura"""
        try:
            # Llenar campo de búsqueda con prefactura
            campo_busqueda = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_BUSCARVIAJES")))
            campo_busqueda.click()
            campo_busqueda.clear()
            campo_busqueda.send_keys(str(prefactura))
            logger.info(f"✅ Prefactura '{prefactura}' ingresada en búsqueda")
            
            # Hacer clic en Aplicar
            try:
                aplicar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_APLICAR")))
                aplicar_btn.click()
                time.sleep(2)  # Esperar a que se filtren los resultados
                logger.info("✅ Filtros aplicados")
                    
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en Aplicar: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al buscar viaje: {e}")
            return False
    
    def seleccionar_viaje_de_tabla(self):
        """Selecciona el viaje de la tabla de resultados"""
        try:
            # Buscar el primer viaje en la tabla
            # El selector puede necesitar ajustes según la estructura real de la tabla
            
            # Método 1: Buscar por patrón de ID de tabla
            try:
                viaje_elemento = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[starts-with(@id, 'TABLE_PROVIAJES_')]")))
                viaje_elemento.click()
                time.sleep(2)  # Esperar a que el sistema detecte la selección
                logger.info("✅ Viaje seleccionado de la tabla")
                return True
            except:
                pass
            
            # Método 2: Buscar por estructura de tabla
            try:
                viaje_elemento = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//table//tr[position()>1]//td[1]")))
                viaje_elemento.click()
                time.sleep(2)
                logger.info("✅ Viaje seleccionado de la tabla (método 2)")
                return True
            except:
                pass
            
            logger.error("❌ No se pudo seleccionar el viaje de la tabla")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al seleccionar viaje de tabla: {e}")
            return False
    
    def autorizar_viaje(self):
        """Hace clic en el botón 'Autorizar'"""
        try:
            autorizar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_AUTORIZAR")))
            autorizar_btn.click()
            time.sleep(2)  # Esperar procesamiento
            logger.info("✅ Viaje autorizado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al autorizar viaje: {e}")
            return False
    
    def facturar_viaje(self):
        """Hace clic en el botón 'Facturar'"""
        try:
            facturar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_FACTURAR")))
            facturar_btn.click()
            time.sleep(2)  # Esperar procesamiento
            logger.info("✅ Viaje facturado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al facturar viaje: {e}")
            return False
    
    def procesar_autorizacion_facturacion(self, configurar_filtros=True):
        """Proceso principal para autorizar y facturar el viaje"""
        try:
            logger.info("🚀 Iniciando proceso de autorización y facturación del viaje")
            
            # Extraer datos necesarios
            fecha_viaje = self.datos_viaje.get('fecha', '')
            prefactura = self.datos_viaje.get('prefactura', '')
            clave_determinante = self.datos_viaje.get('clave_determinante', '')
            
            if not all([fecha_viaje, prefactura, clave_determinante]):
                logger.error("❌ Faltan datos necesarios para procesar autorización y facturación")
                return False
            
            logger.info(f"📋 Procesando: Prefactura={prefactura}, Fecha={fecha_viaje}, Determinante={clave_determinante}")
            
            # Configurar filtros si es necesario
            if configurar_filtros:
                if not self.configurar_filtros_busqueda():
                    logger.warning("⚠️ No se pudieron configurar los filtros de búsqueda")
            
            # Ajustar fecha desde
            if not self.ajustar_fecha_desde(fecha_viaje):
                return False
            
            # Seleccionar sucursal
            if not self.seleccionar_sucursal(clave_determinante):
                return False
            
            # Buscar viaje
            if not self.buscar_viaje(prefactura):
                return False
            
            # Seleccionar viaje de la tabla
            if not self.seleccionar_viaje_de_tabla():
                return False
            
            # NUEVO PROCESO SIMPLIFICADO: Solo Autorizar y Facturar
            logger.info("📋 Proceso simplificado: Autorizar → Facturar")
            
            # Paso 1: Autorizar viaje
            if not self.autorizar_viaje():
                return False
            
            # Paso 2: Facturar viaje
            if not self.facturar_viaje():
                return False
            
            logger.info("✅ Proceso de autorización y facturación completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error general en procesar_autorizacion_facturacion: {e}")
            return False

# Función principal para ser llamada desde otros módulos
def procesar_salida_viaje(driver, datos_viaje=None, configurar_filtros=True):
    """Función principal para autorizar y facturar el viaje (renombrada para compatibilidad)"""
    try:
        automation = GMSalidaAutomation(driver, datos_viaje)
        return automation.procesar_autorizacion_facturacion(configurar_filtros)
    except Exception as e:
        logger.error(f"❌ Error en procesar_salida_viaje: {e}")
        return False

# Función nueva con nombre más claro
def procesar_autorizacion_facturacion(driver, datos_viaje=None, configurar_filtros=True):
    """Función principal para autorizar y facturar el viaje"""
    try:
        automation = GMSalidaAutomation(driver, datos_viaje)
        return automation.procesar_autorizacion_facturacion(configurar_filtros)
    except Exception as e:
        logger.error(f"❌ Error en procesar_autorizacion_facturacion: {e}")
        return False

# Ejemplo de uso
if __name__ == "__main__":
    # Este bloque se ejecutaría solo si ejecutas este archivo directamente
    # Aquí puedes agregar código de prueba
    pass