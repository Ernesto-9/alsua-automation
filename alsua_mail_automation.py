#!/usr/bin/env python3
"""
Sistema completo de automatización Alsua Transport
Mail Reader → Cola JSON → GM Automation
"""

import os
import time
import logging
import re
import sys
import csv
from datetime import datetime, timedelta
import win32com.client
import pythoncom
from modules.parser import parse_xls
from modules.gm_login import login_to_gm
from modules.gm_transport_general import GMTransportAutomation
from cola_viajes import (
    agregar_viaje_a_cola,
    obtener_siguiente_viaje_cola,
    marcar_viaje_exitoso_cola,
    marcar_viaje_fallido_cola,
    registrar_error_reintentable_cola,
    obtener_estadisticas_cola
)
from viajes_log import registrar_viaje_fallido as log_viaje_fallido, viajes_log
# Importar módulos de mejora
from modules import robot_state_manager
from modules.debug_logger import debug_logger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlsuaMailAutomation:
    # Variable de clase para controlar la ejecución desde Flask
    continuar_ejecutando = True

    def __init__(self):
        self.carpeta_descarga = os.path.abspath("archivos_descargados")

        self.driver = None

        self.com_inicializado = False

        self.emails_fallidos = {}

        # Sistema de detección de loops infinitos
        self.historial_procesamiento = {}  # {prefactura: [timestamp1, timestamp2, ...]}
        self.ultimo_viaje_procesado = None
        self.ultimo_timestamp_procesado = None

        self._crear_carpeta_descarga()
        
    def _crear_carpeta_descarga(self):
        try:
            if not os.path.exists(self.carpeta_descarga):
                os.makedirs(self.carpeta_descarga)

            test_file = os.path.join(self.carpeta_descarga, "test_permisos.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                logger.error(f"Error de permisos en carpeta: {e}")
                self.carpeta_descarga = os.path.join(os.path.expanduser("~"), "Downloads", "alsua_archivos")
                os.makedirs(self.carpeta_descarga, exist_ok=True)
                logger.warning(f"Usando carpeta alternativa: {self.carpeta_descarga}")

        except Exception as e:
            logger.error(f"Error al crear carpeta: {e}")
            self.carpeta_descarga = os.path.join(os.path.expanduser("~"), "Downloads", "alsua_archivos")
            os.makedirs(self.carpeta_descarga, exist_ok=True)
            logger.warning(f"Carpeta fallback: {self.carpeta_descarga}")
    
    def inicializar_com(self):
        try:
            if not self.com_inicializado:
                pythoncom.CoInitialize()
                self.com_inicializado = True
                return True
        except Exception as e:
            logger.error(f"Error inicializando COM: {e}")
            return False

    def limpiar_com(self):
        try:
            if self.com_inicializado:
                pythoncom.CoUninitialize()
                self.com_inicializado = False
        except Exception as e:
            logger.warning(f"Error limpiando COM: {e}")
    
    def ya_fue_procesado_correo_csv(self, mensaje):
        try:
            prefactura = self.extraer_prefactura_del_asunto(mensaje.Subject or "")
            if not prefactura:
                return False
            
            viaje_existente = viajes_log.verificar_viaje_existe(prefactura)

            if viaje_existente:
                logger.info(f"Correo duplicado: {prefactura} ({viaje_existente.get('estatus')} @ {viaje_existente.get('timestamp')})")
                return True

            return False
            
        except Exception as e:
            logger.warning(f"Error verificando duplicados en CSV: {e}")
            return False
    
    def extraer_prefactura_del_asunto(self, asunto):
        match = re.search(r"prefactura\s+(\d+)", asunto, re.IGNORECASE)
        if match:
            return match.group(1)
        
        match = re.search(r"\b\d{7}\b", asunto)
        if match:
            return match.group(0)
            
        return None
    
    def extraer_clave_determinante(self, asunto):
        match = re.search(r"cedis\s+origen\s+(\d{4})", asunto, re.IGNORECASE)
        if match:
            return match.group(1)
        
        match = re.search(r"\b\d{4}\b", asunto)
        if match:
            return match.group(0)
            
        return None
    
    def convertir_fecha_formato(self, fecha_str):
        try:
            if not fecha_str or fecha_str == "nan":
                return datetime.now().strftime("%d/%m/%Y")
                
            formatos = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
            
            for formato in formatos:
                try:
                    fecha_obj = datetime.strptime(str(fecha_str).split()[0], formato)
                    return fecha_obj.strftime("%d/%m/%Y")
                except:
                    continue
                    
            logger.warning(f"No se pudo convertir fecha: {fecha_str}, usando fecha actual")
            return datetime.now().strftime("%d/%m/%Y")
            
        except Exception as e:
            logger.error(f"Error al convertir fecha: {e}")
            return datetime.now().strftime("%d/%m/%Y")
    
    def extraer_datos_de_correo(self, mensaje):
        try:
            if self.ya_fue_procesado_correo_csv(mensaje):
                logger.info("Saltando correo ya procesado (encontrado en CSV)")
                mensaje.UnRead = False
                return None
            
            asunto = mensaje.Subject or ""
            remitente = mensaje.SenderEmailAddress or ""
            fecha_recibido = mensaje.ReceivedTime
            
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
            
            logger.info(f"Procesando correo NUEVO: {asunto}")
            
            prefactura = self.extraer_prefactura_del_asunto(asunto)
            clave_determinante = self.extraer_clave_determinante(asunto)
            
            if not prefactura:
                logger.warning(f"No se pudo extraer prefactura del asunto: {asunto}")
                mensaje.UnRead = False
                return None
                
            if not clave_determinante:
                logger.warning(f"No se pudo extraer clave determinante del asunto: {asunto}")
                mensaje.UnRead = False
                return None
            
            for i in range(1, adjuntos.Count + 1):
                archivo = adjuntos.Item(i)
                nombre = archivo.FileName
                
                if not nombre.endswith(".xls"):
                    continue
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_unico = f"{timestamp}_{nombre}"
                ruta_local = os.path.join(self.carpeta_descarga, nombre_unico)
                
                try:
                    archivo.SaveAsFile(ruta_local)
                    logger.info(f"Archivo descargado: {ruta_local}")
                except Exception as e:
                    logger.error(f"Error al descargar archivo {nombre}: {e}")
                    mensaje.UnRead = False
                    continue
                
                resultado = parse_xls(ruta_local, determinante_from_asunto=clave_determinante)
                
                if "error" in resultado:
                    logger.warning(f"Archivo no válido: {resultado['error']}")
                    os.remove(ruta_local)
                    
                    if "no es tipo VACIO" in resultado['error']:
                        logger.info("Correo válido pero viaje no es tipo VACIO - marcando como leído")
                        mensaje.UnRead = False
                        return None
                    else:
                        mensaje.UnRead = False
                        continue
                
                resultado["prefactura"] = prefactura
                resultado["fecha"] = self.convertir_fecha_formato(resultado.get("fecha"))
                resultado["archivo_descargado"] = ruta_local

                logger.info(f"Viaje extraído: {resultado['prefactura']} | "
                           f"Fecha:{resultado['fecha']} | Tractor:{resultado['placa_tractor']} | "
                           f"Remolque:{resultado['placa_remolque']} | Det:{resultado['clave_determinante']} | ${resultado['importe']}")

                return resultado
                
        except KeyboardInterrupt:
            logger.info("Interrupción manual - no marcando correo como leído")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al procesar correo: {e}")
            try:
                mensaje.UnRead = False
            except:
                pass
            return None
            
        return None
    
    def revisar_y_extraer_correos(self, limite_viajes=3):
        try:
            if not self.inicializar_com():
                logger.error("No se pudo inicializar COM")
                return False
            
            logger.info(f"Revisando correos (máximo {limite_viajes} viajes)...")
            
            try:
                outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
                inbox = outlook.GetDefaultFolder(6)
                logger.info("Conexión a Outlook establecida exitosamente")
            except Exception as e:
                logger.error(f"Error conectando a Outlook: {e}")
                return False
            
            mensajes = inbox.Items.Restrict("[UnRead] = True")
            mensajes.Sort("[ReceivedTime]", True)
            
            correos_totales = mensajes.Count
            viajes_extraidos = 0
            correos_saltados = 0
            
            logger.info(f"Correos no leídos encontrados: {correos_totales}")
            
            for mensaje in mensajes:
                if viajes_extraidos >= limite_viajes:
                    logger.info(f"Límite alcanzado: {limite_viajes} viajes extraídos")
                    break

                try:
                    remitente = mensaje.SenderEmailAddress or ""
                    if "PreFacturacionTransportes@walmart.com" not in remitente:
                        continue

                    asunto = mensaje.Subject or ""
                    prefactura = self.extraer_prefactura_del_asunto(asunto)

                    if prefactura in self.emails_fallidos and self.emails_fallidos[prefactura] >= 3:
                        try:
                            carpeta_problemas = inbox.Folders("Problemas")
                        except:
                            carpeta_problemas = inbox.Folders.Add("Problemas")

                        mensaje.Move(carpeta_problemas)
                        correos_saltados += 1
                        continue

                    logger.info(f"Extrayendo viaje: {prefactura}")
                    datos_viaje = self.extraer_datos_de_correo(mensaje)

                    if datos_viaje:
                        if isinstance(datos_viaje, list):
                            correos_saltados += 1
                            self.emails_fallidos[prefactura] = self.emails_fallidos.get(prefactura, 0) + 1
                            continue

                        if not isinstance(datos_viaje, dict):
                            correos_saltados += 1
                            self.emails_fallidos[prefactura] = self.emails_fallidos.get(prefactura, 0) + 1
                            continue

                        if agregar_viaje_a_cola(datos_viaje):
                            viajes_extraidos += 1
                            logger.info(f"Viaje agregado a cola: {datos_viaje['prefactura']}")

                            mensaje.UnRead = False
                        else:
                            logger.warning(f"No se pudo agregar viaje a cola: {datos_viaje.get('prefactura')}")
                    else:
                        correos_saltados += 1

                except Exception as e:
                    logger.error(f"Error procesando mensaje individual: {e}")
                    correos_saltados += 1
                    try:
                        asunto = mensaje.Subject or ""
                        prefactura = self.extraer_prefactura_del_asunto(asunto)
                        self.emails_fallidos[prefactura] = self.emails_fallidos.get(prefactura, 0) + 1
                    except:
                        pass
                    continue
            
            logger.info(f"Extracción completada:")
            logger.info(f"   Correos revisados: {correos_totales}")
            logger.info(f"   Viajes extraídos: {viajes_extraidos}")
            logger.info(f"   Correos saltados: {correos_saltados}")
            
            return viajes_extraidos > 0
            
        except Exception as e:
            logger.error(f"Error revisando correos: {e}")
            return False
        finally:
            self.limpiar_com()
    
    def crear_driver_nuevo(self):
        try:
            logger.info("Creando nuevo driver...")

            if self.driver:
                try:
                    self.driver.quit()
                    time.sleep(2)
                except:
                    pass
                finally:
                    self.driver = None

            self.driver = login_to_gm()

            if self.driver:
                logger.info("Nuevo driver creado exitosamente")
                self.ultimo_error_driver = None
                return True
            else:
                logger.error("Error en login GM")
                self.ultimo_error_driver = Exception("Login GM falló sin excepción específica")
                return False

        except Exception as e:
            logger.error(f"Error crítico creando driver: {e}")
            self.driver = None
            self.ultimo_error_driver = e
            return False
    
    def detectar_loop_infinito(self, prefactura, max_intentos_ventana=10, ventana_minutos=5):
        """
        Detecta si un viaje está en un loop infinito

        Args:
            prefactura: ID del viaje
            max_intentos_ventana: Máximo de intentos permitidos en la ventana de tiempo
            ventana_minutos: Tamaño de la ventana de tiempo en minutos

        Returns:
            True si se detecta loop infinito, False en caso contrario
        """
        ahora = datetime.now()

        # Registrar intento actual
        if prefactura not in self.historial_procesamiento:
            self.historial_procesamiento[prefactura] = []

        self.historial_procesamiento[prefactura].append(ahora)

        # Limpiar intentos antiguos (fuera de la ventana)
        ventana_inicio = ahora - timedelta(minutes=ventana_minutos)
        self.historial_procesamiento[prefactura] = [
            ts for ts in self.historial_procesamiento[prefactura]
            if ts >= ventana_inicio
        ]

        # Contar intentos en la ventana
        intentos_recientes = len(self.historial_procesamiento[prefactura])

        if intentos_recientes > max_intentos_ventana:
            logger.error(f"LOOP INFINITO DETECTADO: Viaje {prefactura} procesado {intentos_recientes} veces en {ventana_minutos} minutos")
            debug_logger.error(f"[{prefactura}] LOOP INFINITO: {intentos_recientes} intentos en {ventana_minutos} min")
            debug_logger.error(f"[{prefactura}] Timestamps: {[ts.strftime('%H:%M:%S') for ts in self.historial_procesamiento[prefactura]]}")
            return True

        return False

    def detectar_tipo_error(self, error):
        error_str = str(error).lower()

        if any(keyword in error_str for keyword in [
            'invalid session', 'chrome not reachable', 'no such window',
            'session deleted', 'connection refused', 'stacktrace',
            'gethandleverifier', 'basethreadinitthunk', 'devtools'
        ]):
            return 'DRIVER_CORRUPTO'

        if any(keyword in error_str for keyword in [
            'limite de usuarios', 'user limit', 'maximum users',
            'máximo de usuarios', 'conexiones simultáneas'
        ]):
            return 'LOGIN_LIMIT'

        return 'DRIVER_CORRUPTO'
    
    def procesar_viaje_individual(self, viaje_registro):
        try:
            viaje_id = viaje_registro.get('id')
            datos_viaje = viaje_registro.get('datos_viaje', {})
            prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')

            # DETECCIÓN DE LOOP INFINITO: Verificar si este viaje se está procesando repetidamente
            if self.detectar_loop_infinito(prefactura, max_intentos_ventana=10, ventana_minutos=5):
                logger.error(f"ABORTANDO viaje {prefactura} por loop infinito detectado")
                robot_state_manager.incrementar_fallidos(prefactura, "Loop infinito detectado - más de 10 intentos en 5 minutos")
                debug_logger.log_viaje_fallo(prefactura, "loop_infinito", "Más de 10 intentos en 5 minutos")

                return 'VIAJE_FALLIDO', 'loop_infinito'

            # Marcar viaje como en proceso en estado_robots.json
            debug_logger.info(f"[{prefactura}] Paso 1/7: Marcando viaje como en proceso")
            robot_state_manager.marcar_viaje_actual(
                prefactura=prefactura,
                fase="Inicializando",
                placa_tractor=datos_viaje.get('placa_tractor', ''),
                placa_remolque=datos_viaje.get('placa_remolque', ''),
                determinante=datos_viaje.get('clave_determinante', '')
            )
            debug_logger.log_viaje_inicio(prefactura, datos_viaje)

            # LOGGING DETALLADO: Verificación de duplicados
            debug_logger.info(f"[{prefactura}] Paso 2/7: Verificando duplicados en viajes_log.csv")
            try:
                if viajes_log.verificar_viaje_existe(prefactura):
                    logger.warning(f"DUPLICADO DETECTADO: {prefactura} ya fue procesado - saltando")
                    debug_logger.warning(f"[{prefactura}] DUPLICADO encontrado en viajes_log.csv")
                    robot_state_manager.limpiar_viaje_actual()
                    return 'EXITOSO', 'duplicado_detectado'
                debug_logger.info(f"[{prefactura}] No es duplicado, continuando")
            except Exception as e:
                logger.error(f"Error verificando duplicados: {e}")
                debug_logger.error(f"[{prefactura}] ERROR verificando duplicados: {e}")

            logger.info(f"Procesando viaje: {prefactura}")

            # LOGGING DETALLADO: Verificación del driver
            debug_logger.info(f"[{prefactura}] Paso 3/7: Verificando estado del driver")
            if not self.driver:
                logger.info("No hay driver, creando nuevo...")
                debug_logger.warning(f"[{prefactura}] Driver es None, creando nuevo driver...")
                if not self.crear_driver_nuevo():
                    debug_logger.error(f"[{prefactura}] ERROR CRÍTICO: No se pudo crear driver nuevo")
                    if hasattr(self, 'ultimo_error_driver') and self.ultimo_error_driver:
                        tipo_error = self.detectar_tipo_error(self.ultimo_error_driver)
                        debug_logger.error(f"[{prefactura}] Tipo de error detectado: {tipo_error} - {self.ultimo_error_driver}")
                        return tipo_error, 'gm_login'
                    return 'DRIVER_CORRUPTO', 'gm_login'
                debug_logger.info(f"[{prefactura}] Driver nuevo creado exitosamente")
            else:
                debug_logger.info(f"[{prefactura}] Driver existente encontrado")

            # LOGGING DETALLADO: Verificación de URL
            debug_logger.info(f"[{prefactura}] Paso 4/7: Verificando URL del driver")
            try:
                current_url = self.driver.current_url
                debug_logger.info(f"[{prefactura}] URL actual: {current_url}")
                if "softwareparatransporte.com" not in current_url:
                    logger.warning("Driver en página incorrecta, recreando...")
                    debug_logger.warning(f"[{prefactura}] URL incorrecta, recreando driver...")
                    if not self.crear_driver_nuevo():
                        debug_logger.error(f"[{prefactura}] ERROR: No se pudo recrear driver después de URL incorrecta")
                        if hasattr(self, 'ultimo_error_driver') and self.ultimo_error_driver:
                            tipo_error = self.detectar_tipo_error(self.ultimo_error_driver)
                            debug_logger.error(f"[{prefactura}] Tipo de error: {tipo_error}")
                            return tipo_error, 'gm_login'
                        return 'DRIVER_CORRUPTO', 'gm_login'
                    debug_logger.info(f"[{prefactura}] Driver recreado exitosamente")
                else:
                    debug_logger.info(f"[{prefactura}] URL correcta, continuando")
            except Exception as e:
                logger.warning(f"Driver corrupto detectado: {e}")
                debug_logger.error(f"[{prefactura}] ERROR ACCEDIENDO A current_url: {e}")
                debug_logger.error(f"[{prefactura}] Recreando driver por error: {type(e).__name__}")
                if not self.crear_driver_nuevo():
                    debug_logger.error(f"[{prefactura}] ERROR CRÍTICO: No se pudo recrear driver después de excepción")
                    return 'DRIVER_CORRUPTO', 'selenium_driver'
                debug_logger.info(f"[{prefactura}] Driver recreado exitosamente después de excepción")

            # LOGGING DETALLADO: Creación de automation y llamada a fill_viaje_form
            debug_logger.info(f"[{prefactura}] Paso 5/7: Creando instancia de GMTransportAutomation")
            try:
                automation = GMTransportAutomation(self.driver)
                debug_logger.info(f"[{prefactura}] GMTransportAutomation creado exitosamente")

                debug_logger.info(f"[{prefactura}] Paso 6/7: Asignando datos del viaje")
                automation.datos_viaje = datos_viaje
                debug_logger.info(f"[{prefactura}] Datos asignados: Placa tractor={datos_viaje.get('placa_tractor')}, Remolque={datos_viaje.get('placa_remolque')}")

                debug_logger.info(f"[{prefactura}] Paso 7/7: Llamando a fill_viaje_form()")
                debug_logger.info(f"[{prefactura}] ========== INICIO FILL_VIAJE_FORM ==========")
                resultado = automation.fill_viaje_form()
                debug_logger.info(f"[{prefactura}] ========== FIN FILL_VIAJE_FORM - Resultado: {resultado} ==========")
                
                if resultado == "OPERADOR_OCUPADO":
                    logger.warning(f"Operador ocupado: {prefactura}")
                    self.driver = None
                    return 'VIAJE_FALLIDO', 'gm_salida'
                    
                elif resultado:
                    logger.info(f"Viaje completado exitosamente: {prefactura}")
                    logger.info("Datos completos (UUID, Viaje GM, placas) registrados automáticamente")
                    logger.info("MySQL sincronizado automáticamente desde CSV")

                    # Actualizar estado: viaje exitoso
                    robot_state_manager.incrementar_exitosos(prefactura)
                    debug_logger.log_viaje_exito(prefactura)

                    archivo_descargado = datos_viaje.get('archivo_descargado')
                    if archivo_descargado and os.path.exists(archivo_descargado):
                        os.remove(archivo_descargado)
                        logger.info(f"Archivo limpiado: {os.path.basename(archivo_descargado)}")

                    return 'EXITOSO', ''
                else:
                    logger.error(f"Error en automatización GM: {prefactura}")

                    # Leer motivo específico del CSV (la fuente de verdad)
                    mensaje_error = "Error durante creación del viaje"
                    try:
                        with open('viajes_log.csv', 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            viajes = list(reader)
                            # Buscar el último registro de esta prefactura que falló
                            for row in reversed(viajes):
                                if row['prefactura'] == str(prefactura) and row['estatus'] == 'FALLIDO':
                                    mensaje_error = row['motivo_fallo']
                                    break
                    except Exception as e:
                        logger.warning(f"No se pudo leer motivo del CSV: {e}")

                    robot_state_manager.incrementar_fallidos(prefactura, mensaje_error)
                    debug_logger.log_viaje_fallo(prefactura, "gm_transport_general", mensaje_error)
                    return 'VIAJE_FALLIDO', 'gm_transport_general'
                    
            except Exception as automation_error:
                logger.error(f"Error durante automatización: {automation_error}")
                debug_logger.error(f"[{prefactura}] EXCEPCIÓN CAPTURADA durante automatización")
                debug_logger.error(f"[{prefactura}] Tipo de excepción: {type(automation_error).__name__}")
                debug_logger.error(f"[{prefactura}] Mensaje: {str(automation_error)}")

                tipo_error = self.detectar_tipo_error(automation_error)
                debug_logger.warning(f"[{prefactura}] Tipo de error detectado: {tipo_error}")

                if tipo_error == 'LOGIN_LIMIT':
                    debug_logger.warning(f"[{prefactura}] ERROR: LOGIN_LIMIT - Límite de usuarios alcanzado")
                    robot_state_manager.limpiar_viaje_actual()
                    return 'LOGIN_LIMIT', 'gm_login'
                elif tipo_error == 'DRIVER_CORRUPTO':
                    debug_logger.error(f"[{prefactura}] ERROR: DRIVER_CORRUPTO - Cerrando driver")
                    try:
                        self.driver.quit()
                    except:
                        pass
                    finally:
                        self.driver = None
                    robot_state_manager.limpiar_viaje_actual()
                    return 'DRIVER_CORRUPTO', 'selenium_driver'
                else:
                    modulo_error = self.determinar_modulo_error(automation_error)
                    debug_logger.error(f"[{prefactura}] ERROR: VIAJE_FALLIDO en módulo {modulo_error}")
                    robot_state_manager.incrementar_fallidos(prefactura, f"Error durante automatización: {modulo_error}")
                    debug_logger.log_viaje_fallo(prefactura, modulo_error, str(automation_error))
                    return 'VIAJE_FALLIDO', modulo_error
                
        except Exception as e:
            logger.error(f"Error general procesando viaje: {e}")
            debug_logger.error(f"[{prefactura}] EXCEPCIÓN NO CAPTURADA en nivel superior")
            debug_logger.error(f"[{prefactura}] Tipo: {type(e).__name__}")
            debug_logger.error(f"[{prefactura}] Mensaje: {str(e)}")

            try:
                robot_state_manager.limpiar_viaje_actual()
                robot_state_manager.incrementar_fallidos(prefactura, f"Error general: {str(e)}")
                debug_logger.log_viaje_fallo(prefactura, 'sistema_general', str(e))
            except:
                pass
            return 'VIAJE_FALLIDO', 'sistema_general'
    
    def determinar_modulo_error(self, error):
        error_str = str(error).lower()
        
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
        try:
            logger.info("Iniciando procesamiento de cola de viajes...")
            
            while True:
                viaje_registro = obtener_siguiente_viaje_cola()
                
                if not viaje_registro:
                    logger.info("No hay más viajes en cola")
                    break
                
                viaje_id = viaje_registro.get('id')
                datos_viaje = viaje_registro.get('datos_viaje', {})
                prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
                
                resultado, modulo_error = self.procesar_viaje_individual(viaje_registro)
                
                if resultado == 'EXITOSO':
                    marcar_viaje_exitoso_cola(viaje_id)
                    logger.info(f"Viaje {prefactura} completado y removido de cola")
                    
                    logger.info("Esperando 1 minuto antes del siguiente viaje...")
                    time.sleep(60)
                    
                elif resultado == 'LOGIN_LIMIT':
                    registrar_error_reintentable_cola(viaje_id, 'LOGIN_LIMIT', f'Límite de usuarios en {modulo_error}')
                    logger.warning(f"Límite de usuarios - {prefactura} reintentará en 15 minutos")
                    
                    logger.info("Esperando 15 minutos por límite de usuarios...")
                    time.sleep(15 * 60)
                    
                elif resultado == 'DRIVER_CORRUPTO':
                    registrar_error_reintentable_cola(viaje_id, 'DRIVER_CORRUPTO', f'Driver corrupto en {modulo_error}')
                    logger.warning(f"Driver corrupto - {prefactura} reintentará inmediatamente")
                    
                else:
                    motivo_detallado = f"PROCESO FALLÓ EN: {modulo_error}"
                    marcar_viaje_fallido_cola(viaje_id, modulo_error, motivo_detallado)
                    logger.error(f"{prefactura} FALLÓ EN: {modulo_error} - removido de cola")
                    
                    logger.info("Esperando 30 segundos después de viaje fallido...")
                    time.sleep(30)
            
        except KeyboardInterrupt:
            logger.info("Interrupción manual del procesamiento")
        except Exception as e:
            logger.error(f"Error en procesamiento de cola: {e}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                finally:
                    self.driver = None
    
    def mostrar_estadisticas_inicio(self):
        try:
            stats_cola = obtener_estadisticas_cola()
            logger.info(f"Cola: {stats_cola.get('total_viajes', 0)} | Pendientes: {stats_cola.get('pendientes', 0)} | Procesando: {stats_cola.get('procesando', 0)}")
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de cola: {e}")
    
    def ejecutar_bucle_continuo(self, mostrar_debug=False):
        from cola_viajes import resetear_viajes_atascados
        viajes_reseteados = resetear_viajes_atascados()
        if viajes_reseteados > 0:
            logger.warning(f"Se resetearon {viajes_reseteados} viajes atascados")

        robot_state_manager.actualizar_estado_robot("ejecutando")
        debug_logger.info("Iniciando bucle continuo de automatización")

        self.mostrar_estadisticas_inicio()

        try:
            contador_ciclos = 0
            contador_sync_mysql = 0
            ultimo_sync_mysql = time.time()
            ultima_cant_viajes = -1  # Para tracking de cambios en cola

            while AlsuaMailAutomation.continuar_ejecutando:
                # La variable de clase controla la ejecución

                try:
                    contador_ciclos += 1
                    if mostrar_debug:
                        logger.info(f"Ciclo #{contador_ciclos}")

                    # Verificar viajes stuck (timeout: 10 minutos)
                    try:
                        limpiado, mensaje = robot_state_manager.verificar_y_limpiar_viaje_stuck(timeout_minutos=10)
                        if limpiado:
                            logger.error(mensaje)
                            debug_logger.error(mensaje)
                            # Si se limpió un viaje stuck, agregar pausa para estabilidad
                            time.sleep(30)
                    except Exception as e:
                        logger.warning(f"Error verificando viajes stuck: {e}")

                    viaje_registro = obtener_siguiente_viaje_cola()

                    # Actualizar cola en estado_robots.json (solo si cambia)
                    try:
                        from cola_viajes import leer_cola
                        cola_actual = leer_cola()
                        viajes = cola_actual.get('viajes', [])
                        cant_actual = len(viajes)

                        # Solo actualizar si la cantidad cambió
                        if cant_actual != ultima_cant_viajes:
                            if cant_actual > 0:
                                viajes_pendientes = [
                                    {
                                        'prefactura': v.get('datos_viaje', {}).get('prefactura', 'N/A'),
                                        'fecha': v.get('datos_viaje', {}).get('fecha', 'N/A'),
                                        'placa_tractor': v.get('datos_viaje', {}).get('placa_tractor', 'N/A'),
                                        'placa_remolque': v.get('datos_viaje', {}).get('placa_remolque', 'N/A')
                                    }
                                    for v in viajes
                                    if v.get('estado') in ['pendiente', 'procesando']
                                ]
                                robot_state_manager.actualizar_cola(viajes_pendientes)
                            else:
                                robot_state_manager.actualizar_cola([])

                            ultima_cant_viajes = cant_actual
                    except:
                        pass

                    if viaje_registro:
                        viaje_id = viaje_registro.get('id')
                        datos_viaje = viaje_registro.get('datos_viaje', {})
                        prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')

                        logger.info(f"Procesando: {prefactura}")

                        resultado, modulo_error = self.procesar_viaje_individual(viaje_registro)

                        if resultado == 'EXITOSO':
                            marcar_viaje_exitoso_cola(viaje_id)
                            robot_state_manager.limpiar_viaje_actual()
                            logger.info(f"{prefactura} COMPLETADO")
                            contador_sync_mysql += 1
                            time.sleep(60)

                        elif resultado == 'LOGIN_LIMIT':
                            registrar_error_reintentable_cola(viaje_id, 'LOGIN_LIMIT', f'Límite de usuarios en {modulo_error}')
                            logger.warning(f"LOGIN LÍMITE - {prefactura}")
                            time.sleep(15 * 60)

                        elif resultado == 'DRIVER_CORRUPTO':
                            registrar_error_reintentable_cola(viaje_id, 'DRIVER_CORRUPTO', f'Driver corrupto en {modulo_error}')
                            robot_state_manager.limpiar_viaje_actual()
                            logger.warning(f"DRIVER CORRUPTO - {prefactura}")

                        else:
                            motivo_detallado = f"PROCESO FALLÓ EN: {modulo_error}"
                            marcar_viaje_fallido_cola(viaje_id, modulo_error, motivo_detallado)
                            robot_state_manager.limpiar_viaje_actual()
                            logger.error(f"{prefactura} FALLÓ: {modulo_error}")
                            contador_sync_mysql += 1
                            time.sleep(30)

                        # Batch MySQL sync: cada 5 viajes o cada 10 minutos
                        ahora = time.time()
                        if contador_sync_mysql >= 5 or (ahora - ultimo_sync_mysql) > 600:
                            from modules.mysql_simple import sincronizar_csv_a_mysql
                            sincronizar_csv_a_mysql()
                            contador_sync_mysql = 0
                            ultimo_sync_mysql = ahora
                    
                    else:
                        viajes_encontrados = self.revisar_y_extraer_correos(limite_viajes=3)

                        if viajes_encontrados:
                            logger.info(f"Nuevos viajes agregados a cola: {viajes_encontrados}")
                        else:
                            time.sleep(10)

                    # Limpieza zombie automática cada 100 ciclos (~1 hora)
                    if contador_ciclos % 100 == 0:
                        try:
                            from cola_viajes import limpiar_viajes_zombie
                            eliminados = limpiar_viajes_zombie()
                            if eliminados > 0:
                                logger.warning(f"Limpieza zombie: {eliminados} viajes eliminados")
                        except:
                            pass

                    if contador_ciclos % 10 == 0:
                        try:
                            stats = obtener_estadisticas_cola()
                            if stats.get('total_viajes', 0) > 0:
                                logger.info(f"Cola actual: {stats.get('pendientes', 0)} pendientes")
                        except:
                            pass
                    
                except KeyboardInterrupt:
                    logger.info("Interrupción manual detectada")
                    break
                    
                except Exception as e:
                    logger.error(f"Error en ciclo continuo: {e}")
                    logger.info("Continuando con siguiente ciclo en 30 segundos...")
                    time.sleep(30)
                    
        except KeyboardInterrupt:
            logger.info("Sistema detenido por usuario")

        finally:
            # Sync final de MySQL antes de cerrar
            try:
                from modules.mysql_simple import sincronizar_csv_a_mysql
                sincronizar_csv_a_mysql()
            except:
                pass

            robot_state_manager.limpiar_viaje_actual()
            robot_state_manager.actualizar_estado_robot("detenido")
            debug_logger.info("Bucle continuo finalizado")

            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

            self.limpiar_com()

            logger.info("Sistema de automatización finalizado")
    
    def ejecutar_revision_unica(self):
        logger.info("Ejecutando revisión única...")
        logger.info("MODO TEST: Solo algunos ciclos para inspección")
        
        self.mostrar_estadisticas_inicio()
        
        try:
            ciclos_max = 5
            logger.info(f"Ejecutando máximo {ciclos_max} ciclos de prueba...")
            
            for ciclo in range(ciclos_max):
                logger.info(f"Ciclo de prueba {ciclo + 1}/{ciclos_max}")
                
                viajes_encontrados = self.revisar_y_extraer_correos()
                
                if viajes_encontrados:
                    logger.info("Nuevos viajes encontrados en modo test")
                
                viaje_registro = obtener_siguiente_viaje_cola()
                
                if viaje_registro:
                    prefactura = viaje_registro.get('datos_viaje', {}).get('prefactura', 'DESCONOCIDA')
                    logger.info(f"MODO TEST: Procesando viaje {prefactura}")
                    
                    resultado, modulo_error = self.procesar_viaje_individual(viaje_registro)
                    logger.info(f"Resultado test: {resultado} en {modulo_error}")
                    
                    viaje_id = viaje_registro.get('id')
                    if resultado == 'EXITOSO':
                        marcar_viaje_exitoso_cola(viaje_id)
                        logger.info("Viaje test completado")
                        break
                    elif resultado in ['LOGIN_LIMIT', 'DRIVER_CORRUPTO']:
                        registrar_error_reintentable_cola(viaje_id, resultado, f'Error test en {modulo_error}')
                        logger.warning(f"Error reintentable en test: {resultado}")
                    else:
                        marcar_viaje_fallido_cola(viaje_id, modulo_error, f"Test falló en {modulo_error}")
                        logger.error(f"Viaje test falló en: {modulo_error}")
                        break
                else:
                    logger.info("No hay viajes en cola para test")
                
                if ciclo < ciclos_max - 1:
                    logger.info("Pausa entre ciclos de test...")
                    time.sleep(10)
            
            try:
                stats = obtener_estadisticas_cola()
                logger.info("Estadísticas finales del test:")
                logger.info(f"   Total viajes: {stats.get('total_viajes', 0)}")
                logger.info(f"   Pendientes: {stats.get('pendientes', 0)}")
                logger.info(f"   Procesando: {stats.get('procesando', 0)}")
            except Exception as e:
                logger.warning(f"Error obteniendo estadísticas finales: {e}")
            
            logger.info("Revisión única de test completada")
            return True
            
        except Exception as e:
            logger.error(f"Error en revisión única: {e}")
            return False
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            self.limpiar_com()
    
    def mostrar_estadisticas(self):
        try:
            stats = viajes_log.obtener_estadisticas()
            logger.info(f"Total: {stats['total_viajes']} | Exitosos: {stats['exitosos']} | Fallidos: {stats['fallidos']}")
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas CSV: {e}")

        try:
            stats_cola = obtener_estadisticas_cola()
            logger.info(f"Cola: {stats_cola.get('total_viajes', 0)} viajes | Pendientes: {stats_cola.get('pendientes', 0)} | Procesando: {stats_cola.get('procesando', 0)}")
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de cola: {e}")

def main():
    sistema = AlsuaMailAutomation()

    sistema.mostrar_estadisticas()

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logger.info("MODO PRUEBA: Ejecutando revisión de test...")
        sistema.ejecutar_revision_unica()
    else:
        sistema.ejecutar_bucle_continuo(mostrar_debug=False)

if __name__ == "__main__":
    main()