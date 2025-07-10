#!/usr/bin/env python3
"""
Módulo reutilizable para extracción de datos de PDFs
Usado en múltiples automatizaciones de Alsua Transport
ACTUALIZADO: Extrae UUID y Viaje GM automáticamente
"""

import os
import glob
import time
import logging
import re
import PyPDF2
from datetime import datetime

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
    
    def configurar_descarga_chrome(self, driver):
        """CONFIGURACIÓN SIMPLE: Configura Chrome para descargar PDFs directamente sin abrirlos"""
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
        NUEVA FUNCIÓN: Extrae el Viaje GM del texto del PDF
        
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
        NUEVA FUNCIÓN: Extrae tanto UUID como Viaje GM del PDF
        
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
        FUNCIÓN ACTUALIZADA: Proceso completo de descarga y extracción automática
        
        Args:
            driver: WebDriver de Selenium
            timeout: Segundos a esperar por el PDF
            
        Returns:
            dict: {"uuid": str, "viaje_gm": str} con los datos extraídos
        """
        try:
            logger.info("🚀 Iniciando extracción automática completa")
            
            # Paso 1: Configurar descarga
            self.configurar_descarga_chrome(driver)
            
            # Paso 2: Esperar que aparezca un PDF nuevo
            logger.info(f"⏳ Esperando PDF nuevo (timeout: {timeout}s)...")
            pdf_path = self.buscar_pdf_mas_reciente(timeout)
            
            if not pdf_path:
                logger.error("❌ No se encontró PDF descargado")
                return {"uuid": None, "viaje_gm": None}
            
            # Paso 3: Extraer texto del PDF
            texto_pdf = self.extraer_texto_pdf(pdf_path)
            
            if not texto_pdf:
                logger.error("❌ No se pudo extraer texto del PDF")
                return {"uuid": None, "viaje_gm": None}
            
            # Paso 4: Extraer datos completos
            datos_extraidos = self.extraer_datos_completos(texto_pdf)
            
            if datos_extraidos["uuid"] or datos_extraidos["viaje_gm"]:
                logger.info(f"🎉 Extracción completada exitosamente")
            else:
                logger.error("❌ No se pudieron extraer los datos del PDF")
            
            return datos_extraidos
            
        except Exception as e:
            logger.error(f"❌ Error en extracción automática: {e}")
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
    NUEVA FUNCIÓN: Extrae UUID y Viaje GM automáticamente
    
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