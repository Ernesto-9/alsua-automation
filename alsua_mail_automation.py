#!/usr/bin/env python3
"""
Sistema completo de automatización Alsua Transport
Mail Reader → Parser → GM Automation
VERSIÓN FINAL CON PROTECCIÓN ANTI-DUPLICADOS Y MANEJO DE OPERADOR OCUPADO
"""

import os
import time
import logging
import re
import pickle
from datetime import datetime, timedelta
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
        # Usar ruta absoluta para evitar problemas de permisos
        self.carpeta_descarga = os.path.abspath("archivos_descargados")
        
        # NUEVO: Archivos persistentes para tracking de duplicados
        self.archivo_procesados = "correos_procesados.pkl"
        self.archivo_viajes_creados = "viajes_creados.pkl"
        
        # Cargar tracking desde archivos
        self.correos_procesados = self.cargar_correos_procesados()
        self.viajes_creados = self.cargar_viajes_creados()
        
        self.driver = None
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
    # FUNCIONES ANTI-DUPLICADOS
    # ==========================================
    
    def cargar_correos_procesados(self):
        """Carga la lista de correos ya procesados desde archivo"""
        try:
            if os.path.exists(self.archivo_procesados):
                with open(self.archivo_procesados, 'rb') as f:
                    correos = pickle.load(f)
                    # Limpiar correos antiguos (más de 30 días)
                    cutoff_date = datetime.now() - timedelta(days=30)
                    correos_validos = {k: v for k, v in correos.items() 
                                     if v.get('fecha_procesado', datetime.now()) > cutoff_date}
                    logger.info(f"📁 Cargados {len(correos_validos)} correos procesados")
                    return correos_validos
        except Exception as e:
            logger.warning(f"⚠️ Error cargando correos procesados: {e}")
        return {}
    
    def guardar_correos_procesados(self):
        """Guarda la lista de correos procesados en archivo"""
        try:
            with open(self.archivo_procesados, 'wb') as f:
                pickle.dump(self.correos_procesados, f)
        except Exception as e:
            logger.warning(f"⚠️ Error guardando correos procesados: {e}")
    
    def cargar_viajes_creados(self):
        """Carga la lista de viajes ya creados desde archivo"""
        try:
            if os.path.exists(self.archivo_viajes_creados):
                with open(self.archivo_viajes_creados, 'rb') as f:
                    viajes = pickle.load(f)
                    # Limpiar viajes antiguos (más de 15 días)
                    cutoff_date = datetime.now() - timedelta(days=15)
                    viajes_validos = {k: v for k, v in viajes.items() 
                                    if v.get('fecha_creado', datetime.now()) > cutoff_date}
                    logger.info(f"🚛 Cargados {len(viajes_validos)} viajes creados")
                    return viajes_validos
        except Exception as e:
            logger.warning(f"⚠️ Error cargando viajes creados: {e}")
        return {}
    
    def guardar_viajes_creados(self):
        """Guarda la lista de viajes creados en archivo"""
        try:
            with open(self.archivo_viajes_creados, 'wb') as f:
                pickle.dump(self.viajes_creados, f)
        except Exception as e:
            logger.warning(f"⚠️ Error guardando viajes creados: {e}")
    
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
    
    def ya_fue_procesado_correo(self, mensaje):
        """Verifica si este correo específico ya fue procesado"""
        id_correo = self.generar_id_unico_correo(mensaje)
        
        if id_correo in self.correos_procesados:
            info_procesado = self.correos_procesados[id_correo]
            logger.info(f"📧 Correo ya procesado: {id_correo}")
            logger.info(f"   📅 Fecha procesado: {info_procesado.get('fecha_procesado')}")
            logger.info(f"   ✅ Estado: {info_procesado.get('estado', 'COMPLETADO')}")
            return True
        
        return False
    
    def ya_fue_creado_viaje(self, datos_viaje):
        """Verifica si este viaje específico ya fue creado"""
        id_viaje = self.generar_id_unico_viaje(datos_viaje)
        
        if id_viaje in self.viajes_creados:
            info_creado = self.viajes_creados[id_viaje]
            logger.info(f"🚛 Viaje ya creado: {id_viaje}")
            logger.info(f"   📅 Fecha creado: {info_creado.get('fecha_creado')}")
            logger.info(f"   ✅ Estado: {info_creado.get('estado', 'COMPLETADO')}")
            return True
        
        return False
    
    def marcar_correo_procesado(self, mensaje, estado="COMPLETADO"):
        """Marca un correo como procesado"""
        id_correo = self.generar_id_unico_correo(mensaje)
        
        self.correos_procesados[id_correo] = {
            'fecha_procesado': datetime.now(),
            'estado': estado,
            'prefactura': self.extraer_prefactura_del_asunto(mensaje.Subject or ""),
            'asunto': mensaje.Subject or "",
            'remitente': mensaje.SenderEmailAddress or ""
        }
        
        self.guardar_correos_procesados()
        logger.info(f"✅ Correo marcado como procesado: {id_correo} | Estado: {estado}")
    
    def marcar_viaje_creado(self, datos_viaje, estado="COMPLETADO"):
        """Marca un viaje como creado"""
        id_viaje = self.generar_id_unico_viaje(datos_viaje)
        
        self.viajes_creados[id_viaje] = {
            'fecha_creado': datetime.now(),
            'estado': estado,
            'datos': datos_viaje.copy()
        }
        
        self.guardar_viajes_creados()
        logger.info(f"✅ Viaje marcado como creado: {id_viaje} | Estado: {estado}")
    
    def limpiar_archivos_antiguos(self):
        """Limpia archivos de tracking antiguos"""
        try:
            # Limpiar correos procesados antiguos
            correos_originales = len(self.correos_procesados)
            self.correos_procesados = self.cargar_correos_procesados()
            correos_finales = len(self.correos_procesados)
            
            if correos_originales != correos_finales:
                self.guardar_correos_procesados()
                logger.info(f"🧹 Correos limpiados: {correos_originales} → {correos_finales}")
            
            # Limpiar viajes creados antiguos
            viajes_originales = len(self.viajes_creados)
            self.viajes_creados = self.cargar_viajes_creados()
            viajes_finales = len(self.viajes_creados)
            
            if viajes_originales != viajes_finales:
                self.guardar_viajes_creados()
                logger.info(f"🧹 Viajes limpiados: {viajes_originales} → {viajes_finales}")
                
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando archivos: {e}")
    
    def registrar_viaje_para_revision_manual(self, datos_viaje, tipo_error):
        """Registra un viaje válido que falló para revisión manual urgente"""
        try:
            # Archivo especial para viajes que NECESITAN revisión manual
            archivo_revision = "viajes_requieren_revision.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
            placa_tractor = datos_viaje.get('placa_tractor', 'DESCONOCIDA')
            placa_remolque = datos_viaje.get('placa_remolque', 'DESCONOCIDA')
            determinante = datos_viaje.get('clave_determinante', 'DESCONOCIDO')
            importe = datos_viaje.get('importe', '0')
            
            # Log crítico para operadores
            logger.error("🚨" * 20)
            logger.error("🚨 VIAJE VACIO VÁLIDO REQUIERE REVISIÓN MANUAL")
            logger.error(f"🚨 PREFACTURA: {prefactura}")
            logger.error(f"🚨 PLACA TRACTOR: {placa_tractor}")
            logger.error(f"🚨 PLACA REMOLQUE: {placa_remolque}")
            logger.error(f"🚨 DETERMINANTE: {determinante}")
            logger.error(f"🚨 IMPORTE: ${importe}")
            logger.error(f"🚨 ERROR: {tipo_error}")
            logger.error("🚨 ACCIÓN: Procesar manualmente en GM Transport")
            logger.error("🚨" * 20)
            
            # Guardar en archivo especial
            with open(archivo_revision, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp}|URGENTE|{prefactura}|{placa_tractor}|{placa_remolque}|{determinante}|{importe}|{tipo_error}\n")
            
            logger.error(f"📝 Viaje registrado en: {archivo_revision}")
            
        except Exception as e:
            logger.error(f"❌ Error registrando viaje para revisión: {e}")
    
    # ==========================================
    # FUNCIONES PRINCIPALES
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
        """Procesa un correo individual - MANEJO INTELIGENTE DE ERRORES"""
        try:
            # ===== VERIFICACIÓN ANTI-DUPLICADOS =====
            if self.ya_fue_procesado_correo(mensaje):
                logger.info("⏭️ Saltando correo ya procesado")
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
                self.marcar_correo_procesado(mensaje, "ERROR_SIN_PREFACTURA")
                mensaje.UnRead = False
                return False
                
            if not clave_determinante:
                logger.warning(f"⚠️ No se pudo extraer clave determinante del asunto: {asunto}")
                # ERROR TÉCNICO - marcar como leído para evitar bucle
                self.marcar_correo_procesado(mensaje, "ERROR_SIN_DETERMINANTE")
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
                    self.marcar_correo_procesado(mensaje, "ERROR_DESCARGA_ARCHIVO")
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
                        self.marcar_correo_procesado(mensaje, "VIAJE_NO_VACIO")
                        mensaje.UnRead = False
                        return False
                    else:
                        # ERROR TÉCNICO (archivo corrupto, etc) - marcar como leído
                        self.marcar_correo_procesado(mensaje, f"ERROR_PARSE: {resultado['error']}")
                        mensaje.UnRead = False
                        continue
                
                # ===== COMPLETAR DATOS =====
                resultado["prefactura"] = prefactura
                resultado["fecha"] = self.convertir_fecha_formato(resultado.get("fecha"))
                
                # ===== VERIFICAR DUPLICADOS =====
                if self.ya_fue_creado_viaje(resultado):
                    logger.info("⏭️ Saltando viaje ya creado en GM Transport")
                    self.marcar_correo_procesado(mensaje, "VIAJE_YA_EXISTE")
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
                    logger.warning("🚨 OPERADOR OCUPADO: Error registrado en MySQL")
                    logger.info("📧 MARCANDO correo como leído para evitar reprocesamiento en bucle")
                    
                    # MARCAR como procesado para evitar ciclo infinito
                    self.marcar_correo_procesado(mensaje, "ERROR_OPERADOR_OCUPADO")
                    mensaje.UnRead = False  # Marcar como leído
                    
                    # Limpiar archivo Excel
                    os.remove(ruta_local)
                    logger.info(f"🗑️ Archivo limpiado: {ruta_local}")
                    
                    return "OPERADOR_OCUPADO"
                    
                elif resultado_gm:
                    # ✅ ÉXITO COMPLETO - REGISTRAR EN MYSQL
                    try:
                        from modules.mysql_simple import registrar_viaje_exitoso
                        registrar_viaje_exitoso(resultado['prefactura'], resultado['fecha'])
                    except Exception as e:
                        logger.warning(f"⚠️ Error registrando viaje exitoso en MySQL: {e}")
                    
                    self.marcar_correo_procesado(mensaje, "COMPLETADO")
                    self.marcar_viaje_creado(resultado, "COMPLETADO")
                    mensaje.UnRead = False
                    os.remove(ruta_local)
                    logger.info(f"🗑️ Archivo limpiado: {ruta_local}")
                    return True
                else:
                    # ❌ FALLO EN GM - REGISTRAR EN MYSQL
                    try:
                        from modules.mysql_simple import registrar_viaje_fallido
                        motivo_fallo = "Error general en automatización GM Transport"
                        registrar_viaje_fallido(resultado['prefactura'], resultado['fecha'], motivo_fallo)
                    except Exception as e:
                        logger.warning(f"⚠️ Error registrando viaje fallido en MySQL: {e}")
                    
                    logger.error("❌ VIAJE VACIO VÁLIDO FALLÓ EN GM TRANSPORT")
                    logger.error("🚨 REQUIERE REVISIÓN MANUAL URGENTE")
                    
                    # REGISTRAR PARA REVISIÓN MANUAL
                    self.registrar_viaje_para_revision_manual(resultado, "ERROR_GM_AUTOMATION")
                    
                    # Conservar archivo para revisión
                    logger.error(f"📋 Archivo conservado para revisión: {ruta_local}")
                    
                    # Marcar como leído para evitar bucle infinito
                    self.marcar_correo_procesado(mensaje, "ERROR_GM_NECESITA_REVISION")
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
                self.marcar_correo_procesado(mensaje, "ERROR_PROCESAMIENTO_INESPERADO")
                mensaje.UnRead = False
            except:
                pass
            return False
            
        return False
    
    def ejecutar_automatizacion_gm(self, datos_viaje):
        """Ejecuta la automatización completa de GM Transport - CON MANEJO DE OPERADOR OCUPADO"""
        try:
            logger.info("🤖 Iniciando automatización GM Transport...")
            
            # Verificar si el driver sigue activo
            driver_valido = False
            if self.driver:
                try:
                    # Intentar una operación simple para verificar que el driver funciona
                    self.driver.current_url
                    driver_valido = True
                    logger.info("✅ Driver existente válido")
                except Exception as e:
                    logger.warning(f"⚠️ Driver existente inválido: {e}")
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
            
            # Inicializar driver si no existe o falló
            if not driver_valido:
                logger.info("🔐 Realizando nuevo login en GM Transport...")
                try:
                    self.driver = login_to_gm()
                    
                    if not self.driver:
                        logger.error("❌ Error en login GM")
                        return False
                        
                    logger.info("✅ Login exitoso en GM Transport")
                except Exception as e:
                    logger.error(f"❌ Error crítico en login: {e}")
                    return False
            
            # Crear instancia de automatización con los datos del correo
            try:
                automation = GMTransportAutomation(self.driver)
                automation.datos_viaje = datos_viaje
                
                # Ejecutar proceso completo
                resultado = automation.fill_viaje_form()
                
                if resultado == "OPERADOR_OCUPADO":
                    # El navegador ya fue cerrado en gm_salida.py
                    logger.warning("🚨 Operador ocupado detectado")
                    logger.info("📝 Error ya registrado en MySQL")
                    self.driver = None  # Marcar driver como inválido
                    return "OPERADOR_OCUPADO"
                    
                elif resultado:
                    logger.info("🎉 Automatización GM completada exitosamente")
                    return True
                else:
                    logger.error("❌ Error en automatización GM")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error durante automatización: {e}")
                # Si hay error, intentar cerrar driver corrupto
                try:
                    if self.driver:
                        self.driver.quit()
                        self.driver = None
                        logger.info("🗑️ Driver corrupto cerrado")
                except:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"❌ Error general en automatización GM: {e}")
            return False
    
    def revisar_correos_nuevos(self):
        """Revisa correos nuevos en Outlook - CON MANEJO DE OPERADOR OCUPADO"""
        try:
            # Limpiar archivos antiguos automáticamente
            self.limpiar_archivos_antiguos()
            
            logger.info("📬 Revisando correos nuevos...")
            
            # Conectar a Outlook
            outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            inbox = outlook.GetDefaultFolder(6)  # Bandeja de entrada
            
            # Obtener solo correos no leídos, más recientes primero
            mensajes = inbox.Items.Restrict("[UnRead] = True")
            mensajes.Sort("[ReceivedTime]", True)
            
            correos_procesados = 0
            correos_totales = mensajes.Count
            correos_saltados = 0
            operadores_ocupados = 0  # NUEVO CONTADOR
            
            logger.info(f"📊 Correos no leídos encontrados: {correos_totales}")
            logger.info(f"📊 Correos ya procesados en memoria: {len(self.correos_procesados)}")
            logger.info(f"📊 Viajes ya creados en memoria: {len(self.viajes_creados)}")
            
            for mensaje in mensajes:
                try:
                    # Verificación rápida para saltear correos obvios
                    remitente = mensaje.SenderEmailAddress or ""
                    if "PreFacturacionTransportes@walmart.com" not in remitente:
                        continue
                    
                    resultado_procesamiento = self.procesar_correo_individual(mensaje)
                    
                    if resultado_procesamiento == "OPERADOR_OCUPADO":
                        operadores_ocupados += 1
                        logger.warning(f"🚨 Viaje #{operadores_ocupados} con operador ocupado - registrado en MySQL")
                    elif resultado_procesamiento:
                        correos_procesados += 1
                    else:
                        correos_saltados += 1
                        
                    # Limitar procesamiento para evitar sobrecarga
                    if correos_procesados >= 3:
                        logger.info("⚠️ Límite de procesamiento alcanzado, esperando siguiente ciclo")
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje individual: {e}")
                    correos_saltados += 1
                    continue
            
            logger.info(f"✅ Ciclo completado:")
            logger.info(f"   📧 Total correos revisados: {correos_totales}")
            logger.info(f"   ✅ Correos procesados: {correos_procesados}")
            logger.info(f"   ⏭️ Correos saltados: {correos_saltados}")
            logger.info(f"   🚨 Operadores ocupados: {operadores_ocupados}")
            logger.info(f"   💾 Total en tracking: correos={len(self.correos_procesados)}, viajes={len(self.viajes_creados)}")
            
            if operadores_ocupados > 0:
                logger.info("📝 Los errores de operador ocupado fueron registrados en MySQL")
                logger.info("🔧 Estos viajes requieren revisión manual")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al revisar correos: {e}")
            return False
    
    def ejecutar_bucle_continuo(self, intervalo_minutos=5):
        """Ejecuta el sistema en bucle continuo"""
        logger.info("🚀 Iniciando sistema de automatización Alsua Transport v2.0")
        logger.info("🛡️ PROTECCIÓN ANTI-DUPLICADOS ACTIVADA")
        logger.info("🚨 MANEJO DE OPERADOR OCUPADO CON MYSQL")  # NUEVO
        logger.info(f"⏰ Revisión cada {intervalo_minutos} minutos")
        logger.info("📧 Filtrando correos de PreFacturacionTransportes@walmart.com")
        logger.info("🎯 Procesando solo viajes tipo VACIO")
        logger.info("🤖 Automatización GM completa habilitada")
        logger.info("💾 Viajes registrados en base de datos MySQL")  # NUEVO
        logger.info("🔧 Errores marcados para revisión manual")  # NUEVO
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
            
            # CERRAR CONEXIÓN MYSQL AL FINALIZAR
            try:
                from modules.mysql_simple import cerrar_conexion
                cerrar_conexion()
                logger.info("✅ Conexión MySQL cerrada")
            except Exception as e:
                logger.warning(f"⚠️ Error cerrando MySQL: {e}")
                    
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
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas del sistema"""
        logger.info("📊 ESTADÍSTICAS DEL SISTEMA:")
        logger.info(f"   📧 Correos procesados: {len(self.correos_procesados)}")
        logger.info(f"   🚛 Viajes creados: {len(self.viajes_creados)}")
        
        # Mostrar últimos procesados
        if self.correos_procesados:
            logger.info("   📧 Últimos correos procesados:")
            items = list(self.correos_procesados.items())[-3:]
            for key, value in items:
                estado = value.get('estado', 'DESCONOCIDO')
                prefactura = value.get('prefactura', 'Sin prefactura')
                logger.info(f"      - {prefactura} | {estado}")

def main():
    """Función principal"""
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              ALSUA TRANSPORT - SISTEMA COMPLETO v2.0        ║
    ║                  Mail Reader + GM Automation                ║
    ║                  🛡️ PROTECCIÓN ANTI-DUPLICADOS               ║
    ║                  🚨 MANEJO DE OPERADOR OCUPADO              ║
    ║                  💾 REGISTRO MYSQL                          ║
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