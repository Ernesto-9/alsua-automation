#!/usr/bin/env python3
"""
Sistema completo de automatización Alsua Transport
Mail Reader → Cola JSON → GM Automation
VERSIÓN MEJORADA: Cola persistente JSON, reintentos selectivos, proceso GM completo
MANTIENE: Todas las funcionalidades del sistema actual que funcionan
"""

import os
import time
import logging
import re
import sys
from datetime import datetime, timedelta
import win32com.client
import pythoncom  # Para inicialización COM
from modules.parser import parse_xls
from modules.gm_login import login_to_gm
from modules.gm_transport_general import GMTransportAutomation
# Usar tu sistema de cola existente
from cola_viajes import (
    agregar_viaje_a_cola, 
    obtener_siguiente_viaje_cola,
    marcar_viaje_exitoso_cola,
    marcar_viaje_fallido_cola,
    registrar_error_reintentable_cola,
    obtener_estadisticas_cola
)
# Usar tu sistema de logs existente
from viajes_log import registrar_viaje_fallido as log_viaje_fallido, viajes_log

# Configurar logging LIMPIO: Solo consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Solo consola
    ]
)
logger = logging.getLogger(__name__)

class AlsuaMailAutomation:
    def __init__(self):
        # Usar ruta absoluta para evitar problemas de permisos
        self.carpeta_descarga = os.path.abspath("archivos_descargados")
        
        self.driver = None
        
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
    
    def ya_fue_procesado_correo_csv(self, mensaje):
        """Verifica anti-duplicados usando solo el CSV"""
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
    
    # ==========================================
    # FUNCIONES SIMPLIFICADAS DE EXTRACCIÓN
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
    
    # ==========================================
    # FUNCIONES DE EXTRACCIÓN DE CORREOS
    # ==========================================
    
    def extraer_datos_de_correo(self, mensaje):
        """
        Extrae datos del correo y valida si es un viaje VACIO
        NO procesa el viaje, solo extrae datos
        """
        try:
            # Verificación anti-duplicados
            if self.ya_fue_procesado_correo_csv(mensaje):
                logger.info("⏭️ Saltando correo ya procesado (encontrado en CSV)")
                mensaje.UnRead = False
                return None
            
            asunto = mensaje.Subject or ""
            remitente = mensaje.SenderEmailAddress or ""
            fecha_recibido = mensaje.ReceivedTime
            
            # Filtros básicos
            if not remitente or "PreFacturacionTransportes@walmart.com" not in remitente:
                return None
                
            if "cancelado" in asunto.lower() or "no-reply" in remitente.lower():
                mensaje.UnRead = False
                return None
                
            if not "prefactura" in asunto.lower():
                mensaje.UnRead = False
                return None
            
            adjuntos = mensaje.Attachments
            if adjuntos.Count == 0:
                mensaje.UnRead = False
                return None
            
            logger.info(f"📩 Procesando correo NUEVO: {asunto}")
            
            # Extraer datos críticos
            prefactura = self.extraer_prefactura_del_asunto(asunto)
            clave_determinante = self.extraer_clave_determinante(asunto)
            
            if not prefactura:
                logger.warning(f"⚠️ No se pudo extraer prefactura del asunto: {asunto}")
                mensaje.UnRead = False
                return None
                
            if not clave_determinante:
                logger.warning(f"⚠️ No se pudo extraer clave determinante del asunto: {asunto}")
                mensaje.UnRead = False
                return None
            
            # Procesar archivos adjuntos
            for i in range(1, adjuntos.Count + 1):
                archivo = adjuntos.Item(i)
                nombre = archivo.FileName
                
                if not nombre.endswith(".xls"):
                    continue
                
                # Generar nombre único
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_unico = f"{timestamp}_{nombre}"
                ruta_local = os.path.join(self.carpeta_descarga, nombre_unico)
                
                # Descargar archivo
                try:
                    archivo.SaveAsFile(ruta_local)
                    logger.info(f"📥 Archivo descargado: {ruta_local}")
                except Exception as e:
                    logger.error(f"❌ Error al descargar archivo {nombre}: {e}")
                    mensaje.UnRead = False
                    continue
                
                # Parsear archivo usando tu parser existente
                resultado = parse_xls(ruta_local, determinante_from_asunto=clave_determinante)
                
                if "error" in resultado:
                    logger.warning(f"⚠️ Archivo no válido: {resultado['error']}")
                    os.remove(ruta_local)
                    
                    # Verificar si es porque NO ES TIPO VACIO
                    if "no es tipo VACIO" in resultado['error']:
                        logger.info("📄 Correo válido pero viaje no es tipo VACIO - marcando como leído")
                        mensaje.UnRead = False
                        return None
                    else:
                        # ERROR TÉCNICO (archivo corrupto, etc) - marcar como leído
                        mensaje.UnRead = False
                        continue
                
                # Completar datos
                resultado["prefactura"] = prefactura
                resultado["fecha"] = self.convertir_fecha_formato(resultado.get("fecha"))
                resultado["archivo_descargado"] = ruta_local
                
                logger.info("✅ Viaje VACIO válido extraído:")
                logger.info(f"   📋 Prefactura: {resultado['prefactura']}")
                logger.info(f"   📅 Fecha: {resultado['fecha']}")
                logger.info(f"   🚛 Placa Tractor: {resultado['placa_tractor']}")
                logger.info(f"   🚚 Placa Remolque: {resultado['placa_remolque']}")
                logger.info(f"   🎯 Determinante: {resultado['clave_determinante']}")
                logger.info(f"   💰 Importe: ${resultado['importe']}")
                
                return resultado
                
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
            return None
            
        return None
    
    def revisar_y_extraer_correos(self):
        """
        Revisa correos y extrae viajes válidos para agregar a la cola
        NO procesa viajes, solo los agrega a la cola
        """
        try:
            # INICIALIZAR COM PARA FLASK
            if not self.inicializar_com():
                logger.error("❌ No se pudo inicializar COM")
                return False
            
            logger.info("📬 Revisando correos para extraer viajes...")
            
            # Conectar a Outlook
            try:
                outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
                inbox = outlook.GetDefaultFolder(6)
                logger.info("✅ Conexión a Outlook establecida exitosamente")
            except Exception as e:
                logger.error(f"❌ Error conectando a Outlook: {e}")
                return False
            
            # Obtener correos no leídos, más recientes primero
            mensajes = inbox.Items.Restrict("[UnRead] = True")
            mensajes.Sort("[ReceivedTime]", True)
            
            correos_totales = mensajes.Count
            viajes_extraidos = 0
            correos_saltados = 0
            
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
                    
                    logger.info(f"🚀 Extrayendo viaje: {prefactura}")
                    datos_viaje = self.extraer_datos_de_correo(mensaje)
                    
                    if datos_viaje:
                        # Agregar a cola usando tu sistema existente
                        if agregar_viaje_a_cola(datos_viaje):
                            viajes_extraidos += 1
                            logger.info(f"➕ Viaje agregado a cola: {datos_viaje['prefactura']}")
                            
                            # Marcar correo como leído solo después de agregar a cola exitosamente
                            mensaje.UnRead = False
                        else:
                            logger.warning(f"⚠️ No se pudo agregar viaje a cola: {datos_viaje.get('prefactura')}")
                            # No marcar como leído si no se pudo agregar a cola
                    else:
                        correos_saltados += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando mensaje individual: {e}")
                    correos_saltados += 1
                    continue
            
            logger.info(f"✅ Extracción completada:")
            logger.info(f"   📧 Correos revisados: {correos_totales}")
            logger.info(f"   ➕ Viajes extraídos: {viajes_extraidos}")
            logger.info(f"   ⏭️ Correos saltados: {correos_saltados}")
            
            return viajes_extraidos > 0
            
        except Exception as e:
            logger.error(f"❌ Error revisando correos: {e}")
            return False
        finally:
            self.limpiar_com()
    
    # ==========================================
    # FUNCIONES DE PROCESAMIENTO DE COLA
    # ==========================================
    
    def crear_driver_nuevo(self):
        """Crea un nuevo driver con login"""
        try:
            logger.info("🔄 Creando nuevo driver...")
            
            # Limpiar driver anterior si existe
            if self.driver:
                try:
                    self.driver.quit()
                    time.sleep(2)
                except:
                    pass
                finally:
                    self.driver = None
            
            # Crear nuevo driver con login usando tu módulo existente
            self.driver = login_to_gm()
            
            if self.driver:
                logger.info("✅ Nuevo driver creado exitosamente")
                return True
            else:
                logger.error("❌ Error en login GM")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error crítico creando driver: {e}")
            self.driver = None
            return False
    
    def detectar_tipo_error(self, error):
        """
        Detecta el tipo de error - SOLO 2 TIPOS SON REINTENTABLES
        
        Returns:
            str: 'LOGIN_LIMIT', 'DRIVER_CORRUPTO', 'VIAJE_FALLIDO'
        """
        error_str = str(error).lower()
        
        # ERRORES REINTENTABLES:
        
        # 1. Errores de límite de usuarios (reintenta en 15 min)
        if any(keyword in error_str for keyword in ['limit', 'limite', 'usuarios', 'user limit', 'maximum', 'conexiones']):
            return 'LOGIN_LIMIT'
        
        # 2. Errores de driver corrupto (reintenta inmediatamente)
        if any(keyword in error_str for keyword in ['invalid session', 'chrome not reachable', 'no such window', 'session deleted', 'connection refused']):
            return 'DRIVER_CORRUPTO'
        
        # TODOS LOS DEMÁS SON FALLIDOS (no reintenta):
        # - Operador ocupado
        # - Determinante no encontrada  
        # - Placa sin operador
        # - Errores de módulos específicos
        # - Cualquier otro error de datos/proceso
        return 'VIAJE_FALLIDO'
    
    def procesar_viaje_individual(self, viaje_registro):
        """
        Procesa un solo viaje de la cola usando TU SISTEMA GM COMPLETO
        
        Returns:
            tuple: (resultado, modulo_error) donde:
            - resultado: 'EXITOSO', 'VIAJE_FALLIDO', 'LOGIN_LIMIT', 'DRIVER_CORRUPTO'
            - modulo_error: módulo específico donde falló (para logging)
        """
        try:
            viaje_id = viaje_registro.get('id')
            datos_viaje = viaje_registro.get('datos_viaje', {})
            prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
            
            logger.info(f"🚀 Procesando viaje: {prefactura}")
            
            # PASO 1: Crear/verificar driver
            if not self.driver:
                logger.info("🔄 No hay driver, creando nuevo...")
                if not self.crear_driver_nuevo():
                    return 'LOGIN_LIMIT', 'gm_login'  # Error de login
            
            # PASO 2: Verificar que driver sigue válido
            try:
                current_url = self.driver.current_url
                if "softwareparatransporte.com" not in current_url:
                    logger.warning("⚠️ Driver en página incorrecta, recreando...")
                    if not self.crear_driver_nuevo():
                        return 'LOGIN_LIMIT', 'gm_login'
            except Exception as e:
                logger.warning(f"⚠️ Driver corrupto detectado: {e}")
                if not self.crear_driver_nuevo():
                    return 'DRIVER_CORRUPTO', 'selenium_driver'
            
            # PASO 3: Ejecutar automatización GM COMPLETA usando tu sistema existente
            try:
                # MANTENER INTEGRACIÓN COMPLETA CON TU SISTEMA ACTUAL
                automation = GMTransportAutomation(self.driver)
                automation.datos_viaje = datos_viaje
                
                # Esta función YA orquesta todo tu proceso completo:
                # - Facturación inicial (gm_facturacion1.py)
                # - Salida del viaje (gm_salida.py) 
                # - Llegada y facturación final (gm_llegadayfactura2.py)
                # - Extracción automática de PDF (pdf_extractor.py)
                # - Registro en CSV (viajes_log.py)
                # - Sincronización MySQL (mysql_simple.py)
                resultado = automation.fill_viaje_form()
                
                if resultado == "OPERADOR_OCUPADO":
                    logger.warning(f"🚨 Operador ocupado: {prefactura}")
                    # El navegador ya fue cerrado en gm_salida.py
                    self.driver = None
                    # OPERADOR_OCUPADO ahora es VIAJE_FALLIDO (no reintenta)
                    return 'VIAJE_FALLIDO', 'gm_salida'
                    
                elif resultado:
                    logger.info(f"✅ Viaje completado exitosamente: {prefactura}")
                    logger.info("📊 Datos completos (UUID, Viaje GM, placas) registrados automáticamente")
                    logger.info("🔄 MySQL sincronizado automáticamente desde CSV")
                    
                    # Limpiar archivo Excel
                    archivo_descargado = datos_viaje.get('archivo_descargado')
                    if archivo_descargado and os.path.exists(archivo_descargado):
                        os.remove(archivo_descargado)
                        logger.info(f"🗑️ Archivo limpiado: {os.path.basename(archivo_descargado)}")
                    
                    return 'EXITOSO', ''
                else:
                    logger.error(f"❌ Error en automatización GM: {prefactura}")
                    return 'VIAJE_FALLIDO', 'gm_transport_general'
                    
            except Exception as automation_error:
                logger.error(f"❌ Error durante automatización: {automation_error}")
                
                # Detectar tipo de error
                tipo_error = self.detectar_tipo_error(automation_error)
                
                if tipo_error == 'LOGIN_LIMIT':
                    return 'LOGIN_LIMIT', 'gm_login'
                elif tipo_error == 'DRIVER_CORRUPTO':
                    # Driver corrupto - limpiar y reintentará inmediatamente
                    try:
                        self.driver.quit()
                    except:
                        pass
                    finally:
                        self.driver = None
                    return 'DRIVER_CORRUPTO', 'selenium_driver'
                else:
                    # Error de viaje - determinar módulo específico del error
                    modulo_error = self.determinar_modulo_error(automation_error)
                    return 'VIAJE_FALLIDO', modulo_error
                
        except Exception as e:
            logger.error(f"❌ Error general procesando viaje: {e}")
            return 'VIAJE_FALLIDO', 'sistema_general'
    
    def determinar_modulo_error(self, error):
        """
        Determina en qué módulo específico ocurrió el error para mejor debugging
        
        Returns:
            str: nombre del módulo donde falló
        """
        error_str = str(error).lower()
        
        # Mapear errores a módulos específicos
        if any(keyword in error_str for keyword in ['determinante', 'ruta_gm', 'base_origen']):
            return 'gm_transport_general'
        elif any(keyword in error_str for keyword in ['placa_tractor', 'placa_remolque', 'operador']):
            return 'gm_transport_general'
        elif any(keyword in error_str for keyword in ['facturacion', 'importe', 'total']):
            return 'gm_facturacion1'
        elif any(keyword in error_str for keyword in ['salida', 'status', 'en_ruta']):
            return 'gm_salida'
        elif any(keyword in error_str for keyword in ['llegada', 'terminado', 'autorizar', 'facturar']):
            return 'gm_llegadayfactura2'
        elif any(keyword in error_str for keyword in ['pdf', 'uuid', 'viajegm', 'folio']):
            return 'pdf_extractor'
        elif any(keyword in error_str for keyword in ['navigate', 'viaje', 'crear']):
            return 'navigate_to_create_viaje'
        else:
            return 'modulo_desconocido'
    
    def procesar_cola_viajes(self):
        """
        FUNCIÓN PRINCIPAL: Procesa todos los viajes en la cola
        FLUJO CONTINUO CON TIEMPOS ESPECÍFICOS
        """
        try:
            logger.info("🚀 Iniciando procesamiento de cola de viajes...")
            
            while True:
                # Obtener siguiente viaje usando tu sistema de cola existente
                viaje_registro = obtener_siguiente_viaje_cola()
                
                if not viaje_registro:
                    logger.info("✅ No hay más viajes en cola")
                    break
                
                viaje_id = viaje_registro.get('id')
                datos_viaje = viaje_registro.get('datos_viaje', {})
                prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
                
                # Procesar viaje usando tu sistema GM completo
                resultado, modulo_error = self.procesar_viaje_individual(viaje_registro)
                
                if resultado == 'EXITOSO':
                    # ✅ VIAJE EXITOSO → Remover de cola → Esperar 1 min
                    marcar_viaje_exitoso_cola(viaje_id)
                    logger.info(f"✅ Viaje {prefactura} completado y removido de cola")
                    
                    # ESPERAR 1 MINUTO antes del siguiente viaje
                    logger.info("⏳ Esperando 1 minuto antes del siguiente viaje...")
                    time.sleep(60)
                    
                elif resultado == 'LOGIN_LIMIT':
                    # 🚨 ERROR DE LOGIN → Mantener en cola → Esperar 15 min
                    registrar_error_reintentable_cola(viaje_id, 'LOGIN_LIMIT', f'Límite de usuarios en {modulo_error}')
                    logger.warning(f"🚨 Límite de usuarios - {prefactura} reintentará en 15 minutos")
                    
                    # ESPERAR 15 MINUTOS
                    logger.info("⏳ Esperando 15 minutos por límite de usuarios...")
                    time.sleep(15 * 60)
                    
                elif resultado == 'DRIVER_CORRUPTO':
                    # 🔧 DRIVER CORRUPTO → Mantener en cola → Reintentar inmediatamente
                    registrar_error_reintentable_cola(viaje_id, 'DRIVER_CORRUPTO', f'Driver corrupto en {modulo_error}')
                    logger.warning(f"🔧 Driver corrupto - {prefactura} reintentará inmediatamente")
                    # NO ESPERA - reintenta inmediatamente
                    
                else:  # VIAJE_FALLIDO
                    # ❌ ERROR DEL VIAJE → Remover de cola → Esperar 30 seg
                    motivo_detallado = f"PROCESO FALLÓ EN: {modulo_error}"
                    marcar_viaje_fallido_cola(viaje_id, modulo_error, motivo_detallado)
                    logger.error(f"❌ {prefactura} FALLÓ EN: {modulo_error} - removido de cola")
                    
                    # ESPERAR 30 SEGUNDOS después de fallo
                    logger.info("⏳ Esperando 30 segundos después de viaje fallido...")
                    time.sleep(30)
            
        except KeyboardInterrupt:
            logger.info("⚠️ Interrupción manual del procesamiento")
        except Exception as e:
            logger.error(f"❌ Error en procesamiento de cola: {e}")
        finally:
            # Limpiar driver al finalizar
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                finally:
                    self.driver = None
    
    # ==========================================
    # FUNCIONES PRINCIPALES DEL SISTEMA
    # ==========================================
    
    def mostrar_estadisticas_inicio(self):
        """Muestra estadísticas al iniciar el sistema"""
        logger.info("📊 Estado inicial del sistema:")
        
        # Estadísticas de cola usando tu sistema existente
        try:
            stats_cola = obtener_estadisticas_cola()
            logger.info(f"   📋 Viajes en cola: {stats_cola.get('total_viajes', 0)}")
            logger.info(f"   ⏳ Pendientes: {stats_cola.get('pendientes', 0)}")
            logger.info(f"   🔄 Procesando: {stats_cola.get('procesando', 0)}")
            
            if stats_cola.get('viajes_con_errores', 0) > 0:
                logger.info(f"   ⚠️ Con errores: {stats_cola.get('viajes_con_errores', 0)}")
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo estadísticas de cola: {e}")
    
    def ejecutar_bucle_continuo(self, mostrar_debug=False):
        """
        SISTEMA CONTINUO: Flujo perpetuo con cola persistente
        SIN intervalos fijos - Procesamiento inmediato
        """
        logger.info("🚀 Iniciando sistema de automatización Alsua Transport v6.0 CONTINUO")
        logger.info("🔄 FLUJO CONTINUO CON COLA PERSISTENTE:")
        logger.info("   📬 Revisar correos → 🎯 Viaje VACIO → ➕ Cola → 🚛 Procesar")
        logger.info("   ✅ Exitoso: 1 min → 🔄")
        logger.info("   ❌ Fallido: 30 seg → 🔄")  
        logger.info("   🚨 Login: 15 min → 🔄")
        logger.info("   🔧 Driver: Inmediato → 🔄")
        logger.info("🛡️ ROBUSTEZ MÁXIMA:")
        logger.info("   ✅ MANTIENE todo tu sistema actual")
        logger.info("   ✅ Proceso GM completo (facturación → salida → llegada)")
        logger.info("   ✅ Extracción automática PDF (UUID + Viaje GM)")
        logger.info("   ✅ Registro unificado CSV + MySQL")
        logger.info("   ✅ Solo 2 errores reintentables (LOGIN_LIMIT, DRIVER_CORRUPTO)")
        logger.info("   ✅ Todos los demás → FALLIDO con módulo específico")
        logger.info("🌐 Compatible con Flask - SIN input manual")
        logger.info("🚫 SIN intervalos de 5 minutos innecesarios")
        logger.info("=" * 70)
        
        # Mostrar estadísticas iniciales
        self.mostrar_estadisticas_inicio()
        
        try:
            contador_ciclos = 0
            while True:
                try:
                    contador_ciclos += 1
                    if mostrar_debug:
                        logger.info(f"🔄 Ciclo #{contador_ciclos}")
                    
                    # PASO 1: Revisar correos y extraer viajes VACIO
                    if mostrar_debug:
                        logger.info("📬 Revisando correos nuevos...")
                    
                    viajes_encontrados = self.revisar_y_extraer_correos()
                    
                    if viajes_encontrados:
                        logger.info("✅ Nuevos viajes VACIO encontrados y agregados a cola")
                    
                    # PASO 2: Procesar cola de viajes (uno por uno)
                    if mostrar_debug:
                        logger.info("🚛 Procesando cola de viajes...")
                    
                    # Obtener UN viaje de la cola
                    viaje_registro = obtener_siguiente_viaje_cola()
                    
                    if viaje_registro:
                        viaje_id = viaje_registro.get('id')
                        datos_viaje = viaje_registro.get('datos_viaje', {})
                        prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
                        
                        logger.info(f"🎯 Procesando viaje de cola: {prefactura}")
                        
                        # Procesar viaje usando tu sistema GM completo
                        resultado, modulo_error = self.procesar_viaje_individual(viaje_registro)
                        
                        if resultado == 'EXITOSO':
                            # ✅ EXITOSO → Remover de cola → Esperar 1 min → Continuar
                            marcar_viaje_exitoso_cola(viaje_id)
                            logger.info(f"✅ Viaje {prefactura} COMPLETADO - removido de cola")
                            logger.info("⏳ Esperando 1 minuto antes de continuar...")
                            time.sleep(60)
                            
                        elif resultado == 'LOGIN_LIMIT':
                            # 🚨 LOGIN_LIMIT → Mantener en cola → Esperar 15 min → Continuar
                            registrar_error_reintentable_cola(viaje_id, 'LOGIN_LIMIT', f'Límite de usuarios en {modulo_error}')
                            logger.warning(f"🚨 LOGIN LÍMITE - {prefactura} reintentará en 15 minutos")
                            logger.info("⏳ Esperando 15 minutos por límite de usuarios...")
                            time.sleep(15 * 60)
                            
                        elif resultado == 'DRIVER_CORRUPTO':
                            # 🔧 DRIVER_CORRUPTO → Mantener en cola → Continuar inmediatamente
                            registrar_error_reintentable_cola(viaje_id, 'DRIVER_CORRUPTO', f'Driver corrupto en {modulo_error}')
                            logger.warning(f"🔧 DRIVER CORRUPTO - {prefactura} reintentará inmediatamente")
                            # NO ESPERA - continúa inmediatamente
                            
                        else:  # VIAJE_FALLIDO
                            # ❌ FALLIDO → Remover de cola → Esperar 30 seg → Continuar
                            motivo_detallado = f"PROCESO FALLÓ EN: {modulo_error}"
                            marcar_viaje_fallido_cola(viaje_id, modulo_error, motivo_detallado)
                            logger.error(f"❌ {prefactura} FALLÓ EN: {modulo_error} - removido de cola")
                            logger.info("⏳ Esperando 30 segundos después de viaje fallido...")
                            time.sleep(30)
                    
                    else:
                        # No hay viajes en cola - continuar inmediatamente revisando correos
                        if mostrar_debug:
                            logger.info("ℹ️ Cola vacía - continuando revisión de correos")
                        # Sin espera - continúa inmediatamente el bucle
                    
                    # PASO 3: Mostrar estadísticas periódicamente
                    if contador_ciclos % 10 == 0:  # Cada 10 ciclos
                        try:
                            stats = obtener_estadisticas_cola()
                            if stats.get('total_viajes', 0) > 0:
                                logger.info(f"📊 Cola actual: {stats.get('pendientes', 0)} pendientes, {stats.get('procesando', 0)} procesando")
                        except:
                            pass
                    
                    # SIN ESPERAS INNECESARIAS - continúa inmediatamente al siguiente ciclo
                    
                except KeyboardInterrupt:
                    logger.info("⚠️ Interrupción manual detectada")
                    break
                    
                except Exception as e:
                    logger.error(f"❌ Error en ciclo continuo: {e}")
                    logger.info("🔄 Continuando con siguiente ciclo en 30 segundos...")
                    time.sleep(30)  # Espera solo en caso de error
                    
        except KeyboardInterrupt:
            logger.info("🛑 Sistema detenido por usuario")
            
        finally:
            # Limpiar driver si existe
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            # Limpiar COM
            self.limpiar_com()
            
            logger.info("👋 Sistema de automatización finalizado")
    
    def ejecutar_revision_unica(self):
        """Ejecuta una sola revisión completa (para pruebas y debugging)"""
        logger.info("🧪 Ejecutando revisión única...")
        logger.info("🔄 MODO TEST: Solo algunos ciclos para inspección")
        logger.info("✅ MANTIENE TODO TU SISTEMA ACTUAL")
        
        # Mostrar estadísticas iniciales
        self.mostrar_estadisticas_inicio()
        
        try:
            # Ejecutar solo algunos ciclos para prueba
            ciclos_max = 5
            logger.info(f"🔄 Ejecutando máximo {ciclos_max} ciclos de prueba...")
            
            for ciclo in range(ciclos_max):
                logger.info(f"🧪 Ciclo de prueba {ciclo + 1}/{ciclos_max}")
                
                # Revisar correos
                viajes_encontrados = self.revisar_y_extraer_correos()
                
                if viajes_encontrados:
                    logger.info("✅ Nuevos viajes encontrados en modo test")
                
                # Procesar UN viaje si hay
                viaje_registro = obtener_siguiente_viaje_cola()
                
                if viaje_registro:
                    prefactura = viaje_registro.get('datos_viaje', {}).get('prefactura', 'DESCONOCIDA')
                    logger.info(f"🎯 MODO TEST: Procesando viaje {prefactura}")
                    
                    resultado, modulo_error = self.procesar_viaje_individual(viaje_registro)
                    logger.info(f"📊 Resultado test: {resultado} en {modulo_error}")
                    
                    # Manejar resultado igual que en modo producción
                    viaje_id = viaje_registro.get('id')
                    if resultado == 'EXITOSO':
                        marcar_viaje_exitoso_cola(viaje_id)
                        logger.info("✅ Viaje test completado")
                        break  # Salir después de 1 éxito en modo test
                    elif resultado in ['LOGIN_LIMIT', 'DRIVER_CORRUPTO']:
                        registrar_error_reintentable_cola(viaje_id, resultado, f'Error test en {modulo_error}')
                        logger.warning(f"⚠️ Error reintentable en test: {resultado}")
                    else:
                        marcar_viaje_fallido_cola(viaje_id, modulo_error, f"Test falló en {modulo_error}")
                        logger.error(f"❌ Viaje test falló en: {modulo_error}")
                        break  # Salir después de 1 fallo en modo test
                else:
                    logger.info("ℹ️ No hay viajes en cola para test")
                
                # Pausa corta entre ciclos de test
                if ciclo < ciclos_max - 1:
                    logger.info("⏳ Pausa entre ciclos de test...")
                    time.sleep(10)
            
            # Mostrar estadísticas finales
            try:
                stats = obtener_estadisticas_cola()
                logger.info("📊 Estadísticas finales del test:")
                logger.info(f"   📋 Total viajes: {stats.get('total_viajes', 0)}")
                logger.info(f"   ⏳ Pendientes: {stats.get('pendientes', 0)}")
                logger.info(f"   🔄 Procesando: {stats.get('procesando', 0)}")
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo estadísticas finales: {e}")
            
            logger.info("✅ Revisión única de test completada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en revisión única: {e}")
            return False
        finally:
            # Limpiar driver
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            self.limpiar_com()
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas del sistema usando solo CSV"""
        logger.info("📊 ESTADÍSTICAS DEL SISTEMA MEJORADO v6.0:")
        logger.info("   🔄 Sistema de cola persistente JSON")
        logger.info("   🛡️ Reintentos selectivos inteligentes")
        logger.info("   ✅ MANTIENE TODO TU SISTEMA ACTUAL:")
        logger.info("       • Proceso GM completo")
        logger.info("       • Extracción automática PDF")
        logger.info("       • Registro CSV + MySQL")
        logger.info("       • Compatibilidad Flask")
        logger.info("   🌐 Arranque automático para interfaz web")
        
        # Mostrar estadísticas del CSV usando tu sistema existente
        try:
            stats = viajes_log.obtener_estadisticas()
            logger.info(f"   📊 Total viajes en CSV: {stats['total_viajes']}")
            logger.info(f"   ✅ Exitosos: {stats['exitosos']}")
            logger.info(f"   ❌ Fallidos: {stats['fallidos']}")
            if stats['ultimo_viaje']:
                logger.info(f"   📅 Último viaje: {stats['ultimo_viaje']}")
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo estadísticas CSV: {e}")
        
        # Mostrar estadísticas de la cola usando tu sistema existente
        try:
            stats_cola = obtener_estadisticas_cola()
            logger.info(f"   📋 Viajes en cola: {stats_cola.get('total_viajes', 0)}")
            logger.info(f"   ⏳ Pendientes: {stats_cola.get('pendientes', 0)}")
            logger.info(f"   🔄 Procesando: {stats_cola.get('procesando', 0)}")
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo estadísticas de cola: {e}")

def main():
    """Función principal - ARRANQUE AUTOMÁTICO CONTINUO"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║         ALSUA TRANSPORT - SISTEMA v6.0 CONTINUO             ║
    ║               🔄 FLUJO CONTINUO CON COLA PERSISTENTE         ║
    ║               🛡️ ROBUSTEZ MÁXIMA                             ║
    ║               ✅ MANTIENE TODO TU SISTEMA ACTUAL             ║
    ║               📊 Proceso GM completo conservado              ║
    ║               🎯 Extracción automática PDF                   ║
    ║               💾 Registro CSV + MySQL                        ║
    ║               🌐 Compatible con Flask                        ║
    ║               🚫 SIN intervalos de 5 minutos                 ║
    ║               🚫 SIN input manual requerido                  ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    sistema = AlsuaMailAutomation()
    
    # Mostrar estadísticas iniciales
    sistema.mostrar_estadisticas()
    
    # ARRANQUE AUTOMÁTICO continuo
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Modo prueba: revisión única con debugging
        logger.info("🧪 MODO PRUEBA: Ejecutando revisión de test...")
        sistema.ejecutar_revision_unica()
    else:
        # Modo producción: flujo continuo sin intervalos
        logger.info("🚀 MODO PRODUCCIÓN: Iniciando flujo continuo")
        logger.info("🔄 PROCESAMIENTO PERPETUO:")
        logger.info("   📬 Revisar correos → 🎯 Viaje VACIO → ➕ Cola → 🚛 Procesar → 🔄")
        logger.info("   ✅ Sin intervalos fijos innecesarios")
        logger.info("   ✅ Máxima robustez con cola persistente")
        logger.info("   ✅ Solo 2 errores reintentables")
        logger.info("🌐 Compatible con interfaz web Flask")
        sistema.ejecutar_bucle_continuo(mostrar_debug=False)

if __name__ == "__main__":
    main()