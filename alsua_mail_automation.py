#!/usr/bin/env python3
"""
Sistema completo de automatización Alsua Transport
Mail Reader → Parser → GM Automation
"""

import os
import time
import logging
import re
from datetime import datetime
import win32com.client
from modules.parser import parse_xls
from modules.gm_login import login_to_gm
from modules.gm_transport_general import GMTransportAutomation

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('alsua_automation.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class AlsuaMailAutomation:
    def __init__(self):
        self.carpeta_descarga = r"C:\Users\MONITOR3\Documents\ROBOTS\VACIO\alsua-automation\archivos_descargados"
        self.correos_procesados = set()  # Para evitar reprocesar
        self.driver = None
        self._crear_carpeta_descarga()
        
    def _crear_carpeta_descarga(self):
        """Crear carpeta de descarga si no existe"""
        if not os.path.exists(self.carpeta_descarga):
            os.makedirs(self.carpeta_descarga)
            logger.info(f"📁 Carpeta creada: {self.carpeta_descarga}")
    
    def extraer_prefactura_del_asunto(self, asunto):
        """Extrae el número de prefactura del asunto del correo"""
        # Buscar patrón: "Envío de prefactura 7979536"
        match = re.search(r"prefactura\s+(\d+)", asunto, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback: buscar cualquier número de 7 dígitos
        match = re.search(r"\b\d{7}\b", asunto)
        if match:
            return match.group(0)
            
        return None
    
    def extraer_clave_determinante(self, asunto):
        """Extrae la clave determinante del asunto"""
        # Buscar patrón: "Cedis Origen 4792"
        match = re.search(r"cedis\s+origen\s+(\d{4})", asunto, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback: buscar cualquier número de 4 dígitos
        match = re.search(r"\b\d{4}\b", asunto)
        if match:
            return match.group(0)
            
        return None
    
    def convertir_fecha_formato(self, fecha_str):
        """Convierte fecha de YYYY-MM-DD a DD/MM/YYYY"""
        try:
            if not fecha_str or fecha_str == "nan":
                return datetime.now().strftime("%d/%m/%Y")
                
            # Intentar varios formatos
            formatos = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
            
            for formato in formatos:
                try:
                    fecha_obj = datetime.strptime(str(fecha_str).split()[0], formato)
                    return fecha_obj.strftime("%d/%m/%Y")
                except:
                    continue
                    
            # Si no funciona ningún formato, usar fecha actual
            logger.warning(f"⚠️ No se pudo convertir fecha: {fecha_str}, usando fecha actual")
            return datetime.now().strftime("%d/%m/%Y")
            
        except Exception as e:
            logger.error(f"❌ Error al convertir fecha: {e}")
            return datetime.now().strftime("%d/%m/%Y")
    
    def procesar_correo_individual(self, mensaje):
        """Procesa un correo individual"""
        try:
            asunto = mensaje.Subject or ""
            remitente = mensaje.SenderEmailAddress or ""
            fecha_recibido = mensaje.ReceivedTime
            
            # Filtros básicos
            if not remitente or "PreFacturacionTransportes@walmart.com" not in remitente:
                return False
                
            if "cancelado" in asunto.lower() or "no-reply" in remitente.lower():
                return False
                
            if not "prefactura" in asunto.lower():
                return False
            
            # Evitar reprocesar correos
            correo_id = f"{fecha_recibido}_{asunto}"
            if correo_id in self.correos_procesados:
                return False
                
            adjuntos = mensaje.Attachments
            if adjuntos.Count == 0:
                return False
            
            logger.info(f"📩 Procesando correo: {asunto}")
            
            # Extraer datos del asunto
            prefactura = self.extraer_prefactura_del_asunto(asunto)
            clave_determinante = self.extraer_clave_determinante(asunto)
            
            if not prefactura:
                logger.warning(f"⚠️ No se pudo extraer prefactura del asunto: {asunto}")
                return False
                
            if not clave_determinante:
                logger.warning(f"⚠️ No se pudo extraer clave determinante del asunto: {asunto}")
                return False
            
            # Procesar archivos adjuntos
            for i in range(1, adjuntos.Count + 1):
                archivo = adjuntos.Item(i)
                nombre = archivo.FileName
                
                if not nombre.endswith(".xls"):
                    continue
                
                # Generar nombre único para evitar conflictos
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_unico = f"{timestamp}_{nombre}"
                ruta_local = os.path.join(self.carpeta_descarga, nombre_unico)
                
                # Descargar archivo
                archivo.SaveAsFile(ruta_local)
                logger.info(f"📥 Archivo descargado: {ruta_local}")
                
                # Parsear archivo
                resultado = parse_xls(ruta_local, determinante_from_asunto=clave_determinante)
                
                if "error" in resultado:
                    logger.warning(f"⚠️ Archivo no válido: {resultado['error']}")
                    os.remove(ruta_local)  # Limpiar archivo inválido
                    continue
                
                # Completar datos faltantes
                resultado["prefactura"] = prefactura
                resultado["fecha"] = self.convertir_fecha_formato(resultado.get("fecha"))
                
                logger.info("✅ Viaje VACIO válido encontrado:")
                logger.info(f"   📋 Prefactura: {resultado['prefactura']}")
                logger.info(f"   📅 Fecha: {resultado['fecha']}")
                logger.info(f"   🚛 Placa Tractor: {resultado['placa_tractor']}")
                logger.info(f"   🚚 Placa Remolque: {resultado['placa_remolque']}")
                logger.info(f"   🎯 Determinante: {resultado['clave_determinante']}")
                logger.info(f"   💰 Importe: ${resultado['importe']}")
                
                # Ejecutar automatización GM
                if self.ejecutar_automatizacion_gm(resultado):
                    # Marcar correo como procesado
                    self.correos_procesados.add(correo_id)
                    
                    # Marcar correo como leído para evitar reprocesamiento
                    mensaje.UnRead = False
                    
                    # Limpiar archivo procesado
                    os.remove(ruta_local)
                    logger.info(f"🗑️ Archivo limpiado: {ruta_local}")
                    
                    return True
                else:
                    logger.error("❌ Error en automatización GM")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error al procesar correo: {e}")
            return False
            
        return False
    
    def ejecutar_automatizacion_gm(self, datos_viaje):
        """Ejecuta la automatización completa de GM Transport"""
        try:
            logger.info("🤖 Iniciando automatización GM Transport...")
            
            # Inicializar driver si no existe
            if not self.driver:
                logger.info("🔐 Realizando login en GM Transport...")
                self.driver = login_to_gm()
                
                if not self.driver:
                    logger.error("❌ Error en login GM")
                    return False
                    
                logger.info("✅ Login exitoso en GM Transport")
            
            # Crear instancia de automatización con los datos del correo
            automation = GMTransportAutomation(self.driver)
            automation.datos_viaje = datos_viaje
            
            # Ejecutar proceso completo
            resultado = automation.fill_viaje_form()
            
            if resultado:
                logger.info("🎉 Automatización GM completada exitosamente")
                return True
            else:
                logger.error("❌ Error en automatización GM")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en automatización GM: {e}")
            return False
    
    def revisar_correos_nuevos(self):
        """Revisa correos nuevos en Outlook"""
        try:
            logger.info("📬 Revisando correos nuevos...")
            
            # Conectar a Outlook
            outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            inbox = outlook.GetDefaultFolder(6)  # Bandeja de entrada
            
            # Obtener solo correos no leídos, más recientes primero
            mensajes = inbox.Items.Restrict("[UnRead] = True")
            mensajes.Sort("[ReceivedTime]", True)
            
            correos_procesados = 0
            correos_totales = mensajes.Count
            
            logger.info(f"📊 Correos no leídos encontrados: {correos_totales}")
            
            for mensaje in mensajes:
                if self.procesar_correo_individual(mensaje):
                    correos_procesados += 1
                    
                # Limitar procesamiento para evitar sobrecarga
                if correos_procesados >= 5:  # Máximo 5 correos por ciclo
                    logger.info("⚠️ Límite de procesamiento alcanzado, esperando siguiente ciclo")
                    break
            
            logger.info(f"✅ Ciclo completado: {correos_procesados} correos procesados de {correos_totales}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al revisar correos: {e}")
            return False
    
    def ejecutar_bucle_continuo(self, intervalo_minutos=5):
        """Ejecuta el sistema en bucle continuo"""
        logger.info("🚀 Iniciando sistema de automatización Alsua Transport")
        logger.info(f"⏰ Revisión cada {intervalo_minutos} minutos")
        logger.info("📧 Filtrando correos de PreFacturacionTransportes@walmart.com")
        logger.info("🎯 Procesando solo viajes tipo VACIO")
        logger.info("🤖 Automatización GM completa habilitada")
        logger.info("=" * 70)
        
        try:
            while True:
                try:
                    self.revisar_correos_nuevos()
                    
                    logger.info(f"😴 Esperando {intervalo_minutos} minutos hasta próxima revisión...")
                    time.sleep(intervalo_minutos * 60)
                    
                except KeyboardInterrupt:
                    logger.info("⚠️ Interrupción manual detectada")
                    break
                    
                except Exception as e:
                    logger.error(f"❌ Error en ciclo: {e}")
                    logger.info(f"🔄 Reintentando en {intervalo_minutos} minutos...")
                    time.sleep(intervalo_minutos * 60)
                    
        except KeyboardInterrupt:
            logger.info("🛑 Sistema detenido por usuario")
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("✅ Driver cerrado correctamente")
                except:
                    pass
                    
            logger.info("👋 Sistema de automatización finalizado")
    
    def ejecutar_revision_unica(self):
        """Ejecuta una sola revisión de correos (para pruebas)"""
        logger.info("🧪 Ejecutando revisión única de correos...")
        
        resultado = self.revisar_correos_nuevos()
        
        if self.driver:
            input("🟢 Presiona ENTER para cerrar el navegador...")
            try:
                self.driver.quit()
                logger.info("✅ Driver cerrado correctamente")
            except:
                pass
                
        return resultado

def main():
    """Función principal"""
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              ALSUA TRANSPORT - SISTEMA COMPLETO             ║
    ║                  Mail Reader + GM Automation                ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    sistema = AlsuaMailAutomation()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Modo prueba: una sola ejecución
        sistema.ejecutar_revision_unica()
    else:
        # Modo producción: bucle continuo
        try:
            intervalo = int(input("⏰ Intervalo en minutos (default 5): ") or "5")
        except ValueError:
            intervalo = 5
            
        sistema.ejecutar_bucle_continuo(intervalo)

if __name__ == "__main__":
    main()