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
        self.wait = WebDriverWait(driver, 20)  # Aumenté timeout para computadoras más lentas
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
    
    def manejar_checkbox_robusto(self, checkbox_id, marcar=True):
        """Maneja un checkbox de forma súper robusta contra errores stale element"""
        logger.info(f"🎯 Procesando checkbox {checkbox_id}...")
        
        max_intentos = 5
        for intento in range(max_intentos):
            try:
                # SIEMPRE buscar el elemento de nuevo para evitar stale element
                checkbox = self.wait.until(EC.presence_of_element_located((By.ID, checkbox_id)))
                
                # Verificar si está visible y habilitado
                if not checkbox.is_displayed():
                    logger.warning(f"⚠️ Checkbox {checkbox_id} no visible en intento {intento + 1}")
                    time.sleep(1)
                    continue
                
                # Hacer scroll para asegurar visibilidad
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", checkbox)
                time.sleep(0.5)
                
                # Verificar estado actual
                esta_marcado = checkbox.is_selected()
                
                if marcar and not esta_marcado:
                    # Necesita marcarse
                    try:
                        # Método 1: Clic normal
                        checkbox.click()
                        time.sleep(0.3)
                        
                        # Verificar si funcionó
                        checkbox_verificacion = self.driver.find_element(By.ID, checkbox_id)
                        if checkbox_verificacion.is_selected():
                            logger.info(f"✅ Checkbox {checkbox_id} marcado exitosamente (método 1)")
                            return True
                        else:
                            # Método 2: JavaScript click
                            self.driver.execute_script("arguments[0].click();", checkbox)
                            time.sleep(0.3)
                            
                            # Verificar otra vez
                            checkbox_verificacion = self.driver.find_element(By.ID, checkbox_id)
                            if checkbox_verificacion.is_selected():
                                logger.info(f"✅ Checkbox {checkbox_id} marcado exitosamente (método 2)")
                                return True
                            else:
                                # Método 3: Forzar con JavaScript
                                script = f"""
                                    var checkbox = document.getElementById('{checkbox_id}');
                                    if (checkbox && !checkbox.checked) {{
                                        checkbox.checked = true;
                                        var event = new Event('change', {{ bubbles: true }});
                                        checkbox.dispatchEvent(event);
                                    }}
                                """
                                self.driver.execute_script(script)
                                time.sleep(0.3)
                                
                                # Verificación final
                                checkbox_verificacion = self.driver.find_element(By.ID, checkbox_id)
                                if checkbox_verificacion.is_selected():
                                    logger.info(f"✅ Checkbox {checkbox_id} marcado exitosamente (método 3)")
                                    return True
                    except Exception as e:
                        logger.warning(f"⚠️ Error en intento {intento + 1} para {checkbox_id}: {e}")
                        time.sleep(1)
                        continue
                        
                elif not marcar and esta_marcado:
                    # Necesita desmarcarse
                    try:
                        checkbox.click()
                        time.sleep(0.3)
                        
                        # Verificar
                        checkbox_verificacion = self.driver.find_element(By.ID, checkbox_id)
                        if not checkbox_verificacion.is_selected():
                            logger.info(f"✅ Checkbox {checkbox_id} desmarcado exitosamente")
                            return True
                    except Exception as e:
                        logger.warning(f"⚠️ Error desmarcando {checkbox_id} en intento {intento + 1}: {e}")
                        time.sleep(1)
                        continue
                else:
                    # Ya está en el estado correcto
                    estado = "marcado" if esta_marcado else "desmarcado"
                    logger.info(f"✅ Checkbox {checkbox_id} ya estaba {estado}")
                    return True
                    
            except Exception as e:
                logger.warning(f"⚠️ Intento {intento + 1} falló para {checkbox_id}: {e}")
                time.sleep(1)
                
        logger.error(f"❌ TODOS los intentos fallaron para {checkbox_id}")
        return False
    
    def configurar_filtros_busqueda(self):
        """Configura los filtros de búsqueda (versión robusta contra stale elements)"""
        try:
            # Abrir configuración de Búsqueda General
            busqueda_link = self.wait.until(EC.element_to_be_clickable((By.ID, "LINK_BUSQUEDAGENERAL")))
            busqueda_link.click()
            time.sleep(2)  # Más tiempo para que la página se estabilice
            logger.info("✅ Configuración de Búsqueda General abierta")
            
            # Esperar a que la interfaz esté completamente cargada
            time.sleep(1)
            
            # Desmarcar checkboxes 1 y 2 con método robusto
            logger.info("🔧 Desmarcando checkboxes 1 y 2...")
            self.manejar_checkbox_robusto("_1_TABLE_BUSQUEDAGENERAL_1", marcar=False)
            self.manejar_checkbox_robusto("_2_TABLE_BUSQUEDAGENERAL_1", marcar=False)
            
            # Marcar checkboxes 5, 7 y 8 con método robusto
            logger.info("🔧 Marcando checkboxes 5, 7 y 8...")
            checkboxes_a_marcar = ["_5_TABLE_BUSQUEDAGENERAL_1", "_7_TABLE_BUSQUEDAGENERAL_1", "_8_TABLE_BUSQUEDAGENERAL_1"]
            
            for checkbox_id in checkboxes_a_marcar:
                self.manejar_checkbox_robusto(checkbox_id, marcar=True)
            
            # Esperar un momento antes de hacer clic en Seleccionar
            time.sleep(1)
            
            # Hacer clic en "Seleccionar" para aplicar la configuración de filtros
            try:
                seleccionar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_SELECCIONARBUSQUEDAGENERAL")))
                seleccionar_btn.click()
                time.sleep(2)  # Más tiempo para que se apliquen los cambios
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
                time.sleep(3)  # Más tiempo para que se filtren los resultados
                logger.info("✅ Filtros aplicados")
                    
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en Aplicar: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al buscar viaje: {e}")
            return False
    
    def seleccionar_viaje_de_tabla(self):
        """Selecciona el viaje de la tabla de resultados y espera la recarga"""
        try:
            logger.info("🔍 Buscando viaje en la tabla...")
            
            # Selectores específicos basados en el HTML real
            viaje_selectors = [
                "//td[contains(@onclick, 'OnSelectLigne')]",  # Cualquier celda con el onclick correcto
                "//td[contains(@onclick, 'TABLE_PROVIAJES')]",  # Celda específica de la tabla de viajes
                "//div[starts-with(@id, 'TABLE_PROVIAJES_0_')]",  # Div interno de la celda
                "//td[@class and contains(@onclick, 'OnSelectLigne')][1]",  # Primera celda clickeable
                "//table//tr[position()>1]//td[contains(@onclick, 'OnSelectLigne')]",  # Celda en fila de datos
            ]
            
            viaje_seleccionado = False
            
            for i, selector in enumerate(viaje_selectors):
                try:
                    logger.info(f"🎯 Intentando selector {i+1}: {selector}")
                    viaje_elemento = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    
                    # Hacer scroll al elemento
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", viaje_elemento)
                    time.sleep(0.5)
                    
                    # Hacer clic (usar JavaScript para mayor confiabilidad)
                    self.driver.execute_script("arguments[0].click();", viaje_elemento)
                    logger.info(f"✅ Clic realizado en viaje con selector {i+1}")
                    
                    # Esperar la recarga (2-3 segundos)
                    time.sleep(3)
                    
                    # Verificar que el botón cambió de "DESAUTORIZAR" a "AUTORIZAR"
                    try:
                        autorizar_check = self.driver.find_element(By.ID, "BTN_AUTORIZAR")
                        if autorizar_check.is_displayed() and "Autorizar" in autorizar_check.text:
                            logger.info("✅ Viaje seleccionado correctamente - Botón cambió a 'Autorizar'")
                            viaje_seleccionado = True
                            break
                        else:
                            logger.warning(f"⚠️ Selector {i+1}: Botón no cambió a 'Autorizar', probando siguiente...")
                            continue
                    except:
                        logger.warning(f"⚠️ Selector {i+1}: No se encontró botón 'Autorizar', probando siguiente...")
                        continue
                        
                except Exception as e:
                    logger.warning(f"⚠️ Selector {i+1} falló: {e}")
                    continue
            
            if not viaje_seleccionado:
                logger.error("❌ No se pudo seleccionar ningún viaje de la tabla")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al seleccionar viaje de tabla: {e}")
            return False
    
    def autorizar_viaje(self):
        """Hace clic en el botón 'Autorizar' y espera la recarga"""
        try:
            logger.info("🔓 Buscando botón 'Autorizar'...")
            
            # Esperar que el botón esté disponible
            autorizar_btn = self.wait.until(EC.presence_of_element_located((By.ID, "BTN_AUTORIZAR")))
            
            # Hacer scroll al botón
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", autorizar_btn)
            time.sleep(0.5)
            
            # Usar JavaScript click para evitar problemas de elementos superpuestos
            self.driver.execute_script("arguments[0].click();", autorizar_btn)
            logger.info("✅ Botón 'Autorizar' clickeado (JavaScript)")
            
            # Esperar la recarga después de autorizar (1-2 segundos)
            time.sleep(2)
            
            # Verificar que apareció el botón "Facturar"
            try:
                facturar_check = self.wait.until(EC.presence_of_element_located((By.ID, "BTN_FACTURAR")))
                logger.info("✅ Viaje autorizado correctamente - Botón 'Facturar' disponible")
                return True
            except:
                logger.warning("⚠️ Botón 'Facturar' no apareció después de autorizar")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error al autorizar viaje: {e}")
            return False
    
    def facturar_viaje(self):
        """Hace clic en el botón 'Facturar'"""
        try:
            logger.info("💰 Buscando botón 'Facturar'...")
            
            # Esperar que el botón esté disponible
            facturar_btn = self.wait.until(EC.presence_of_element_located((By.ID, "BTN_FACTURAR")))
            
            # Hacer scroll al botón
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", facturar_btn)
            time.sleep(0.5)
            
            # Usar JavaScript click para consistencia
            self.driver.execute_script("arguments[0].click();", facturar_btn)
            logger.info("✅ Botón 'Facturar' clickeado (JavaScript)")
            
            # Esperar un momento para que se complete la facturación
            time.sleep(3)
            
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
                    # Continuar de todas formas
            
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