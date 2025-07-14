#!/usr/bin/env python3
"""
Sistema completo de automatización Alsua Transport
Mail Reader → Parser → GM Automation
VERSIÓN LIMPIA: Solo usa viajes_log.csv para TODO (anti-duplicados + registros)
SIN archivos .pkl, SIN alsua_automation.log
"""

import os
import time
import logging
import re
from datetime import datetime, timedelta
import win32com.client
import pythoncom  # Para inicialización COM
from modules.parser import parse_xls
from modules.gm_login import login_to_gm
from modules.gm_transport_general import GMTransportAutomation
# SIMPLIFICADO: Solo importar sistema de log CSV
from viajes_log import registrar_viaje_fallido as log_viaje_fallido, viajes_log

# Configurar logging LIMPIO: Solo consola, SIN archivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Solo consola, NO archivo
    ]
)
logger = logging.getLogger(__name__)

class AlsuaMailAutomation:
    def __init__(self):
        # Usar ruta absoluta para evitar problemas de permisos
        self.carpeta_descarga = os.path.abspath("archivos_descargados")
        
        self.driver = None
        self.driver_corrupto = False  # Flag para trackear driver corrupto
        
        # Control de inicialización COM
        self.com_inicializado = False
        
        self._crear_carpeta_descarga()
        
    def _crear_carpeta_descarga(self):
        """Crear carpeta de descarga si no existe"""
        try:
            if not os.path.exists(self.carpeta_descarga):
                os.makedirs(self.carpeta_descarga)
                logger.info(f"📁 Carpeta creada: {self.carpeta_descarga}")
            else:
                logger.info(f"📁 Carpeta existe: {self.carpeta_descarga}")
                
            # Verificar permisos de escritura
            test_file = os.path.join(self.carpeta_descarga, "test_permisos.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                logger.info("✅ Permisos de escritura verificados")
            except Exception as e:
                logger.error(f"❌ Error de permisos en carpeta: {e}")
                # Usar carpeta alternativa
                self.carpeta_descarga = os.path.join(os.path.expanduser("~"), "Downloads", "alsua_archivos")
                os.makedirs(self.carpeta_descarga, exist_ok=True)
                logger.info(f"📁 Usando carpeta alternativa: {self.carpeta_descarga}")
                
        except Exception as e:
            logger.error(f"❌ Error al crear carpeta: {e}")
            # Fallback a carpeta del usuario
            self.carpeta_descarga = os.path.join(os.path.expanduser("~"), "Downloads", "alsua_archivos")
            os.makedirs(self.carpeta_descarga, exist_ok=True)
            logger.info(f"📁 Carpeta fallback: {self.carpeta_descarga}")
    
    # ==========================================
    # FUNCIONES COM PARA FLASK
    # ==========================================
    
    def inicializar_com(self):
        """Inicializa COM para el thread actual"""
        try:
            if not self.com_inicializado:
                logger.info("🔧 Inicializando COM para thread actual...")
                pythoncom.CoInitialize()
                self.com_inicializado = True
                logger.info("✅ COM inicializado exitosamente")
                return True
        except Exception as e:
            logger.error(f"❌ Error inicializando COM: {e}")
            return False
    
    def limpiar_com(self):
        """Limpia COM al finalizar"""
        try:
            if self.com_inicializado:
                logger.info("🧹 Limpiando inicialización COM...")
                pythoncom.CoUninitialize()
                self.com_inicializado = False
                logger.info("✅ COM limpiado exitosamente")
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando COM: {e}")
    
    # ==========================================
    # FUNCIONES ANTI-DUPLICADOS USANDO CSV
    # ==========================================
    
    def generar_id_unico_correo(self, mensaje):
        """Genera un ID único para el correo basado en múltiples factores"""
        try:
            # Usar múltiples elementos para crear ID único
            asunto = mensaje.Subject or ""
            remitente = mensaje.SenderEmailAddress or ""
            fecha_recibido = str(mensaje.ReceivedTime)
            
            # Extraer prefactura del asunto
            prefactura = self.extraer_prefactura_del_asunto(asunto)
            
            # Crear ID compuesto más robusto
            fecha_corta = fecha_recibido.split()[0] if fecha_recibido else "sin_fecha"
            id_correo = f"{prefactura}_{fecha_corta}_{abs(hash(asunto + remitente)) % 10000}"
            return id_correo
            
        except Exception as e:
            logger.warning(f"⚠️ Error generando ID de correo: {e}")
            return f"unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def generar_id_unico_viaje(self, datos_viaje):
        """Genera un ID único para el viaje"""
        prefactura = datos_viaje.get('prefactura', 'SIN_PREFACTURA')
        fecha = datos_viaje.get('fecha', 'SIN_FECHA')
        placa_tractor = datos_viaje.get('placa_tractor', 'SIN_TRACTOR')
        determinante = datos_viaje.get('clave_determinante', 'SIN_DETERMINANTE')
        
        return f"{prefactura}_{fecha}_{placa_tractor}_{determinante}"
    
    def ya_fue_procesado_correo_csv(self, mensaje):
        """NUEVO: Verifica anti-duplicados usando solo el CSV"""
        try:
            prefactura = self.extraer_prefactura_del_asunto(mensaje.Subject or "")
            if not prefactura:
                return False
            
            # Buscar en el CSV si esta prefactura ya fue procesada
            viaje_existente = viajes_log.verificar_viaje_existe(prefactura)
            
            if viaje_existente:
                logger.info(f"📧 Correo ya procesado (encontrado en CSV): {prefactura}")
                logger.info(f"   📊 Estatus en CSV: {viaje_existente.get('estatus')}")
                logger.info(f"   📅 Timestamp: {viaje_existente.get('timestamp')}")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Error verificando duplicados en CSV: {e}")
            return False
    
    def ya_fue_creado_viaje_csv(self, datos_viaje):
        """NUEVO: Verifica si este viaje ya fue creado usando solo el CSV"""
        try:
            prefactura = datos_viaje.get('prefactura')
            determinante = datos_viaje.get('clave_determinante')
            
            if not prefactura:
                return False
            
            # Buscar en el CSV
            viaje_existente = viajes_log.verificar_viaje_existe(prefactura, determinante)
            
            if viaje_existente:
                logger.info(f"🚛 Viaje ya creado (encontrado en CSV): {prefactura}")
                logger.info(f"   📊 Estatus en CSV: {viaje_existente.get('estatus')}")
                logger.info(f"   📅 Timestamp: {viaje_existente.get('timestamp')}")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Error verificando viaje en CSV: {e}")
            return False
    
    def registrar_viaje_para_revision_manual_csv(self, datos_viaje, tipo_error):
        """
        FUNCIÓN SIMPLIFICADA: Registra un viaje válido que falló SOLO en CSV
        """
        try:
            # SIMPLIFICADO: Registrar directamente en CSV sin archivo separado
            prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
            determinante = datos_viaje.get('clave_determinante', 'DESCONOCIDO')
            fecha_viaje = datos_viaje.get('fecha', '')
            placa_tractor = datos_viaje.get('placa_tractor', 'DESCONOCIDA')
            placa_remolque = datos_viaje.get('placa_remolque', 'DESCONOCIDA')
            importe = datos_viaje.get('importe', '0')
            cliente_codigo = datos_viaje.get('cliente_codigo', '')
            
            # Motivo específico para revisión manual
            motivo_fallo = f"REVISIÓN MANUAL REQUERIDA - {tipo_error}"
            
            # Registrar en CSV
            exito_csv = log_viaje_fallido(
                prefactura=prefactura,
                motivo_fallo=motivo_fallo,
                determinante=determinante,
                fecha_viaje=fecha_viaje,
                placa_tractor=placa_tractor,
                placa_remolque=placa_remolque,
                importe=importe,
                cliente_codigo=cliente_codigo
            )
            
            if exito_csv:
                logger.error("🚨 VIAJE VACIO VÁLIDO REGISTRADO PARA REVISIÓN MANUAL:")
                logger.error(f"   📋 Prefactura: {prefactura}")
                logger.error(f"   🎯 Determinante: {determinante}")
                logger.error(f"   🚛 Placas: {placa_tractor} / {placa_remolque}")
                logger.error(f"   💰 Importe: ${importe}")
                logger.error(f"   ❌ Error: {tipo_error}")
                logger.error("   🔧 ACCIÓN: Procesar manualmente en GM Transport")
                logger.error("   📊 Registrado en CSV con estatus FALLIDO")
                logger.error("🔄 MySQL se actualizará automáticamente desde CSV")
                return True
            else:
                logger.error("❌ Error registrando viaje para revisión en CSV")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error registrando viaje para revisión: {e}")
            return False
    
    # ==========================================
    # FUNCIONES PARA MANEJO DE DRIVER
    # ==========================================
    
    def verificar_driver_valido(self):
        """Verifica si el driver actual sigue siendo válido"""
        if not self.driver or self.driver_corrupto:
            return False
            
        try:
            # Intentar una operación simple para verificar que el driver funciona
            current_url = self.driver.current_url
            title = self.driver.title
            
            # Verificar que estamos en una página válida de GM Transport
            if "softwareparatransporte.com" in current_url:
                logger.info(f"✅ Driver válido - URL: {current_url[:80]}...")
                return True
            else:
                logger.warning(f"⚠️ Driver en página incorrecta: {current_url}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Driver inválido detectado: {e}")
            self.driver_corrupto = True
            return False
    
    def cerrar_driver_corrupto(self):
        """Cierra y limpia el driver corrupto"""
        try:
            if self.driver:
                logger.info("🗑️ Cerrando driver corrupto...")
                self.driver.quit()
                time.sleep(2)  # Esperar a que se cierre completamente
                logger.info("✅ Driver corrupto cerrado")
        except Exception as e:
            logger.warning(f"⚠️ Error cerrando driver corrupto: {e}")
        finally:
            self.driver = None
            self.driver_corrupto = False
    
    def inicializar_driver_nuevo(self):
        """Inicializa un nuevo driver con login"""
        try:
            logger.info("🔄 Inicializando nuevo driver...")
            
            # Asegurar que no hay driver anterior
            if self.driver:
                self.cerrar_driver_corrupto()
            
            # Crear nuevo driver con login
            self.driver = login_to_gm()
            
            if self.driver:
                self.driver_corrupto = False
                logger.info("✅ Nuevo driver inicializado exitosamente")
                return True
            else:
                logger.error("❌ Error en login GM")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error crítico inicializando driver: {e}")
            self.driver = None
            self.driver_corrupto = True
            return False
    
    def obtener_driver_valido(self):
        """Obtiene un driver válido, creando uno nuevo si es necesario"""
        # Si el driver actual es válido, usarlo
        if self.verificar_driver_valido():
            return True
        
        # Si no es válido, crear uno nuevo
        logger.info("🔄 Driver no válido, creando uno nuevo...")
        return self.inicializar_driver_nuevo()
    
    # ==========================================
    # FUNCIONES PRINCIPALES SIMPLIFICADAS
    # ==========================================
    
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
        """
        FUNCIÓN LIMPIA: Procesa un correo individual usando solo CSV para anti-duplicados
        """
        try:
            # ===== VERIFICACIÓN ANTI-DUPLICADOS USANDO CSV =====
            if self.ya_fue_procesado_correo_csv(mensaje):
                logger.info("⏭️ Saltando correo ya procesado (encontrado en CSV)")
                mensaje.UnRead = False
                return False
            
            asunto = mensaje.Subject or ""
            remitente = mensaje.SenderEmailAddress or ""
            fecha_recibido = mensaje.ReceivedTime
            
            # ===== FILTROS BÁSICOS (marcar como leído si no pasan) =====
            if not remitente or "PreFacturacionTransportes@walmart.com" not in remitente:
                return False
                
            if "cancelado" in asunto.lower() or "no-reply" in remitente.lower():
                # Estos no son viajes válidos - marcar como leído
                mensaje.UnRead = False
                return False
                
            if not "prefactura" in asunto.lower():
                # No es un correo de prefactura - marcar como leído
                mensaje.UnRead = False
                return False
            
            adjuntos = mensaje.Attachments
            if adjuntos.Count == 0:
                # No tiene archivos - marcar como leído
                mensaje.UnRead = False
                return False
            
            logger.info(f"📩 Procesando correo NUEVO: {asunto}")
            
            # ===== EXTRAER DATOS CRÍTICOS =====
            prefactura = self.extraer_prefactura_del_asunto(asunto)
            clave_determinante = self.extraer_clave_determinante(asunto)
            
            if not prefactura:
                logger.warning(f"⚠️ No se pudo extraer prefactura del asunto: {asunto}")
                # ERROR TÉCNICO - marcar como leído para evitar bucle
                mensaje.UnRead = False
                return False
                
            if not clave_determinante:
                logger.warning(f"⚠️ No se pudo extraer clave determinante del asunto: {asunto}")
                # ERROR TÉCNICO - marcar como leído para evitar bucle
                mensaje.UnRead = False
                return False
            
            # ===== PROCESAR ARCHIVOS ADJUNTOS =====
            for i in range(1, adjuntos.Count + 1):
                archivo = adjuntos.Item(i)
                nombre = archivo.FileName
                
                if not nombre.endswith(".xls"):
                    continue
                
                # Generar nombre único
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_unico = f"{timestamp}_{nombre}"
                ruta_local = os.path.join(self.carpeta_descarga, nombre_unico)
                
                # ===== DESCARGAR ARCHIVO =====
                try:
                    archivo.SaveAsFile(ruta_local)
                    logger.info(f"📥 Archivo descargado: {ruta_local}")
                except Exception as e:
                    logger.error(f"❌ Error al descargar archivo {nombre}: {e}")
                    # ERROR TÉCNICO - marcar como leído
                    mensaje.UnRead = False
                    continue
                
                # ===== PARSEAR ARCHIVO =====
                resultado = parse_xls(ruta_local, determinante_from_asunto=clave_determinante)
                
                if "error" in resultado:
                    logger.warning(f"⚠️ Archivo no válido: {resultado['error']}")
                    os.remove(ruta_local)
                    
                    # Verificar si es porque NO ES TIPO VACIO
                    if "no es tipo VACIO" in resultado['error']:
                        logger.info("📄 Correo válido pero viaje no es tipo VACIO - marcando como leído")
                        mensaje.UnRead = False
                        return False
                    else:
                        # ERROR TÉCNICO (archivo corrupto, etc) - marcar como leído
                        mensaje.UnRead = False
                        continue
                
                # ===== COMPLETAR DATOS =====
                resultado["prefactura"] = prefactura
                resultado["fecha"] = self.convertir_fecha_formato(resultado.get("fecha"))
                
                # ===== VERIFICAR DUPLICADOS USANDO CSV =====
                if self.ya_fue_creado_viaje_csv(resultado):
                    logger.info("⏭️ Saltando viaje ya creado (encontrado en CSV)")
                    mensaje.UnRead = False
                    os.remove(ruta_local)
                    return False
                
                # ===== VIAJE VACIO VÁLIDO DETECTADO =====
                logger.info("✅ Viaje VACIO válido encontrado:")
                logger.info(f"   📋 Prefactura: {resultado['prefactura']}")
                logger.info(f"   📅 Fecha: {resultado['fecha']}")
                logger.info(f"   🚛 Placa Tractor: {resultado['placa_tractor']}")
                logger.info(f"   🚚 Placa Remolque: {resultado['placa_remolque']}")
                logger.info(f"   🎯 Determinante: {resultado['clave_determinante']}")
                logger.info(f"   💰 Importe: ${resultado['importe']}")
                
                # ===== EJECUTAR AUTOMATIZACIÓN GM =====
                resultado_gm = self.ejecutar_automatizacion_gm(resultado)
                
                if resultado_gm == "OPERADOR_OCUPADO":
                    # 🚨 OPERADOR OCUPADO - MARCAR CORREO COMO LEÍDO PARA EVITAR CICLO
                    logger.warning("🚨 OPERADOR OCUPADO: Error registrado en CSV")
                    logger.info("📧 MARCANDO correo como leído para evitar reprocesamiento en bucle")
                    logger.info("🔄 MySQL se actualizará automáticamente desde CSV")
                    
                    # Marcar como leído
                    mensaje.UnRead = False
                    
                    # Limpiar archivo Excel
                    os.remove(ruta_local)
                    logger.info(f"🗑️ Archivo limpiado: {ruta_local}")
                    
                    return "OPERADOR_OCUPADO"
                    
                elif resultado_gm == "DRIVER_CORRUPTO":
                    # 🚨 DRIVER CORRUPTO - NO MARCAR COMO PROCESADO PARA PERMITIR REINTENTO
                    logger.error("🚨 DRIVER CORRUPTO: Fallo en navegación GM Transport")
                    logger.info("🔄 NO marcando correo como procesado - se reintentará en próximo ciclo")
                    logger.info("📧 Correo permanecerá como no leído para reintento automático")
                    
                    # NO marcar como leído - mantener como no leído
                    
                    # Limpiar archivo Excel ya que se volverá a descargar
                    os.remove(ruta_local)
                    logger.info(f"🗑️ Archivo limpiado para reintento: {ruta_local}")
                    
                    return "DRIVER_CORRUPTO"
                    
                elif resultado_gm:
                    # ✅ ÉXITO COMPLETO - EL REGISTRO SE HIZO EN CSV
                    logger.info("🎉 VIAJE EXITOSO COMPLETADO")
                    logger.info("📊 Datos completos (UUID, Viaje GM, placas) registrados en CSV")
                    logger.info("🔄 MySQL se sincronizará automáticamente desde CSV")
                    
                    mensaje.UnRead = False
                    os.remove(ruta_local)
                    logger.info(f"🗑️ Archivo limpiado: {ruta_local}")
                    return True
                else:
                    # ❌ FALLO EN GM - REGISTRAR EN CSV
                    logger.error("❌ VIAJE VACIO VÁLIDO FALLÓ EN GM TRANSPORT")
                    logger.error("🚨 REQUIERE REVISIÓN MANUAL URGENTE")
                    
                    # SIMPLIFICADO: REGISTRAR PARA REVISIÓN MANUAL EN CSV
                    self.registrar_viaje_para_revision_manual_csv(resultado, "ERROR_GM_AUTOMATION")
                    
                    # Conservar archivo para revisión
                    logger.error(f"📋 Archivo conservado para revisión: {ruta_local}")
                    
                    # Marcar como leído para evitar bucle infinito
                    mensaje.UnRead = False
                    
                    return False
                    
        except KeyboardInterrupt:
            # El usuario detuvo manualmente - no marcar como leído
            logger.info("⚠️ Interrupción manual - no marcando correo como leído")
            raise
            
        except Exception as e:
            logger.error(f"❌ Error inesperado al procesar correo: {e}")
            # ERROR TÉCNICO INESPERADO - marcar como leído para evitar bucle
            try:
                mensaje.UnRead = False
            except:
                pass
            return False
            
        return False
    
    def ejecutar_automatizacion_gm(self, datos_viaje):
        """
        FUNCIÓN SIMPLIFICADA: Ejecuta la automatización completa de GM Transport
        Todos los registros se hacen en CSV, MySQL se sincroniza automáticamente
        """
        try:
            logger.info("🤖 Iniciando automatización GM Transport...")
            
            # PASO 1: VERIFICAR/OBTENER DRIVER VÁLIDO
            if not self.obtener_driver_valido():
                logger.error("❌ No se pudo obtener driver válido para GM Transport")
                # Marcar como corrupto para forzar reinicio en próximo intento
                self.driver_corrupto = True
                return "DRIVER_CORRUPTO"
            
            # PASO 2: CREAR INSTANCIA DE AUTOMATIZACIÓN
            try:
                automation = GMTransportAutomation(self.driver)
                automation.datos_viaje = datos_viaje
                
                # PASO 3: EJECUTAR PROCESO COMPLETO CON MANEJO DE ERRORES
                logger.info("🚀 Ejecutando proceso completo de GM Transport...")
                resultado = automation.fill_viaje_form()
                
                if resultado == "OPERADOR_OCUPADO":
                    # El navegador ya fue cerrado en gm_salida.py
                    logger.warning("🚨 Operador ocupado detectado")
                    logger.info("📝 Error ya registrado en CSV")
                    logger.info("🔄 MySQL se actualizará automáticamente desde CSV")
                    # Marcar driver como corrupto para forzar nuevo login
                    self.driver = None
                    self.driver_corrupto = True
                    return "OPERADOR_OCUPADO"
                    
                elif resultado:
                    logger.info("🎉 Automatización GM completada exitosamente")
                    logger.info("📊 Datos completos registrados en CSV")
                    logger.info("🔄 MySQL se sincronizará automáticamente desde CSV")
                    # Driver sigue siendo válido
                    return True
                else:
                    logger.error("❌ Error en automatización GM")
                    # Verificar si el driver sigue siendo válido después del error
                    if not self.verificar_driver_valido():
                        logger.warning("⚠️ Driver corrupto después del error")
                        self.cerrar_driver_corrupto()
                        return "DRIVER_CORRUPTO"
                    return False
                    
            except Exception as automation_error:
                logger.error(f"❌ Error durante automatización: {automation_error}")
                
                # Verificar si el error fue por driver corrupto
                if any(keyword in str(automation_error).lower() for keyword in 
                       ['invalid session', 'chrome not reachable', 'no such window', 'session deleted']):
                    logger.error("🚨 Error detectado como driver corrupto")
                    self.cerrar_driver_corrupto()
                    return "DRIVER_CORRUPTO"
                else:
                    # Error general - verificar si driver sigue válido
                    if not self.verificar_driver_valido():
                        logger.warning("⚠️ Driver corrupto después del error general")
                        self.cerrar_driver_corrupto()
                        return "DRIVER_CORRUPTO"
                    return False
                
        except Exception as e:
            logger.error(f"❌ Error general en automatización GM: {e}")
            # En caso de error general, asumir que el driver está corrupto
            self.cerrar_driver_corrupto()
            return "DRIVER_CORRUPTO"
    
    def revisar_correos_nuevos(self, modo_test=False):
        """
        FUNCIÓN LIMPIA: Revisa correos nuevos usando solo CSV para anti-duplicados
        """
        try:
            # INICIALIZAR COM PARA FLASK
            if not self.inicializar_com():
                logger.error("❌ No se pudo inicializar COM - aborting")
                return False
            
            logger.info("📬 Revisando correos nuevos...")
            if modo_test:
                logger.info("🧪 MODO TEST: Pausará después de cada viaje para inspección")
            
            # Conectar a Outlook CON COM INICIALIZADO
            try:
                outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
                inbox = outlook.GetDefaultFolder(6)  # Bandeja de entrada
                logger.info("✅ Conexión a Outlook establecida exitosamente")
            except Exception as e:
                logger.error(f"❌ Error conectando a Outlook: {e}")
                return False
            
            # Obtener solo correos no leídos, más recientes primero
            mensajes = inbox.Items.Restrict("[UnRead] = True")
            mensajes.Sort("[ReceivedTime]", True)
            
            correos_procesados = 0
            correos_totales = mensajes.Count
            correos_saltados = 0
            operadores_ocupados = 0
            drivers_corruptos = 0
            reintentos_pendientes = 0
            
            logger.info(f"📊 Correos no leídos encontrados: {correos_totales}")
            
            # Obtener estadísticas del CSV para mostrar estado actual
            try:
                stats_csv = viajes_log.obtener_estadisticas()
                logger.info(f"📊 Estado actual CSV: {stats_csv['total_viajes']} viajes total")
                logger.info(f"📊 Exitosos: {stats_csv['exitosos']}, Fallidos: {stats_csv['fallidos']}")
            except:
                logger.info("📊 Estado CSV: No disponible")
            
            for mensaje in mensajes:
                try:
                    # Verificación rápida para saltear correos obvios
                    remitente = mensaje.SenderEmailAddress or ""
                    if "PreFacturacionTransportes@walmart.com" not in remitente:
                        continue
                    
                    # Extraer prefactura para logging
                    asunto = mensaje.Subject or ""
                    prefactura = self.extraer_prefactura_del_asunto(asunto)
                    
                    logger.info(f"🚀 Procesando viaje: {prefactura}")
                    resultado_procesamiento = self.procesar_correo_individual(mensaje)
                    
                    if resultado_procesamiento == "OPERADOR_OCUPADO":
                        operadores_ocupados += 1
                        logger.warning(f"🚨 Viaje {prefactura} con operador ocupado - registrado en CSV")
                        logger.info("🔄 MySQL se actualizará automáticamente desde CSV")
                        
                        # PAUSA EN MODO TEST
                        if modo_test:
                            input(f"🚨 OPERADOR OCUPADO en viaje {prefactura}. Presiona ENTER para continuar...")
                        else:
                            time.sleep(3)
                            
                    elif resultado_procesamiento == "DRIVER_CORRUPTO":
                        drivers_corruptos += 1
                        reintentos_pendientes += 1
                        logger.error(f"🚨 Viaje {prefactura} con driver corrupto - se reintentará automáticamente")
                        
                        # PAUSA EN MODO TEST
                        if modo_test:
                            input(f"🔧 DRIVER CORRUPTO en viaje {prefactura}. NO marcado como procesado - se reintentará. Presiona ENTER para continuar...")
                        else:
                            time.sleep(5)
                            
                    elif resultado_procesamiento:
                        correos_procesados += 1
                        logger.info(f"✅ Viaje {prefactura} completado exitosamente")
                        logger.info("📊 Todos los datos registrados en CSV")
                        logger.info("🔄 MySQL se sincronizará automáticamente desde CSV")
                        
                        # PAUSA EN MODO TEST
                        if modo_test:
                            input(f"✅ VIAJE EXITOSO {prefactura}. Presiona ENTER para continuar...")
                        else:
                            time.sleep(2)
                    else:
                        correos_saltados += 1
                        
                        # PAUSA EN MODO TEST SOLO SI ES UN ERROR QUE REQUIERE ATENCIÓN
                        if modo_test and "ERROR_GM_AUTOMATION" in str(resultado_procesamiento):
                            input(f"❌ ERROR EN VIAJE {prefactura} - requiere revisión manual. Presiona ENTER para continuar...")
                        
                    # Limitar procesamiento para evitar sobrecarga (excepto en modo test)
                    if not modo_test and correos_procesados >= 3:
                        logger.info("⚠️ Límite de procesamiento alcanzado, esperando siguiente ciclo")
                        break
                    
                    # Si hay muchos errores de driver, parar para evitar bucle (excepto en modo test)
                    if not modo_test and drivers_corruptos >= 2:
                        logger.warning("🚨 Múltiples errores de driver detectados - pausando ciclo")
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje individual: {e}")
                    correos_saltados += 1
                    
                    # PAUSA EN MODO TEST PARA ERRORES INESPERADOS
                    if modo_test:
                        input(f"❌ ERROR INESPERADO procesando correo. Presiona ENTER para continuar...")
                    continue
            
            logger.info(f"✅ Ciclo completado:")
            logger.info(f"   📧 Total correos revisados: {correos_totales}")
            logger.info(f"   ✅ Correos procesados: {correos_procesados}")
            logger.info(f"   ⏭️ Correos saltados: {correos_saltados}")
            logger.info(f"   🚨 Operadores ocupados: {operadores_ocupados}")
            logger.info(f"   🔧 Drivers corruptos: {drivers_corruptos}")
            logger.info(f"   🔄 Reintentos pendientes: {reintentos_pendientes}")
            logger.info("📊 IMPORTANTE: Todos los registros están en CSV ÚNICAMENTE")
            logger.info("🔄 MySQL se sincronizará automáticamente desde CSV")
            
            if operadores_ocupados > 0:
                logger.info("📝 Los errores de operador ocupado fueron registrados en CSV")
                logger.info("🔧 Estos viajes requieren revisión manual")
            
            if drivers_corruptos > 0:
                logger.warning("🚨 Errores de driver corrupto detectados")
                logger.warning("🔄 Estos correos NO fueron marcados como procesados - se reintentarán automáticamente")
                logger.warning("💡 Si persisten, considera verificar la configuración del navegador")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al revisar correos: {e}")
            return False
        finally:
            # LIMPIAR COM AL FINALIZAR
            self.limpiar_com()
    
    def ejecutar_bucle_continuo(self, intervalo_minutos=5):
        """FUNCIÓN LIMPIA: Ejecuta el sistema en bucle continuo usando solo CSV"""
        logger.info("🚀 Iniciando sistema de automatización Alsua Transport v5.0 LIMPIO")
        logger.info("🛡️ PROTECCIÓN ANTI-DUPLICADOS USANDO SOLO CSV")
        logger.info("📊 REGISTRO UNIFICADO EN CSV ÚNICAMENTE")
        logger.info("🔄 SINCRONIZACIÓN AUTOMÁTICA CON MySQL")
        logger.info("🔧 MANEJO ROBUSTO DE DRIVER CORRUPTO")
        logger.info("🌐 COMPATIBLE CON FLASK Y THREADING")
        logger.info("🚫 SIN archivos .pkl")
        logger.info("🚫 SIN alsua_automation.log")
        logger.info("✅ SOLO viajes_log.csv")
        logger.info(f"⏰ Revisión cada {intervalo_minutos} minutos")
        logger.info("📧 Filtrando correos de PreFacturacionTransportes@walmart.com")
        logger.info("🎯 Procesando solo viajes tipo VACIO")
        logger.info("🤖 Automatización GM completa habilitada")
        logger.info("📊 Datos completos: UUID, Viaje GM, placas, fecha, prefactura")
        logger.info("🔧 Errores marcados para revisión manual")
        logger.info("💾 CSV → mysql_simple.py → MySQL (automático)")
        logger.info("=" * 70)
        
        try:
            while True:
                try:
                    self.revisar_correos_nuevos(modo_test=False)
                    
                    logger.info(f"😴 Esperando {intervalo_minutos} minutos hasta próxima revisión...")
                    time.sleep(intervalo_minutos * 60)
                    
                except KeyboardInterrupt:
                    logger.info("⚠️ Interrupción manual detectada")
                    break
                    
                except Exception as e:
                    logger.error(f"❌ Error en ciclo: {e}")
                    # Cerrar driver corrupto en caso de error grave
                    if self.driver:
                        try:
                            self.cerrar_driver_corrupto()
                        except:
                            pass
                    logger.info(f"🔄 Reintentando en {intervalo_minutos} minutos...")
                    time.sleep(intervalo_minutos * 60)
                    
        except KeyboardInterrupt:
            logger.info("🛑 Sistema detenido por usuario")
            
        finally:
            # Cerrar driver si existe
            if self.driver:
                try:
                    self.cerrar_driver_corrupto()
                except:
                    pass
            
            # LIMPIAR COM AL FINALIZAR
            self.limpiar_com()
            
            logger.info("👋 Sistema de automatización finalizado")
    
    def ejecutar_revision_unica(self):
        """FUNCIÓN LIMPIA: Ejecuta una sola revisión de correos (para pruebas)"""
        logger.info("🧪 Ejecutando revisión única de correos...")
        logger.info("⏸️ MODO TEST: Se pausará después de cada viaje esperando tu confirmación")
        logger.info("📊 Todos los registros se harán SOLO en CSV")
        logger.info("🔄 MySQL se sincronizará automáticamente desde CSV")
        
        resultado = self.revisar_correos_nuevos(modo_test=True)
        
        if self.driver:
            logger.info("🔍 MODO DEBUG: El navegador permanecerá abierto para inspección final...")
            input("🟢 Presiona ENTER para cerrar el navegador y finalizar la sesión de prueba...")
            try:
                self.cerrar_driver_corrupto()
            except:
                pass
                
        return resultado
    
    def mostrar_estadisticas(self):
        """FUNCIÓN LIMPIA: Muestra estadísticas del sistema usando solo CSV"""
        logger.info("📊 ESTADÍSTICAS DEL SISTEMA LIMPIO:")
        logger.info("   🚫 NO usa archivos .pkl")
        logger.info("   🚫 NO usa alsua_automation.log")
        logger.info("   ✅ SOLO usa viajes_log.csv")
        logger.info("   🔄 Sincronización MySQL: Automática")
        
        # Mostrar estadísticas del CSV
        try:
            stats = viajes_log.obtener_estadisticas()
            logger.info(f"   📊 Total viajes en CSV: {stats['total_viajes']}")
            logger.info(f"   ✅ Exitosos: {stats['exitosos']}")
            logger.info(f"   ❌ Fallidos: {stats['fallidos']}")
            if stats['ultimo_viaje']:
                logger.info(f"   📅 Último viaje: {stats['ultimo_viaje']}")
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo estadísticas CSV: {e}")

def main():
    """Función principal"""
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           ALSUA TRANSPORT - SISTEMA LIMPIO v5.0             ║
    ║               Mail Reader + GM Automation                    ║
    ║               🛡️ PROTECCIÓN ANTI-DUPLICADOS                  ║
    ║               📊 REGISTRO UNIFICADO EN CSV ÚNICAMENTE        ║
    ║               🔄 SINCRONIZACIÓN AUTOMÁTICA MySQL             ║
    ║               🔧 MANEJO ROBUSTO DE DRIVER CORRUPTO           ║
    ║               🚫 SIN archivos .pkl                           ║
    ║               🚫 SIN alsua_automation.log                    ║
    ║               ✅ SOLO viajes_log.csv                         ║
    ║               💾 CSV → mysql_simple.py → MySQL               ║
    ║               🌐 COMPATIBLE CON FLASK                        ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    sistema = AlsuaMailAutomation()
    
    # Mostrar estadísticas iniciales
    sistema.mostrar_estadisticas()
    
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