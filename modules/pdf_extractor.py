#!/usr/bin/env python3
"""
Módulo reutilizable para extracción de datos de PDFs
Usado en múltiples automatizaciones de Alsua Transport
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
            raise Exception(f"❌ Carpeta {self.carpeta_pdfs} no encontrada. Créala manualmente.")
        logger.info(f"✅ Carpeta PDFs verificada: {self.carpeta_pdfs}")
    
    def configurar_descarga_chrome(self, driver):
        """Configura Chrome para descargar PDFs automáticamente"""
        try:
            driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': self.carpeta_pdfs
            })
            logger.info("✅ Chrome configurado para descarga automática de PDFs")
            return True
        except Exception as e:
            logger.warning(f"⚠️ No se pudo configurar descarga automática: {e}")
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
                    texto_completo += texto_pagina
                    logger.info(f"📋 Página {i+1}: {len(texto_pagina)} caracteres extraídos")
                
                logger.info(f"✅ Texto total extraído: {len(texto_completo)} caracteres")
                return texto_completo
                
        except Exception as e:
            logger.error(f"❌ Error extrayendo texto del PDF: {e}")
            return None
    
    def extraer_folio_fiscal(self, texto_pdf):
        """
        Extrae el folio fiscal del texto del PDF
        
        Args:
            texto_pdf: Texto extraído del PDF
            
        Returns:
            str: Folio fiscal encontrado o None
        """
        try:
            logger.info("🔍 Buscando folio fiscal en el texto...")
            
            # Mostrar una muestra del texto para debug
            logger.info(f"📋 Muestra del texto (primeros 300 chars): {texto_pdf[:300]}...")
            
            # Patrón 1: "Folio Fiscal" seguido de UUID con guiones
            patron1 = r"Folio\s*Fiscal[:\s]*([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})"
            match1 = re.search(patron1, texto_pdf, re.IGNORECASE)
            
            # Patrón 2: UUID estándar en cualquier parte
            patron2 = r"([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})"
            match2 = re.search(patron2, texto_pdf)
            
            # Patrón 3: Folio fiscal sin guiones (32 caracteres hexadecimales)
            patron3 = r"Folio\s*Fiscal[:\s]*([A-F0-9]{32})"
            match3 = re.search(patron3, texto_pdf, re.IGNORECASE)
            
            # Patrón 4: Cualquier secuencia de 32 caracteres hexadecimales
            patron4 = r"([A-F0-9]{32})"
            match4 = re.search(patron4, texto_pdf)
            
            if match1:
                folio = match1.group(1)
                logger.info(f"✅ Folio fiscal encontrado (Patrón 1 - con 'Folio Fiscal'): {folio}")
                return folio
            elif match2:
                folio = match2.group(1)
                logger.info(f"✅ Folio fiscal encontrado (Patrón 2 - UUID con guiones): {folio}")
                return folio
            elif match3:
                folio = match3.group(1)
                logger.info(f"✅ Folio fiscal encontrado (Patrón 3 - con 'Folio Fiscal' sin guiones): {folio}")
                return folio
            elif match4:
                folio = match4.group(1)
                logger.info(f"✅ Folio fiscal encontrado (Patrón 4 - 32 chars hex): {folio}")
                return folio
            else:
                logger.warning("⚠️ No se encontró folio fiscal con ningún patrón")
                
                # Debug: mostrar todo el texto para análisis
                logger.info("🔍 Texto completo para análisis manual:")
                logger.info(f"{texto_pdf}")
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error buscando folio fiscal: {e}")
            return None
    
    def extraer_folio_de_pdf_automatico(self, driver, timeout=15):
        """
        Proceso completo: configura descarga, espera PDF y extrae folio
        
        Args:
            driver: WebDriver de Selenium
            timeout: Segundos a esperar por el PDF
            
        Returns:
            str: Folio fiscal extraído o None
        """
        try:
            logger.info("🚀 Iniciando extracción automática de folio fiscal")
            
            # Paso 1: Configurar descarga
            self.configurar_descarga_chrome(driver)
            
            # Paso 2: Esperar que aparezca un PDF nuevo
            logger.info(f"⏳ Esperando PDF nuevo (timeout: {timeout}s)...")
            pdf_path = self.buscar_pdf_mas_reciente(timeout)
            
            if not pdf_path:
                logger.error("❌ No se encontró PDF descargado")
                return None
            
            # Paso 3: Extraer texto del PDF
            texto_pdf = self.extraer_texto_pdf(pdf_path)
            
            if not texto_pdf:
                logger.error("❌ No se pudo extraer texto del PDF")
                return None
            
            # Paso 4: Buscar folio fiscal
            folio_fiscal = self.extraer_folio_fiscal(texto_pdf)
            
            if folio_fiscal:
                logger.info(f"🎉 Folio fiscal extraído exitosamente: {folio_fiscal}")
            else:
                logger.error("❌ No se pudo extraer folio fiscal")
            
            return folio_fiscal
            
        except Exception as e:
            logger.error(f"❌ Error en extracción automática: {e}")
            return None
    
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

# Función de conveniencia para uso rápido
def extraer_folio_fiscal_automatico(driver, carpeta_pdfs="pdfs_temporales", timeout=15):
    """
    Función de conveniencia para extraer folio fiscal automáticamente
    
    Args:
        driver: WebDriver de Selenium
        carpeta_pdfs: Carpeta donde buscar PDFs
        timeout: Segundos a esperar por el PDF
        
    Returns:
        str: Folio fiscal extraído o None
    """
    extractor = PDFExtractor(carpeta_pdfs)
    return extractor.extraer_folio_de_pdf_automatico(driver, timeout)

# Script de prueba
if __name__ == "__main__":
    print("🧪 Probando PDFExtractor...")
    
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