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
        self.wait = WebDriverWait(driver, 20)
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
            logger.info("🔍 Buscando viajes en la tabla...")
            
            # TODO: TEMPORAL PARA PRUEBAS - BORRAR DESPUÉS
            logger.info("⏸️ MODO PRUEBAS: Selecciona manualmente el viaje que quieres procesar")
            input("🟢 Presiona ENTER después de seleccionar el viaje que quieres...")
            logger.info("✅ Continuando automatización...")
            
            # Verificar que hay un viaje seleccionado
            try:
                # Verificar si está disponible "Salida" o "Llegada"
                salida_disponible = False
                llegada_disponible = False
                
                try:
                    salida_check = self.driver.find_element(By.LINK_TEXT, "Salida")
                    if salida_check.is_displayed():
                        salida_disponible = True
                        logger.info("✅ Viaje seleccionado - Link 'Salida' disponible")
                except:
                    pass
                
                try:
                    llegada_check = self.driver.find_element(By.LINK_TEXT, "Llegada")
                    if llegada_check.is_displayed():
                        llegada_disponible = True
                        logger.info("✅ Viaje seleccionado - Link 'Llegada' disponible")
                except:
                    pass
                
                if salida_disponible or llegada_disponible:
                    return True
                else:
                    logger.error("❌ No se detectaron links 'Salida' o 'Llegada' - ¿Seleccionaste un viaje?")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error al verificar viaje seleccionado: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al seleccionar viaje de tabla: {e}")
            return False
    
    def procesar_salida_viaje(self):
        """Proceso específico de salida del viaje"""
        try:
            logger.info("🚛 Iniciando proceso de SALIDA del viaje")
            
            # Obtener fecha del viaje
            fecha_viaje = self.datos_viaje.get('fecha', '')
            if not fecha_viaje:
                logger.error("❌ No se encontró fecha del viaje")
                return False
            
            # Paso 1: Hacer clic en el link "Salida"
            try:
                salida_link = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Salida")))
                self.driver.execute_script("arguments[0].click();", salida_link)
                time.sleep(1.5)
                logger.info("✅ Link 'Salida' clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Salida': {e}")
                return False
            
            # Paso 2: Llenar fecha de salida (la misma fecha del viaje)
            try:
                fecha_input = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_SALIDA")))
                fecha_input.clear()
                fecha_input.send_keys(fecha_viaje)
                logger.info(f"✅ Fecha de salida '{fecha_viaje}' insertada")
            except Exception as e:
                logger.error(f"❌ Error al insertar fecha de salida: {e}")
                return False
            
            # Paso 3: Seleccionar status "EN RUTA" (valor 2)
            try:
                status_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATESTATUSVIAJE"))))
                status_select.select_by_value("2")  # EN RUTA
                time.sleep(0.5)
                logger.info("✅ Status 'EN RUTA' seleccionado")
            except Exception as e:
                logger.error(f"❌ Error al seleccionar status EN RUTA: {e}")
                return False
            
            # Paso 4: Hacer clic en "Aceptar"
            try:
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTAR")))
                self.driver.execute_script("arguments[0].click();", aceptar_btn)
                time.sleep(1)
                logger.info("✅ Botón 'Aceptar' clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Aceptar': {e}")
                return False
            
            # Paso 5: Responder "No" al envío de correo
            try:
                no_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                self.driver.execute_script("arguments[0].click();", no_btn)
                time.sleep(2)  # Esperar a que se cierre la ventana y regrese a la lista
                logger.info("✅ Botón 'No' clickeado - Proceso de salida completado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'No': {e}")
                return False
            
            logger.info("✅ Proceso de SALIDA completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de salida: {e}")
            return False
    
    def procesar_salida_completo(self, configurar_filtros=True):
        """Proceso principal para buscar el viaje y procesarle la salida"""
        try:
            logger.info("🚀 Iniciando proceso completo de salida del viaje")
            
            # Extraer datos necesarios
            fecha_viaje = self.datos_viaje.get('fecha', '')
            prefactura = self.datos_viaje.get('prefactura', '')
            clave_determinante = self.datos_viaje.get('clave_determinante', '')
            
            if not all([fecha_viaje, prefactura, clave_determinante]):
                logger.error("❌ Faltan datos necesarios para procesar salida")
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
            
            # Procesar salida del viaje
            if not self.procesar_salida_viaje():
                return False
            
            logger.info("✅ Proceso completo de salida completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error general en procesar_salida_completo: {e}")
            return False

# Función principal para ser llamada desde otros módulos
def procesar_salida_viaje(driver, datos_viaje=None, configurar_filtros=True):
    """Función principal para procesar la salida del viaje"""
    try:
        automation = GMSalidaAutomation(driver, datos_viaje)
        return automation.procesar_salida_completo(configurar_filtros)
    except Exception as e:
        logger.error(f"❌ Error en procesar_salida_viaje: {e}")
        return False

# Ejemplo de uso
if __name__ == "__main__":
    # Este bloque se ejecutaría solo si ejecutas este archivo directamente
    # Aquí puedes agregar código de prueba
    pass