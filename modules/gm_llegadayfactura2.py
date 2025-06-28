import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcesadorLlegadaFactura:
    def __init__(self, driver, datos_viaje):
        self.driver = driver
        self.datos_viaje = datos_viaje
        self.wait = WebDriverWait(driver, 15)
        
    def procesar_llegada_y_factura(self):
        """Proceso principal de llegada y facturación"""
        try:
            logger.info("🚀 Iniciando proceso de llegada y facturación")
            
            # Paso 1: Hacer clic en "Llegada"
            if not self._hacer_clic_llegada():
                return False
                
            # Paso 2: Llenar fecha de llegada y status
            if not self._procesar_llegada():
                return False
                
            # Paso 3: Autorizar
            if not self._autorizar():
                return False
                
            # Paso 4: Facturar
            if not self._procesar_facturacion():
                return False
                
            logger.info("✅ Proceso de llegada y facturación completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de llegada y facturación: {e}")
            return False
    
    def _hacer_clic_llegada(self):
        """Hacer clic en el link de Llegada"""
        try:
            # Buscar el link de Llegada
            llegada_link = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Llegada")))
            self.driver.execute_script("arguments[0].click();", llegada_link)
            time.sleep(1.5)
            logger.info("✅ Link 'Llegada' clickeado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al hacer clic en 'Llegada': {e}")
            return False
    
    def _procesar_llegada(self):
        """Llenar fecha de llegada y seleccionar status TERMINADO"""
        try:
            # Obtener fecha actual para la llegada
            fecha_llegada = datetime.now().strftime("%d/%m/%Y")
            
            # Llenar fecha de llegada
            try:
                fecha_input = self.wait.until(EC.element_to_be_clickable((By.ID, "EDT_LLEGADA")))
                fecha_input.clear()
                fecha_input.send_keys(fecha_llegada)
                logger.info(f"✅ Fecha de llegada '{fecha_llegada}' insertada")
            except Exception as e:
                logger.error(f"❌ Error al insertar fecha de llegada: {e}")
                return False
            
            # Seleccionar status "TERMINADO" (valor 3)
            try:
                status_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATESTATUSVIAJE"))))
                status_select.select_by_value("3")  # TERMINADO
                time.sleep(0.5)
                logger.info("✅ Status 'TERMINADO' seleccionado")
            except Exception as e:
                logger.error(f"❌ Error al seleccionar status TERMINADO: {e}")
                return False
            
            # Hacer clic en "No" (confirmación)
            try:
                no_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                self.driver.execute_script("arguments[0].click();", no_btn)
                time.sleep(1)
                logger.info("✅ Botón 'No' clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'No': {e}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de llegada: {e}")
            return False
    
    def _autorizar(self):
        """Hacer clic en Autorizar"""
        try:
            autorizar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_AUTORIZAR")))
            self.driver.execute_script("arguments[0].click();", autorizar_btn)
            time.sleep(1.5)
            logger.info("✅ Botón 'Autorizar' clickeado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al hacer clic en 'Autorizar': {e}")
            return False
    
    def _procesar_facturacion(self):
        """Proceso completo de facturación"""
        try:
            # Hacer clic en "Facturar"
            facturar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_FACTURAR")))
            self.driver.execute_script("arguments[0].click();", facturar_btn)
            time.sleep(2)
            logger.info("✅ Botón 'Facturar' clickeado")
            
            # Cambiar tipo de documento a "FACTURA CFDI - W" (valor 7)
            try:
                tipo_doc_select = Select(self.wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATTIPOSDOCUMENTOS"))))
                tipo_doc_select.select_by_value("7")  # FACTURA CFDI - W
                time.sleep(0.5)
                logger.info("✅ Tipo de documento 'FACTURA CFDI - W' seleccionado")
            except Exception as e:
                logger.error(f"❌ Error al seleccionar tipo de documento: {e}")
                return False
            
            # Hacer clic en "Aceptar"
            try:
                # Buscar por el texto del span
                aceptar_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Aceptar')]/..")))
                self.driver.execute_script("arguments[0].click();", aceptar_btn)
                time.sleep(2)
                logger.info("✅ Botón 'Aceptar' clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Aceptar': {e}")
                return False
            
            # Confirmar timbrado con "Sí"
            try:
                si_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_YES")))
                self.driver.execute_script("arguments[0].click();", si_btn)
                time.sleep(3)  # Esperar más tiempo para el timbrado
                logger.info("✅ Confirmación 'Sí' para timbrado clickeada")
            except Exception as e:
                logger.error(f"❌ Error al confirmar timbrado: {e}")
                return False
            
            # Procesar impresión
            if not self._procesar_impresion():
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de facturación: {e}")
            return False
    
    def _procesar_impresion(self):
        """Procesar la parte de impresión y verificaciones"""
        try:
            # Hacer clic en "Regresar" primero
            try:
                regresar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_REGRESAR")))
                self.driver.execute_script("arguments[0].click();", regresar_btn)
                time.sleep(1)
                logger.info("✅ Botón 'Regresar' clickeado")
            except Exception as e:
                logger.warning(f"⚠️ No se encontró botón 'Regresar': {e}")
            
            # Hacer clic en "Imprimir"
            try:
                imprimir_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_IMPRIMIR")))
                self.driver.execute_script("arguments[0].click();", imprimir_btn)
                time.sleep(2)
                logger.info("✅ Botón 'Imprimir' clickeado")
            except Exception as e:
                logger.error(f"❌ Error al hacer clic en 'Imprimir': {e}")
                return False
            
            # Verificar existencia de Folio Fiscal y Número de Factura
            self._verificar_datos_factura()
            
            # Cerrar impresión (buscar span vacío)
            try:
                cerrar_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@class='btnvalignmiddle' and text()='']/..")))
                self.driver.execute_script("arguments[0].click();", cerrar_btn)
                time.sleep(1)
                logger.info("✅ Impresión cerrada")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo cerrar impresión automáticamente: {e}")
            
            # Marcar como NO impreso
            try:
                no_impreso_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "BTN_NO")))
                self.driver.execute_script("arguments[0].click();", no_impreso_btn)
                time.sleep(1)
                logger.info("✅ Marcado como 'No impreso'")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo marcar como 'No impreso': {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de impresión: {e}")
            return False
    
    def _verificar_datos_factura(self):
        """Verificar que existen Folio Fiscal y Número de Factura"""
        try:
            # Buscar Folio Fiscal (puede tener diferentes IDs o nombres)
            folio_fiscal_encontrado = False
            numero_factura_encontrado = False
            
            # Intentar encontrar Folio Fiscal
            try:
                # Buscar por texto que contenga "Folio Fiscal" o similar
                folio_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Folio Fiscal') or contains(text(), 'FOLIO FISCAL')]")
                if folio_elements:
                    folio_fiscal_encontrado = True
                    logger.info("✅ Folio Fiscal encontrado")
            except Exception:
                pass
            
            # Intentar encontrar Número de Factura
            try:
                # Buscar por texto que contenga "Factura" o "FACTURA"
                factura_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'FACTURA') or contains(text(), 'Factura')]")
                if factura_elements:
                    numero_factura_encontrado = True
                    logger.info("✅ Número de Factura encontrado")
            except Exception:
                pass
            
            if not folio_fiscal_encontrado:
                logger.warning("⚠️ No se pudo verificar Folio Fiscal")
            if not numero_factura_encontrado:
                logger.warning("⚠️ No se pudo verificar Número de Factura")
                
        except Exception as e:
            logger.warning(f"⚠️ Error al verificar datos de factura: {e}")


def procesar_llegada_factura(driver, datos_viaje):
    """Función principal para procesar llegada y facturación"""
    procesador = ProcesadorLlegadaFactura(driver, datos_viaje)
    return procesador.procesar_llegada_y_factura()