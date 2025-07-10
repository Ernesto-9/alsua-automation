from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
            from datetime import datetime, timedelta
            fecha_obj = datetime.strptime(fecha_str, '%d/%m/%Y')
            fecha_anterior = fecha_obj - timedelta(days=1)
            return fecha_anterior.strftime('%d/%m/%Y')
        except Exception as e:
            logger.error(f"❌ Error al calcular fecha anterior: {e}")
            return fecha_str
    
    def detectar_operador_ocupado(self):
        """
        Detecta el BTN_OK de operador ocupado
        Retorna: True si se detectó, False si no
        """
        try:
            logger.info("🔍 Verificando si apareció BTN_OK de operador ocupado...")
            
            # Buscar específicamente el botón BTN_OK
            try:
                btn_ok = self.driver.find_element(By.ID, "BTN_OK")
                
                if btn_ok.is_displayed() and btn_ok.is_enabled():
                    logger.warning("🚨 BTN_OK DETECTADO - OPERADOR OCUPADO")
                    return True
                    
            except NoSuchElementException:
                # No hay BTN_OK, todo bien
                logger.info("✅ No se detectó BTN_OK - proceso normal")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Error al detectar BTN_OK: {e}")
            return False
    
    def manejar_operador_ocupado(self):
        """
        Maneja el error de operador ocupado:
        1. Hace clic en BTN_OK
        2. Registra error en MySQL 
        3. Cierra navegador
        """
        try:
            logger.warning("🚨 MANEJANDO ERROR DE OPERADOR OCUPADO")
            
            # Paso 1: Hacer clic en BTN_OK para cerrar el error
            try:
                btn_ok = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_OK")))
                self.driver.execute_script("arguments[0].click();", btn_ok)
                time.sleep(2)
                logger.info("✅ BTN_OK clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en BTN_OK: {e}")
            
            # Paso 2: Registrar error en MySQL
            try:
                from modules.mysql_simple import registrar_viaje_fallido
                
                prefactura = self.datos_viaje.get('prefactura', '')
                fecha_viaje = self.datos_viaje.get('fecha', '')
                motivo = f"Operador ocupado - Tractor {self.datos_viaje.get('placa_tractor', 'DESCONOCIDO')} no disponible"
                
                exito_mysql = registrar_viaje_fallido(prefactura, fecha_viaje, motivo)
                
                if exito_mysql:
                    logger.info("✅ Error registrado en MySQL exitosamente")
                else:
                    logger.warning("⚠️ Error registrado en archivo fallback")
                    
            except Exception as e:
                logger.error(f"❌ Error registrando en MySQL: {e}")
            
            # Paso 3: Cerrar navegador
            try:
                logger.warning("🚨 CERRANDO NAVEGADOR por operador ocupado")
                self.driver.quit()
                logger.info("✅ Navegador cerrado exitosamente")
            except Exception as e:
                logger.warning(f"⚠️ Error cerrando navegador: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error general manejando operador ocupado: {e}")
            return False
    
    def configurar_filtros_busqueda(self):
        """Configura los filtros de búsqueda con los checkboxes específicos"""
        try:
            logger.info("⚙️ Configurando filtros de búsqueda...")
            
            # Paso 1: Abrir configuración de Búsqueda General
            busqueda_link = self.wait.until(EC.element_to_be_clickable((By.ID, "LINK_BUSQUEDAGENERAL")))
            busqueda_link.click()
            time.sleep(2)
            logger.info("✅ Configuración de Búsqueda General abierta")
            
            # Paso 2: DESMARCAR filtros que NO queremos
            filtros_a_desmarcar = ["_1_TABLE_BUSQUEDAGENERAL_1", "_2_TABLE_BUSQUEDAGENERAL_1"]
            
            for filtro_id in filtros_a_desmarcar:
                try:
                    checkbox = self.driver.find_element(By.ID, filtro_id)
                    if checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                        logger.info(f"   ✅ DESMARCADO: {filtro_id}")
                        time.sleep(0.3)
                    else:
                        logger.info(f"   ℹ️ Ya desmarcado: {filtro_id}")
                except Exception as e:
                    logger.warning(f"   ⚠️ No se pudo desmarcar {filtro_id}: {e}")
            
            # Paso 3: MARCAR filtros que SÍ queremos
            filtros_a_marcar = ["_5_TABLE_BUSQUEDAGENERAL_1", "_7_TABLE_BUSQUEDAGENERAL_1", "_8_TABLE_BUSQUEDAGENERAL_1"]
            
            for filtro_id in filtros_a_marcar:
                try:
                    checkbox = self.driver.find_element(By.ID, filtro_id)
                    if not checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                        logger.info(f"   ✅ MARCADO: {filtro_id}")
                        time.sleep(0.3)
                    else:
                        logger.info(f"   ℹ️ Ya marcado: {filtro_id}")
                except Exception as e:
                    logger.warning(f"   ⚠️ No se pudo marcar {filtro_id}: {e}")
            
            # Paso 4: Aplicar configuración
            try:
                seleccionar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_SELECCIONARBUSQUEDAGENERAL")))
                seleccionar_btn.click()
                time.sleep(2)
                logger.info("✅ Filtros aplicados con 'Seleccionar'")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Seleccionar': {e}")
                return False
            
            logger.info("✅ Configuración de filtros completada")
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
                time.sleep(3)
                logger.info("✅ Filtros aplicados")
                    
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en Aplicar: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al buscar viaje: {e}")
            return False
    
    def seleccionar_viaje_de_tabla(self):
        """FUNCIÓN CON DEBUG: Selecciona el primer viaje de la tabla después del filtrado"""
        try:
            logger.info("🔍 Buscando viajes en la tabla...")
            
            # Esperar más tiempo tras aplicar filtros
            time.sleep(3)
            
            # DEBUG: Buscar elementos de viajes con múltiples selectores
            logger.info("🔍 DEBUG: Probando diferentes selectores...")
            
            # Selector 1: TABLE_PROVIAJES
            elementos_proviajes = self.driver.find_elements(By.XPATH, "//div[contains(@id, 'TABLE_PROVIAJES')]")
            logger.info(f"📊 Selector TABLE_PROVIAJES encontró: {len(elementos_proviajes)} elementos")
            
            # Selector 2: Filas de tabla genéricas
            filas_tabla = self.driver.find_elements(By.XPATH, "//table//tr[td]")
            logger.info(f"📊 Selector filas de tabla encontró: {len(filas_tabla)} elementos")
            
            # Selector 3: Buscar elementos con texto "WALMART" o "WAL MART"
            elementos_walmart = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'WAL MART') or contains(text(), 'WALMART')]")
            logger.info(f"📊 Elementos con WALMART encontrados: {len(elementos_walmart)} elementos")
            
            # DEBUG: Mostrar algunos IDs de elementos encontrados
            if elementos_proviajes:
                logger.info("🔍 IDs de elementos TABLE_PROVIAJES:")
                for i, elem in enumerate(elementos_proviajes[:3]):  # Mostrar máximo 3
                    try:
                        elem_id = elem.get_attribute('id')
                        elem_text = elem.text[:50] if elem.text else "Sin texto"
                        logger.info(f"   {i+1}: ID='{elem_id}' Texto='{elem_text}'")
                    except:
                        logger.info(f"   {i+1}: Error obteniendo info del elemento")
            
            # Decidir qué selector usar - PRIORIZAR WALMART
            elementos_a_usar = None
            selector_usado = ""
            
            if elementos_walmart:
                # PRIORIDAD 1: Usar elementos con texto WALMART (los viajes reales)
                elementos_a_usar = elementos_walmart
                selector_usado = "WALMART text"
            elif elementos_proviajes and len(elementos_proviajes) <= 20:
                # PRIORIDAD 2: Solo usar TABLE_PROVIAJES si hay pocos elementos (evitar headers)
                elementos_a_usar = elementos_proviajes
                selector_usado = "TABLE_PROVIAJES"
            elif filas_tabla and len(filas_tabla) <= 10:
                # PRIORIDAD 3: Filas de tabla solo si hay muy pocas
                elementos_a_usar = filas_tabla
                selector_usado = "filas de tabla"
            else:
                logger.error("❌ No se encontraron elementos válidos para seleccionar")
                logger.error(f"   - WALMART: {len(elementos_walmart)} (MEJOR OPCIÓN)")
                logger.error(f"   - TABLE_PROVIAJES: {len(elementos_proviajes)} (muchos elementos, incluye headers)")
                logger.error(f"   - Filas tabla: {len(filas_tabla)} (muchas filas)")
                return False
            
            logger.info(f"✅ Usando selector: {selector_usado} con {len(elementos_a_usar)} elementos")
            
            # Hacer clic en el primer elemento
            primer_elemento = elementos_a_usar[0]
            try:
                # Intentar hacer scroll al elemento primero
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", primer_elemento)
                time.sleep(0.5)
                
                # Hacer clic
                self.driver.execute_script("arguments[0].click();", primer_elemento)
                logger.info(f"✅ Primer elemento seleccionado automáticamente usando {selector_usado}")
                
                # Esperar más tiempo para que GM procese la selección
                time.sleep(4)
                
                # Verificar que apareció el link "Salida"
                try:
                    salida_check = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.LINK_TEXT, "Salida"))
                    )
                    if salida_check.is_displayed():
                        logger.info("✅ Viaje seleccionado correctamente - Link 'Salida' disponible")
                        return True
                    else:
                        logger.error("❌ Link 'Salida' existe pero no es visible")
                        return False
                        
                except Exception as e:
                    logger.error(f"❌ Link 'Salida' no apareció después de 10 segundos: {e}")
                    
                    # DEBUG: Mostrar qué links están disponibles
                    try:
                        todos_links = self.driver.find_elements(By.TAG_NAME, "a")
                        links_visibles = [link.text.strip() for link in todos_links 
                                        if link.is_displayed() and link.text.strip()]
                        logger.info(f"🔍 Links disponibles actualmente: {links_visibles[:10]}")
                    except:
                        pass
                    
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en el elemento: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error general al seleccionar viaje de tabla: {e}")
            return False
    
    def procesar_salida_viaje(self):
        """Proceso específico de salida del viaje CON DETECCIÓN DE OPERADOR OCUPADO"""
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
                
                # Verificar inmediatamente si hay error de operador ocupado
                if self.detectar_operador_ocupado():
                    self.manejar_operador_ocupado()
                    return "OPERADOR_OCUPADO"
                    
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Salida': {e}")
                return False
            
            # Paso 2: Llenar fecha de salida
            try:
                fecha_input = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_SALIDA")))
                fecha_input.clear()
                fecha_input.send_keys(fecha_viaje)
                logger.info(f"✅ Fecha de salida '{fecha_viaje}' insertada")
                
                # Verificar si hay error después de insertar fecha
                time.sleep(1)
                if self.detectar_operador_ocupado():
                    self.manejar_operador_ocupado()
                    return "OPERADOR_OCUPADO"
                    
            except Exception as e:
                logger.error(f"❌ Error al insertar fecha de salida: {e}")
                return False
            
            # Paso 3: Seleccionar status "EN RUTA"
            try:
                status_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATESTATUSVIAJE"))))
                status_select.select_by_value("2")  # EN RUTA
                time.sleep(0.5)
                logger.info("✅ Status 'EN RUTA' seleccionado")
                
                # Verificar si hay error después de cambiar status
                if self.detectar_operador_ocupado():
                    self.manejar_operador_ocupado()
                    return "OPERADOR_OCUPADO"
                    
            except Exception as e:
                logger.error(f"❌ Error al seleccionar status EN RUTA: {e}")
                return False
            
            # Paso 4: Hacer clic en "Aceptar" (PUNTO CRÍTICO donde aparece BTN_OK)
            try:
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_ACEPTAR")))
                self.driver.execute_script("arguments[0].click();", aceptar_btn)
                time.sleep(3)  # Tiempo extra para que aparezca BTN_OK si hay error
                logger.info("✅ Botón 'Aceptar' clickeado")
                
                # VERIFICACIÓN CRÍTICA: aquí es donde aparece BTN_OK si operador está ocupado
                if self.detectar_operador_ocupado():
                    self.manejar_operador_ocupado()
                    return "OPERADOR_OCUPADO"
                    
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Aceptar': {e}")
                return False
            
            # Paso 5: Responder "No" al envío de correo (solo si no hubo error)
            try:
                no_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                self.driver.execute_script("arguments[0].click();", no_btn)
                time.sleep(2)
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
            
            # Configurar filtros MEJORADO
            if configurar_filtros:
                logger.info("⚙️ Configurando filtros de búsqueda...")
                if not self.configurar_filtros_busqueda():
                    logger.warning("⚠️ No se pudieron configurar los filtros - continuando de todas formas")
                    # Continuar de todas formas, los filtros no son críticos
            
            # Ajustar fecha desde
            if not self.ajustar_fecha_desde(fecha_viaje):
                logger.warning("⚠️ Error ajustando fecha - continuando")
                # No es crítico, continuar
            
            # Seleccionar sucursal
            if not self.seleccionar_sucursal(clave_determinante):
                logger.warning("⚠️ Error seleccionando sucursal - continuando")
                # No es crítico, continuar
            
            # Buscar viaje
            if not self.buscar_viaje(prefactura):
                logger.error("❌ Error crítico buscando viaje")
                return False
            
            # Seleccionar viaje de la tabla (SIN pausas manuales)
            if not self.seleccionar_viaje_de_tabla():
                logger.error("❌ Error crítico seleccionando viaje automáticamente")
                return False
            
            # Procesar salida del viaje
            resultado = self.procesar_salida_viaje()
            
            if resultado == "OPERADOR_OCUPADO":
                logger.warning("🚨 OPERADOR OCUPADO: Error registrado, navegador cerrado")
                return "OPERADOR_OCUPADO"
            elif resultado:
                logger.info("✅ Proceso completo de salida completado exitosamente")
                return True
            else:
                logger.error("❌ Error en proceso de salida")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error general en procesar_salida_completo: {e}")
            return False

# Función principal para ser llamada desde otros módulos
def procesar_salida_viaje(driver, datos_viaje=None, configurar_filtros=True):
    """
    Función principal para procesar la salida del viaje
    Retorna:
    - True: Éxito
    - False: Error que debe detener el proceso
    - "OPERADOR_OCUPADO": Operador ocupado, error registrado, continuar con siguiente viaje
    """
    try:
        automation = GMSalidaAutomation(driver, datos_viaje)
        resultado = automation.procesar_salida_completo(configurar_filtros)
        
        # Registrar el resultado en logs
        prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA') if datos_viaje else 'DESCONOCIDA'
        
        if resultado == "OPERADOR_OCUPADO":
            logger.warning(f"🚨 VIAJE {prefactura}: Operador ocupado - error registrado en MySQL")
        elif resultado:
            logger.info(f"✅ VIAJE {prefactura} PROCESADO: Salida completada exitosamente")
        else:
            logger.error(f"❌ VIAJE {prefactura} FALLÓ: Error en proceso de salida")
            
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Error en procesar_salida_viaje: {e}")
        return False