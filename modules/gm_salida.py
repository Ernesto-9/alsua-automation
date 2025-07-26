from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import csv
import os
import logging
from datetime import datetime
# SIMPLIFICADO: Solo importar sistema de log CSV
from viajes_log import registrar_viaje_fallido as log_viaje_fallido

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GMSalidaAutomation:
    def __init__(self, driver, datos_viaje=None):
        self.driver = driver
        self.wait = WebDriverWait(driver, 30)  # Aumentado de 20 a 30
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
    
    def llenar_fecha_salida_robusto(self, campo_id, fecha_valor):
        """
        FUNCIÓN MEJORADA: Llena fecha de salida con validación anti-1000
        
        Args:
            campo_id: ID del campo de fecha
            fecha_valor: Fecha en formato DD/MM/YYYY
            
        Returns:
            bool: True si se insertó correctamente, False si falló
        """
        try:
            logger.info(f"🎯 Llenando fecha en {campo_id}: {fecha_valor}")
            
            # Intentar hasta 3 veces si hay problemas
            for intento in range(3):
                # Paso 1: Localizar y hacer clic en el campo
                campo = self.wait.until(EC.element_to_be_clickable((By.ID, campo_id)))
                
                # Paso 2: LIMPIEZA AGRESIVA
                campo.click()
                time.sleep(0.3)
                
                # Múltiples métodos de limpieza
                campo.send_keys(Keys.CONTROL + "a")  # Seleccionar todo
                time.sleep(0.1)
                campo.send_keys(Keys.DELETE)         # Borrar selección
                time.sleep(0.1)
                campo.clear()                        # Método clear adicional
                time.sleep(0.1)
                
                # Limpieza adicional caracter por caracter
                for _ in range(15):  # Eliminar hasta 15 caracteres residuales
                    campo.send_keys(Keys.BACKSPACE)
                    time.sleep(0.05)
                
                # Paso 3: Verificar que está limpio
                valor_actual = campo.get_attribute("value")
                
                if valor_actual and len(valor_actual) > 0:
                    # Una limpieza final
                    campo.send_keys(Keys.HOME)
                    time.sleep(0.1)
                    for _ in range(20):
                        campo.send_keys(Keys.DELETE)
                        time.sleep(0.02)
                
                # Paso 4: INSERTAR FECHA LENTAMENTE
                time.sleep(0.5)  # Pausa antes de escribir
                
                # Escribir carácter por carácter para evitar problemas
                for i, char in enumerate(fecha_valor):
                    campo.send_keys(char)
                    time.sleep(0.08)  # Pausa entre caracteres
                
                # Paso 5: VALIDACIÓN INMEDIATA
                time.sleep(0.5)  # Esperar que se procese
                valor_final = campo.get_attribute("value")
                
                # Verificar que no tiene el problema del 1000
                if "1000" in valor_final:
                    logger.error(f"🚨 ERROR: Fecha con '1000' en intento {intento + 1}")
                    continue
                    
                # Verificar longitud razonable (DD/MM/YYYY = 10 caracteres + posible hora)
                if len(valor_final) > 20:
                    logger.error(f"🚨 ERROR: Fecha muy larga en intento {intento + 1}")
                    continue
                
                # Verificar que contiene la fecha esperada
                if fecha_valor.replace("/", "") not in valor_final.replace("/", "").replace(" ", ""):
                    logger.error(f"🚨 ERROR: Fecha no coincide en intento {intento + 1}")
                    continue
                
                # Si llegamos aquí, la fecha está correcta
                logger.info(f"✅ Fecha insertada correctamente: {fecha_valor}")
                
                # Confirmar con ENTER
                campo.send_keys(Keys.ENTER)
                time.sleep(0.3)
                
                return True
                
            # Si llegamos aquí, fallaron todos los intentos
            logger.error(f"❌ ERROR CRÍTICO: No se pudo insertar fecha después de 3 intentos")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error en llenar_fecha_salida_robusto: {e}")
            return False
    
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
        FUNCIÓN SIMPLIFICADA: Maneja el error de operador ocupado
        SOLO registra en log CSV
        """
        try:
            logger.warning("🚨 MANEJANDO ERROR DE OPERADOR OCUPADO")
            
            # Paso 1: Hacer clic en BTN_OK para cerrar el error
            try:
                btn_ok = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_OK")))
                self.driver.execute_script("arguments[0].click();", btn_ok)
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en BTN_OK: {e}")
            
            # Paso 2: Preparar datos para registro
            prefactura = self.datos_viaje.get('prefactura', 'DESCONOCIDA')
            fecha_viaje = self.datos_viaje.get('fecha', '')
            placa_tractor = self.datos_viaje.get('placa_tractor', 'DESCONOCIDA')
            placa_remolque = self.datos_viaje.get('placa_remolque', 'DESCONOCIDA')
            determinante = self.datos_viaje.get('clave_determinante', 'DESCONOCIDO')
            importe = self.datos_viaje.get('importe', '')
            cliente_codigo = self.datos_viaje.get('cliente_codigo', '')
            
            motivo = f"Operador ocupado - Tractor {placa_tractor} no disponible"
            
            # SIMPLIFICADO: Registrar SOLO en log CSV
            try:
                exito_csv = log_viaje_fallido(
                    prefactura=prefactura,
                    motivo_fallo=motivo,
                    determinante=determinante,
                    fecha_viaje=fecha_viaje,
                    placa_tractor=placa_tractor,
                    placa_remolque=placa_remolque,
                    importe=importe,
                    cliente_codigo=cliente_codigo
                )
                
                if exito_csv:
                    logger.info(f"✅ Operador ocupado registrado: {prefactura} - {placa_tractor}")
                else:
                    logger.error("❌ Error registrando en log CSV")
                    
            except Exception as e:
                logger.error(f"❌ Error registrando en log CSV: {e}")
            
            # Paso 3: Cerrar navegador
            try:
                logger.warning("🚨 Cerrando navegador por operador ocupado")
                self.driver.quit()
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
            
            # Paso 2: DESMARCAR filtros que NO queremos
            filtros_a_desmarcar = ["_1_TABLE_BUSQUEDAGENERAL_1", "_2_TABLE_BUSQUEDAGENERAL_1"]
            
            for filtro_id in filtros_a_desmarcar:
                try:
                    checkbox = self.driver.find_element(By.ID, filtro_id)
                    if checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                        time.sleep(0.3)
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo desmarcar filtro: {e}")
            
            # Paso 3: MARCAR filtros que SÍ queremos
            filtros_a_marcar = ["_5_TABLE_BUSQUEDAGENERAL_1", "_7_TABLE_BUSQUEDAGENERAL_1", "_8_TABLE_BUSQUEDAGENERAL_1"]
            
            for filtro_id in filtros_a_marcar:
                try:
                    checkbox = self.driver.find_element(By.ID, filtro_id)
                    if not checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                        time.sleep(0.3)
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo marcar filtro: {e}")
            
            # Paso 4: Aplicar configuración
            try:
                seleccionar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_SELECCIONARBUSQUEDAGENERAL")))
                seleccionar_btn.click()
                time.sleep(2)
                logger.info("✅ Filtros configurados correctamente")
            except Exception as e:
                logger.error(f"❌ Error al aplicar filtros: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al configurar filtros de búsqueda: {e}")
            return False
    
    def ajustar_fecha_desde(self, fecha_viaje):
        """Ajusta la fecha 'desde' al día anterior del viaje"""
        try:
            fecha_desde = self.calcular_fecha_anterior(fecha_viaje)
            
            # USAR FUNCIÓN ROBUSTA PARA FECHA DESDE
            exito = self.llenar_fecha_salida_robusto("EDT_DESDE", fecha_desde)
            
            if exito:
                logger.info(f"✅ Fecha 'desde' ajustada a: {fecha_desde}")
                return True
            else:
                logger.error(f"❌ Error al ajustar fecha desde con función robusta")
                return False
                
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
                time.sleep(5)  # Aumentado de 3 a 5 segundos
                logger.info("✅ Filtros aplicados")
                    
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en Aplicar: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al buscar viaje: {e}")
            return False
    
    def seleccionar_viaje_de_tabla(self):
        """FUNCIÓN MEJORADA: Selecciona el primer viaje de la tabla después del filtrado"""
        try:
            logger.info("🔍 Seleccionando viaje de la tabla...")
            
            # Esperar más tiempo tras aplicar filtros
            time.sleep(8)  # Aumentado de 3 a 8 segundos
            
            # Intentar hasta 2 veces la selección
            for intento in range(2):
                logger.info(f"🎯 Intento {intento + 1}/2 de selección")
                
                # Buscar elementos de viajes con múltiples selectores
                elementos_proviajes = self.driver.find_elements(By.XPATH, "//div[contains(@id, 'TABLE_PROVIAJES')]")
                filas_tabla = self.driver.find_elements(By.XPATH, "//table//tr[td]")
                elementos_walmart = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'WAL MART') or contains(text(), 'WALMART')]")
                
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
                    if intento == 0:  # Solo reintenta una vez
                        time.sleep(5)
                        continue
                    return False
                
                logger.info(f"✅ Usando selector: {selector_usado}")
                
                # Hacer clic en el primer elemento
                primer_elemento = elementos_a_usar[0]
                try:
                    # Intentar hacer scroll al elemento primero
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", primer_elemento)
                    time.sleep(0.5)
                    
                    # DOBLE CLIC para asegurar selección
                    self.driver.execute_script("arguments[0].click();", primer_elemento)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", primer_elemento)
                    
                    # Esperar más tiempo para que GM procese la selección
                    time.sleep(6)  # Aumentado de 4 a 6 segundos
                    
                    # Verificar que apareció el link "Salida" con mayor timeout
                    try:
                        salida_check = WebDriverWait(self.driver, 25).until(  # Aumentado de 10 a 25 segundos
                            EC.presence_of_element_located((By.LINK_TEXT, "Salida"))
                        )
                        if salida_check.is_displayed():
                            logger.info("✅ Viaje seleccionado correctamente")
                            return True
                        else:
                            logger.error("❌ Link 'Salida' no visible")
                            if intento == 0:  # Solo reintenta una vez
                                time.sleep(3)
                                continue
                            return False
                            
                    except Exception as e:
                        logger.error(f"❌ Link 'Salida' no apareció: {e}")
                        if intento == 0:  # Solo reintenta una vez
                            time.sleep(3)
                            continue
                        return False
                        
                except Exception as e:
                    logger.error(f"❌ Error al hacer clic en el elemento: {e}")
                    if intento == 0:  # Solo reintenta una vez
                        time.sleep(3)
                        continue
                    return False
            
            # Si llegamos aquí, fallaron todos los intentos
            return False
                
        except Exception as e:
            logger.error(f"❌ Error general al seleccionar viaje de tabla: {e}")
            return False
    
    def procesar_salida_viaje(self):
        """Proceso específico de salida del viaje CON DETECCIÓN DE OPERADOR OCUPADO Y FECHA ROBUSTA"""
        try:
            logger.info("🚛 Iniciando proceso de SALIDA del viaje")
            
            # Obtener fecha del viaje
            fecha_viaje = self.datos_viaje.get('fecha', '')
            if not fecha_viaje:
                logger.error("❌ No se encontró fecha del viaje")
                return False
            
            # Paso 1: Hacer clic en el link "Salida" con mejores reintentos
            salida_clickeado = False
            for intento in range(2):  # Máximo 2 intentos
                try:
                    logger.info(f"🎯 Intento {intento + 1}/2 - Buscando link 'Salida'")
                    
                    # Buscar con timeout más largo
                    salida_link = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.LINK_TEXT, "Salida"))
                    )
                    
                    # Verificar que esté visible antes de hacer clic
                    if salida_link.is_displayed() and salida_link.is_enabled():
                        self.driver.execute_script("arguments[0].click();", salida_link)
                        time.sleep(2)  # Aumentado de 1.5 a 2 segundos
                        logger.info("✅ Link 'Salida' clickeado")
                        salida_clickeado = True
                        break
                    else:
                        logger.warning(f"⚠️ Link 'Salida' no visible/habilitado en intento {intento + 1}")
                        if intento == 0:
                            time.sleep(3)
                            continue
                        
                except Exception as e:
                    logger.error(f"❌ Error al hacer clic en 'Salida' intento {intento + 1}: {e}")
                    if intento == 0:
                        time.sleep(3)
                        continue
                    
            if not salida_clickeado:
                logger.error("❌ No se pudo hacer clic en 'Salida' después de 2 intentos")
                return False
                
            # Verificar inmediatamente si hay error de operador ocupado
            if self.detectar_operador_ocupado():
                self.manejar_operador_ocupado()
                return "OPERADOR_OCUPADO"
            
            # Paso 2: Llenar fecha de salida CON FUNCIÓN ROBUSTA
            try:
                logger.info("📅 Llenando fecha de salida con método ROBUSTO...")
                exito_fecha = self.llenar_fecha_salida_robusto("EDT_SALIDA", fecha_viaje)
                
                if not exito_fecha:
                    logger.error("❌ ERROR CRÍTICO: No se pudo insertar fecha de salida después de intentos robustos")
                    return False
                
                logger.info(f"✅ Fecha de salida '{fecha_viaje}' insertada con éxito")
                
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
            
            # Ajustar fecha desde CON FUNCIÓN ROBUSTA
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
            
            # Seleccionar viaje de la tabla (MEJORADO con reintentos)
            if not self.seleccionar_viaje_de_tabla():
                logger.error("❌ Error crítico seleccionando viaje automáticamente")
                return False
            
            # Procesar salida del viaje
            resultado = self.procesar_salida_viaje()
            
            if resultado == "OPERADOR_OCUPADO":
                logger.warning("🚨 OPERADOR OCUPADO: Error registrado en CSV, navegador cerrado")
                logger.info("🔄 MySQL se actualizará automáticamente desde CSV")
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
    FUNCIÓN MEJORADA: Procesar la salida del viaje CON REGISTRO AUTOMÁTICO DE ERRORES
    Retorna:
    - True: Éxito
    - False: Error que debe detener el proceso
    - "OPERADOR_OCUPADO": Operador ocupado, error registrado en CSV, continuar con siguiente viaje
    """
    try:
        automation = GMSalidaAutomation(driver, datos_viaje)
        resultado = automation.procesar_salida_completo(configurar_filtros)
        
        # Registrar el resultado en logs
        prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA') if datos_viaje else 'DESCONOCIDA'
        
        if resultado == "OPERADOR_OCUPADO":
            # Ya se registró en manejar_operador_ocupado()
            logger.warning(f"🚨 VIAJE {prefactura}: Operador ocupado - registrado en CSV")
        elif resultado:
            logger.info(f"✅ VIAJE {prefactura} PROCESADO: Salida completada exitosamente")
        else:  # resultado == False - CUALQUIER ERROR
            logger.error(f"❌ VIAJE {prefactura} FALLÓ: Error en proceso de salida")
            
            # NUEVO: Registrar error genérico en CSV para CUALQUIER fallo
            if datos_viaje:
                try:
                    log_viaje_fallido(
                        prefactura=datos_viaje.get('prefactura', 'DESCONOCIDA'),
                        motivo_fallo="Error en proceso de salida",  # MENSAJE ACORTADO
                        determinante=datos_viaje.get('clave_determinante', ''),
                        fecha_viaje=datos_viaje.get('fecha', ''),
                        placa_tractor=datos_viaje.get('placa_tractor', ''),
                        placa_remolque=datos_viaje.get('placa_remolque', ''),
                        importe=datos_viaje.get('importe', ''),
                        cliente_codigo=datos_viaje.get('cliente_codigo', '')
                    )
                    logger.info("✅ Error de GM_SALIDA registrado en CSV")
                except Exception as log_error:
                    logger.error(f"❌ Error registrando fallo en CSV: {log_error}")
            
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Error en procesar_salida_viaje: {e}")
        
        # NUEVO: También registrar errores de excepción general
        if datos_viaje:
            try:
                log_viaje_fallido(
                    prefactura=datos_viaje.get('prefactura', 'DESCONOCIDA'),
                    motivo_fallo="Error en proceso de salida",  # MENSAJE ACORTADO
                    determinante=datos_viaje.get('clave_determinante', ''),
                    fecha_viaje=datos_viaje.get('fecha', ''),
                    placa_tractor=datos_viaje.get('placa_tractor', ''),
                    placa_remolque=datos_viaje.get('placa_remolque', ''),
                    importe=datos_viaje.get('importe', ''),
                    cliente_codigo=datos_viaje.get('cliente_codigo', '')
                )
                logger.info("✅ Excepción de GM_SALIDA registrada en CSV")
            except Exception as log_error:
                logger.error(f"❌ Error registrando excepción en CSV: {log_error}")
        
        return False