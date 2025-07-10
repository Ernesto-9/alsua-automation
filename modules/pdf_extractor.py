#!/usr/bin/env python3
"""
Módulo reutilizable para extracción de datos de PDFs
Usado en múltiples automatizaciones de Alsua Transport
ACTUALIZADO: Extrae UUID y Viaje GM automáticamente
VERSIÓN MEJORADA: Intercepta URLs y extrae del DOM
"""

import os
import glob
import time
import logging
import re
import PyPDF2
from datetime import datetime
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFExtractor:
    def __init__(self, carpeta_pdfs="pdfs_temporales", max_pdfs=20):
        """
        Inicializa el extractor de PDFs
        
        Args:
            carpeta_pdfs: Carpeta donde se guardan los PDFs
            max_pdfs: Máximo número de PDFs antes de limpiar
        """
        self.carpeta_pdfs = os.path.abspath(carpeta_pdfs)
        self.max_pdfs = max_pdfs
        self._verificar_carpeta()
    
    def _verificar_carpeta(self):
        """Verifica que la carpeta de PDFs existe"""
        if not os.path.exists(self.carpeta_pdfs):
            os.makedirs(self.carpeta_pdfs, exist_ok=True)
            logger.info(f"✅ Carpeta PDFs creada: {self.carpeta_pdfs}")
        else:
            logger.info(f"✅ Carpeta PDFs verificada: {self.carpeta_pdfs}")
    
    def interceptar_url_pdf(self, driver, timeout=10):
        """
        NUEVO MÉTODO: Intercepta la URL del PDF cuando se abre
        
        Returns:
            str: URL del PDF o None
        """
        try:
            logger.info("🎯 Interceptando URL del PDF...")
            
            # Método 1: Buscar iframes con PDF
            try:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    src = iframe.get_attribute("src")
                    if src and (".pdf" in src.lower() or "pdf" in src.lower()):
                        logger.info(f"✅ PDF encontrado en iframe: {src}")
                        return src
            except Exception as e:
                logger.warning(f"⚠️ No se encontró PDF en iframes: {e}")
            
            # Método 2: Buscar elementos embed/object
            try:
                embeds = driver.find_elements(By.TAG_NAME, "embed")
                for embed in embeds:
                    src = embed.get_attribute("src")
                    type_attr = embed.get_attribute("type")
                    if src and (type_attr == "application/pdf" or ".pdf" in src.lower()):
                        logger.info(f"✅ PDF encontrado en embed: {src}")
                        return src
                
                objects = driver.find_elements(By.TAG_NAME, "object")
                for obj in objects:
                    data = obj.get_attribute("data")
                    type_attr = obj.get_attribute("type")
                    if data and (type_attr == "application/pdf" or ".pdf" in data.lower()):
                        logger.info(f"✅ PDF encontrado en object: {data}")
                        return data
            except Exception as e:
                logger.warning(f"⚠️ No se encontró PDF en embed/object: {e}")
            
            # Método 3: Interceptar peticiones de red
            try:
                # Obtener logs de red del navegador
                logs = driver.get_log('performance')
                for log in logs:
                    message = log.get('message', '')
                    if 'pdf' in message.lower():
                        # Buscar URLs en el log
                        urls = re.findall(r'https?://[^\s"]+\.pdf[^\s"]*', message)
                        if urls:
                            logger.info(f"✅ PDF encontrado en logs de red: {urls[0]}")
                            return urls[0]
            except Exception as e:
                logger.warning(f"⚠️ No se pudo acceder a logs de red: {e}")
            
            # Método 4: Buscar en ventanas nuevas
            try:
                ventanas_originales = driver.window_handles
                if len(ventanas_originales) > 1:
                    # Cambiar a la última ventana
                    driver.switch_to.window(ventanas_originales[-1])
                    current_url = driver.current_url
                    
                    if ".pdf" in current_url.lower():
                        logger.info(f"✅ PDF abierto en nueva ventana: {current_url}")
                        # Volver a la ventana original
                        driver.switch_to.window(ventanas_originales[0])
                        return current_url
                    
                    # Volver a la ventana original
                    driver.switch_to.window(ventanas_originales[0])
            except Exception as e:
                logger.warning(f"⚠️ Error verificando ventanas: {e}")
                
            return None
            
        except Exception as e:
            logger.error(f"❌ Error interceptando URL del PDF: {e}")
            return None
    
    def extraer_datos_del_dom(self, driver):
        """
        NUEVO MÉTODO: Extrae UUID y Viaje GM directamente del DOM
        Maneja específicamente PDFs embebidos en el CRM
        
        Returns:
            dict: {"uuid": str, "viaje_gm": str} o valores None
        """
        try:
            logger.info("🔍 Extrayendo datos directamente del DOM...")
            
            # Esperar un momento para que el contenido se cargue
            time.sleep(3)
            
            # MÉTODO 1: Buscar en el visor de PDF de Chrome embebido
            try:
                # Buscar el iframe o embed que contiene el PDF
                pdf_frames = driver.find_elements(By.XPATH, "//iframe | //embed | //object")
                
                for frame in pdf_frames:
                    try:
                        # Verificar si es un PDF
                        frame_src = frame.get_attribute("src") or frame.get_attribute("data") or ""
                        frame_type = frame.get_attribute("type") or ""
                        
                        if "pdf" in frame_src.lower() or frame_type == "application/pdf":
                            logger.info(f"📄 PDF embebido encontrado: {frame.tag_name}")
                            
                            # Cambiar al contexto del iframe
                            driver.switch_to.frame(frame)
                            
                            # Buscar en el visor de PDF de Chrome
                            # El visor de Chrome renderiza el texto en elementos específicos
                            try:
                                # Esperar que el PDF se cargue
                                time.sleep(2)
                                
                                # Buscar texto en el visor de Chrome PDF
                                # Chrome PDF viewer usa divs con clase específica
                                pdf_text = ""
                                
                                # Intento 1: Buscar en elementos del visor
                                text_elements = driver.find_elements(By.XPATH, "//div[@class='textLayer']//span")
                                if text_elements:
                                    logger.info(f"✅ Encontrados {len(text_elements)} elementos de texto en PDF viewer")
                                    for elem in text_elements:
                                        pdf_text += elem.text + " "
                                
                                # Intento 2: Si no hay textLayer, buscar cualquier texto
                                if not pdf_text:
                                    logger.info("🔍 Buscando texto alternativo en PDF viewer...")
                                    body = driver.find_element(By.TAG_NAME, "body")
                                    pdf_text = body.text
                                
                                # Volver al contexto principal
                                driver.switch_to.default_content()
                                
                                if pdf_text:
                                    logger.info(f"📋 Texto extraído del PDF embebido: {len(pdf_text)} caracteres")
                                    
                                    # Buscar UUID y Viaje GM en el texto extraído
                                    resultado = self._buscar_datos_en_texto(pdf_text)
                                    if resultado["uuid"] or resultado["viaje_gm"]:
                                        return resultado
                                        
                            except Exception as e:
                                logger.warning(f"⚠️ Error extrayendo de iframe: {e}")
                                driver.switch_to.default_content()
                                
                    except Exception as e:
                        logger.warning(f"⚠️ Error procesando frame: {e}")
                        try:
                            driver.switch_to.default_content()
                        except:
                            pass
                            
            except Exception as e:
                logger.warning(f"⚠️ Error buscando en frames: {e}")
            
            # MÉTODO 2: Buscar en el DOM principal (fuera de iframes)
            try:
                # Asegurarse de estar en el contexto principal
                driver.switch_to.default_content()
                
                # Obtener todo el texto visible en la página
                body_text = driver.find_element(By.TAG_NAME, "body").text
                logger.info(f"📋 Texto del DOM principal: {len(body_text)} caracteres")
                
                # Buscar datos en el texto
                resultado = self._buscar_datos_en_texto(body_text)
                if resultado["uuid"] or resultado["viaje_gm"]:
                    return resultado
                    
            except Exception as e:
                logger.warning(f"⚠️ Error extrayendo del DOM principal: {e}")
            
            # MÉTODO 3: Buscar en elementos específicos que podrían contener los datos
            try:
                # Buscar en cualquier elemento que pueda contener UUID o Viaje GM
                elementos_con_datos = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), '-') and (string-length(text()) > 20 or contains(text(), 'COB-') or contains(text(), 'HMO-'))]")
                
                for elem in elementos_con_datos[:20]:  # Limitar a 20 elementos
                    texto = elem.text.strip()
                    if texto:
                        resultado = self._buscar_datos_en_texto(texto)
                        if resultado["uuid"] or resultado["viaje_gm"]:
                            logger.info(f"✅ Datos encontrados en elemento: {elem.tag_name}")
                            return resultado
                            
            except Exception as e:
                logger.warning(f"⚠️ Error buscando en elementos específicos: {e}")
            
            logger.warning("⚠️ No se encontraron datos en el DOM")
            return {"uuid": None, "viaje_gm": None}
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo datos del DOM: {e}")
            # Asegurarse de volver al contexto principal
            try:
                driver.switch_to.default_content()
            except:
                pass
            return {"uuid": None, "viaje_gm": None}
    
    def _buscar_datos_en_texto(self, texto):
        """
        Método auxiliar para buscar UUID y Viaje GM en un texto
        
        Args:
            texto: Texto donde buscar
            
        Returns:
            dict: {"uuid": str, "viaje_gm": str} o valores None
        """
        try:
            # Buscar UUID
            uuid = None
            uuid_pattern = r"([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})"
            uuid_matches = re.findall(uuid_pattern, texto, re.IGNORECASE)
            
            if uuid_matches:
                uuid = uuid_matches[0].upper()
                logger.info(f"✅ UUID encontrado: {uuid}")
            
            # Buscar Viaje GM
            viaje_gm = None
            viaje_patterns = [
                r"Viaje\s+GM[:\s]+([A-Z]{2,4}-\d{4,6})",
                r"VIAJE\s+GM[:\s]+([A-Z]{2,4}-\d{4,6})",
                r"ViajeGM[:\s]+([A-Z]{2,4}-\d{4,6})",
                r"VIAJEGM[:\s]+([A-Z]{2,4}-\d{4,6})",
                r"([A-Z]{2,4}-\d{4,6})",  # Patrón genérico para COB-12345, HMO-12345
            ]
            
            for pattern in viaje_patterns:
                matches = re.findall(pattern, texto, re.IGNORECASE)
                if matches:
                    # Filtrar para obtener solo códigos válidos de viaje
                    for match in matches:
                        if match.startswith(('COB-', 'HMO-', 'OBR-', 'HER-')):
                            viaje_gm = match.strip()
                            logger.info(f"✅ Viaje GM encontrado: {viaje_gm}")
                            break
                    if viaje_gm:
                        break
            
            return {
                "uuid": uuid,
                "viaje_gm": viaje_gm
            }
            
        except Exception as e:
            logger.error(f"❌ Error buscando datos en texto: {e}")
            return {"uuid": None, "viaje_gm": None}
    
    def descargar_pdf_desde_url(self, url, nombre_archivo=None):
        """
        NUEVO MÉTODO: Descarga un PDF desde una URL
        
        Args:
            url: URL del PDF
            nombre_archivo: Nombre opcional para el archivo
            
        Returns:
            str: Ruta del archivo descargado o None
        """
        try:
            logger.info(f"📥 Descargando PDF desde URL: {url}")
            
            # Generar nombre de archivo si no se proporciona
            if not nombre_archivo:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_archivo = f"factura_{timestamp}.pdf"
            
            ruta_completa = os.path.join(self.carpeta_pdfs, nombre_archivo)
            
            # Descargar el archivo
            response = requests.get(url, timeout=30, verify=False)
            response.raise_for_status()
            
            # Guardar el archivo
            with open(ruta_completa, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"✅ PDF descargado exitosamente: {nombre_archivo}")
            return ruta_completa
            
        except Exception as e:
            logger.error(f"❌ Error descargando PDF: {e}")
            return None
    
    def configurar_descarga_chrome(self, driver):
        """Configuración SIMPLE: Configura Chrome para descargar PDFs directamente sin abrirlos"""
        try:
            logger.info("🔧 Configurando Chrome para descarga directa de PDFs...")
            
            # Configuración 1: Comportamiento básico de descarga
            driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': self.carpeta_pdfs
            })
            logger.info("✅ Directorio de descarga configurado")
            
            # Configuración 2: Preferencias para abrir PDFs externamente (descargar en lugar de mostrar)
            try:
                driver.execute_cdp_cmd('Runtime.evaluate', {
                    'expression': '''
                        // Configurar preferencias para descargar PDFs directamente
                        chrome.settingsPrivate.setPref('plugins.always_open_pdf_externally', true);
                        chrome.settingsPrivate.setPref('download.prompt_for_download', false);
                    '''
                })
                logger.info("✅ Preferencias de PDF configuradas para descarga directa")
            except Exception as e:
                logger.warning(f"⚠️ No se pudieron configurar preferencias directamente: {e}")
                
                # Fallback: Configurar mediante CDP
                try:
                    driver.execute_cdp_cmd('Browser.setDownloadBehavior', {
                        'behavior': 'allow',
                        'downloadPath': self.carpeta_pdfs
                    })
                    logger.info("✅ Configuración alternativa aplicada")
                except Exception as e2:
                    logger.warning(f"⚠️ Configuración alternativa falló: {e2}")
            
            # Configuración 3: Deshabilitar visor de PDF interno de forma simple
            try:
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        // Deshabilitar visor interno de PDF
                        Object.defineProperty(navigator, 'pdfViewerEnabled', {
                            value: false,
                            writable: false,
                            configurable: false
                        });
                    '''
                })
                logger.info("✅ Visor interno de PDF deshabilitado")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo deshabilitar visor interno: {e}")
            
            logger.info("🚀 Configuración simple de descarga completada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en configuración de descarga: {e}")
            return False
    
    def buscar_pdf_mas_reciente(self, timeout=10):
        """
        Busca el PDF más reciente en la carpeta
        
        Args:
            timeout: Segundos a esperar por un nuevo PDF
            
        Returns:
            str: Ruta del PDF más reciente o None
        """
        try:
            tiempo_inicio = time.time()
            
            while time.time() - tiempo_inicio < timeout:
                pdfs = glob.glob(os.path.join(self.carpeta_pdfs, "*.pdf"))
                
                if pdfs:
                    # Encontrar el más reciente
                    pdf_mas_reciente = max(pdfs, key=os.path.getmtime)
                    
                    # Verificar que es realmente reciente (último minuto)
                    tiempo_modificacion = os.path.getmtime(pdf_mas_reciente)
                    if time.time() - tiempo_modificacion < 60:  # Último minuto
                        logger.info(f"📄 PDF reciente encontrado: {os.path.basename(pdf_mas_reciente)}")
                        return pdf_mas_reciente
                
                time.sleep(1)  # Esperar 1 segundo antes de revisar de nuevo
            
            logger.warning(f"⚠️ No se encontró PDF reciente en {timeout} segundos")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error buscando PDF más reciente: {e}")
            return None
    
    def extraer_texto_pdf(self, ruta_pdf):
        """
        Extrae todo el texto de un PDF
        
        Args:
            ruta_pdf: Ruta al archivo PDF
            
        Returns:
            str: Texto extraído del PDF
        """
        try:
            logger.info(f"📄 Extrayendo texto de: {os.path.basename(ruta_pdf)}")
            
            with open(ruta_pdf, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extraer texto de todas las páginas
                texto_completo = ""
                for i, page in enumerate(pdf_reader.pages):
                    texto_pagina = page.extract_text()
                    texto_completo += texto_pagina + "\n"  # Agregar salto de línea entre páginas
                    logger.info(f"📋 Página {i+1}: {len(texto_pagina)} caracteres extraídos")
                
                logger.info(f"✅ Texto total extraído: {len(texto_completo)} caracteres")
                return texto_completo
                
        except Exception as e:
            logger.error(f"❌ Error extrayendo texto del PDF: {e}")
            return None
    
    def extraer_folio_fiscal(self, texto_pdf):
        """
        Extrae el folio fiscal (UUID) del texto del PDF
        
        Args:
            texto_pdf: Texto extraído del PDF
            
        Returns:
            str: Folio fiscal encontrado o None
        """
        try:
            logger.info("🔍 Buscando folio fiscal (UUID) en el texto...")
            
            # Mostrar una muestra del texto para debug
            logger.info(f"📋 Muestra del texto (primeros 500 chars): {texto_pdf[:500]}...")
            
            # Patrón principal: UUID estándar con guiones (8-4-4-4-12 caracteres hexadecimales)
            patron_uuid = r"([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})"
            matches_uuid = re.findall(patron_uuid, texto_pdf, re.IGNORECASE)
            
            if matches_uuid:
                # Tomar el primer UUID encontrado (normalmente es el folio fiscal)
                folio_fiscal = matches_uuid[0].upper()
                logger.info(f"✅ Folio fiscal encontrado: {folio_fiscal}")
                return folio_fiscal
            else:
                logger.warning("⚠️ No se encontró folio fiscal con patrón UUID")
                
                # Debug: buscar texto que contenga "folio"
                lineas_folio = [linea for linea in texto_pdf.split('\n') if 'folio' in linea.lower()]
                if lineas_folio:
                    logger.info("🔍 Líneas que contienen 'folio':")
                    for linea in lineas_folio[:3]:  # Mostrar máximo 3 líneas
                        logger.info(f"   - {linea.strip()}")
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error buscando folio fiscal: {e}")
            return None
    
    def extraer_viaje_gm(self, texto_pdf):
        """
        Extrae el Viaje GM del texto del PDF
        
        Args:
            texto_pdf: Texto extraído del PDF
            
        Returns:
            str: Viaje GM encontrado o None
        """
        try:
            logger.info("🔍 Buscando Viaje GM en el texto...")
            
            # Patrones para buscar Viaje GM
            patrones_viaje_gm = [
                r"Viaje\s+GM:\s*([A-Z0-9\-]+)",  # "Viaje GM: COB-38048"
                r"VIAJE\s+GM:\s*([A-Z0-9\-]+)",  # "VIAJE GM: COB-38048"
                r"Viaje\s*GM\s*:\s*([A-Z0-9\-]+)",  # Variaciones con espacios
                r"VIAJEGM:\s*([A-Z0-9\-]+)",  # "VIAJEGM: COB-38048"
                r"ViajeGM:\s*([A-Z0-9\-]+)",  # "ViajeGM: COB-38048"
            ]
            
            for patron in patrones_viaje_gm:
                matches = re.findall(patron, texto_pdf, re.IGNORECASE)
                if matches:
                    viaje_gm = matches[0].strip()
                    logger.info(f"✅ Viaje GM encontrado con patrón '{patron}': {viaje_gm}")
                    return viaje_gm
            
            # Si no encuentra con patrones específicos, buscar líneas que contengan "viaje"
            logger.warning("⚠️ No se encontró Viaje GM con patrones específicos")
            logger.info("🔍 Buscando líneas que contengan 'viaje'...")
            
            lineas_viaje = [linea for linea in texto_pdf.split('\n') if 'viaje' in linea.lower()]
            if lineas_viaje:
                logger.info("🔍 Líneas que contienen 'viaje':")
                for linea in lineas_viaje[:5]:  # Mostrar máximo 5 líneas
                    linea_limpia = linea.strip()
                    logger.info(f"   - {linea_limpia}")
                    
                    # Buscar códigos tipo COB-38048 en estas líneas
                    codigo_match = re.search(r"([A-Z]{2,4}-\d{4,6})", linea_limpia)
                    if codigo_match:
                        codigo_encontrado = codigo_match.group(1)
                        logger.info(f"✅ Posible Viaje GM encontrado en línea: {codigo_encontrado}")
                        return codigo_encontrado
            
            logger.warning("⚠️ No se encontró Viaje GM en el PDF")
            return None
                
        except Exception as e:
            logger.error(f"❌ Error buscando Viaje GM: {e}")
            return None
    
    def extraer_datos_completos(self, texto_pdf):
        """
        Extrae tanto UUID como Viaje GM del PDF
        
        Args:
            texto_pdf: Texto extraído del PDF
            
        Returns:
            dict: {"uuid": str, "viaje_gm": str} o valores None si no se encuentran
        """
        try:
            logger.info("🚀 Extrayendo datos completos del PDF...")
            
            # Extraer UUID
            uuid = self.extraer_folio_fiscal(texto_pdf)
            
            # Extraer Viaje GM
            viaje_gm = self.extraer_viaje_gm(texto_pdf)
            
            # Resultado
            resultado = {
                "uuid": uuid,
                "viaje_gm": viaje_gm
            }
            
            logger.info("📊 Resultado de extracción:")
            logger.info(f"   🆔 UUID: {uuid}")
            logger.info(f"   🚛 Viaje GM: {viaje_gm}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error en extracción completa: {e}")
            return {"uuid": None, "viaje_gm": None}
    
    def extraer_de_pdf_automatico(self, driver, timeout=15):
        """
        FUNCIÓN MEJORADA: Proceso completo de extracción con múltiples métodos
        
        Args:
            driver: WebDriver de Selenium
            timeout: Segundos a esperar por el PDF
            
        Returns:
            dict: {"uuid": str, "viaje_gm": str} con los datos extraídos
        """
        try:
            logger.info("🚀 Iniciando extracción automática completa MEJORADA")
            
            # MÉTODO 1: Intentar extraer directamente del DOM
            logger.info("📄 Método 1: Extrayendo datos del DOM...")
            datos_dom = self.extraer_datos_del_dom(driver)
            
            if datos_dom["uuid"] and datos_dom["viaje_gm"]:
                logger.info("🎉 Datos extraídos exitosamente del DOM")
                return datos_dom
            
            # MÉTODO 2: Interceptar URL del PDF y descargarlo
            logger.info("📄 Método 2: Interceptando URL del PDF...")
            pdf_url = self.interceptar_url_pdf(driver)
            
            if pdf_url:
                # Descargar el PDF
                pdf_path = self.descargar_pdf_desde_url(pdf_url)
                
                if pdf_path:
                    # Extraer texto del PDF
                    texto_pdf = self.extraer_texto_pdf(pdf_path)
                    
                    if texto_pdf:
                        # Extraer datos completos
                        datos_pdf = self.extraer_datos_completos(texto_pdf)
                        
                        # Combinar datos del DOM y del PDF (priorizar los que falten)
                        if not datos_dom["uuid"] and datos_pdf["uuid"]:
                            datos_dom["uuid"] = datos_pdf["uuid"]
                        if not datos_dom["viaje_gm"] and datos_pdf["viaje_gm"]:
                            datos_dom["viaje_gm"] = datos_pdf["viaje_gm"]
                        
                        if datos_dom["uuid"] or datos_dom["viaje_gm"]:
                            logger.info("🎉 Datos extraídos exitosamente combinando métodos")
                            return datos_dom
            
            # MÉTODO 3: Método original - esperar descarga automática
            logger.info("📄 Método 3: Esperando descarga automática...")
            self.configurar_descarga_chrome(driver)
            
            pdf_path = self.buscar_pdf_mas_reciente(timeout)
            
            if pdf_path:
                texto_pdf = self.extraer_texto_pdf(pdf_path)
                
                if texto_pdf:
                    datos_pdf = self.extraer_datos_completos(texto_pdf)
                    
                    # Combinar con datos del DOM si existen
                    if not datos_dom["uuid"] and datos_pdf["uuid"]:
                        datos_dom["uuid"] = datos_pdf["uuid"]
                    if not datos_dom["viaje_gm"] and datos_pdf["viaje_gm"]:
                        datos_dom["viaje_gm"] = datos_pdf["viaje_gm"]
                    
                    return datos_dom
            
            # Si llegamos aquí, retornar lo que hayamos podido extraer del DOM
            if datos_dom["uuid"] or datos_dom["viaje_gm"]:
                logger.warning("⚠️ Extracción parcial - solo algunos datos encontrados")
                return datos_dom
            
            logger.error("❌ No se pudieron extraer los datos con ningún método")
            return {"uuid": None, "viaje_gm": None}
            
        except Exception as e:
            logger.error(f"❌ Error en extracción automática mejorada: {e}")
            return {"uuid": None, "viaje_gm": None}
    
    def limpiar_pdfs_viejos(self):
        """Limpia PDFs si hay más del máximo permitido"""
        try:
            pdfs = glob.glob(os.path.join(self.carpeta_pdfs, "*.pdf"))
            
            if len(pdfs) > self.max_pdfs:
                # Ordenar por fecha de modificación y eliminar los más viejos
                pdfs.sort(key=os.path.getmtime)
                pdfs_a_eliminar = pdfs[:-self.max_pdfs]  # Mantener solo los últimos max_pdfs
                
                for pdf in pdfs_a_eliminar:
                    os.remove(pdf)
                    logger.info(f"🗑️ PDF viejo eliminado: {os.path.basename(pdf)}")
                    
                logger.info(f"🧹 Limpieza completada: {len(pdfs_a_eliminar)} PDFs eliminados, {self.max_pdfs} mantenidos")
            else:
                logger.info(f"ℹ️ Limpieza no necesaria: {len(pdfs)} PDFs (máximo: {self.max_pdfs})")
                
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando PDFs viejos: {e}")
    
    def obtener_estadisticas(self):
        """Obtiene estadísticas de la carpeta de PDFs"""
        try:
            pdfs = glob.glob(os.path.join(self.carpeta_pdfs, "*.pdf"))
            
            if not pdfs:
                return {
                    'total_pdfs': 0,
                    'carpeta': self.carpeta_pdfs,
                    'espacio_usado': '0 MB'
                }
            
            # Calcular espacio usado
            espacio_total = sum(os.path.getsize(pdf) for pdf in pdfs)
            espacio_mb = espacio_total / (1024 * 1024)
            
            return {
                'total_pdfs': len(pdfs),
                'carpeta': self.carpeta_pdfs,
                'espacio_usado': f"{espacio_mb:.2f} MB",
                'pdf_mas_reciente': os.path.basename(max(pdfs, key=os.path.getmtime))
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {'error': str(e)}

# Funciones de conveniencia para uso rápido
def extraer_datos_automatico(driver, carpeta_pdfs="pdfs_temporales", timeout=15):
    """
    FUNCIÓN MEJORADA: Extrae UUID y Viaje GM automáticamente
    
    Args:
        driver: WebDriver de Selenium
        carpeta_pdfs: Carpeta donde buscar PDFs
        timeout: Segundos a esperar por el PDF
        
    Returns:
        dict: {"uuid": str, "viaje_gm": str} con los datos extraídos
    """
    extractor = PDFExtractor(carpeta_pdfs)
    return extractor.extraer_de_pdf_automatico(driver, timeout)

# Función legacy para compatibilidad
def extraer_folio_fiscal_automatico(driver, carpeta_pdfs="pdfs_temporales", timeout=15):
    """
    Función de compatibilidad - ahora retorna solo el UUID
    """
    datos = extraer_datos_automatico(driver, carpeta_pdfs, timeout)
    return datos.get("uuid")

# Script de prueba
if __name__ == "__main__":
    print("🧪 Probando PDFExtractor mejorado...")
    
    try:
        extractor = PDFExtractor()
        stats = extractor.obtener_estadisticas()
        
        print("📊 Estadísticas:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
            
        # Limpiar PDFs viejos
        extractor.limpiar_pdfs_viejos()
        
        print("✅ PDFExtractor funcionando correctamente")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Asegúrate de que la carpeta 'pdfs_temporales' existe")