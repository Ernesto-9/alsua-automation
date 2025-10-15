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
    def __init__(self):
        self.carpeta_descarga = os.path.abspath("archivos_descargados")
        
        self.driver = None
        
        self.com_inicializado = False
        
        self._crear_carpeta_descarga()
        
    def _crear_carpeta_descarga(self):
        try:
            if not os.path.exists(self.carpeta_descarga):
                os.makedirs(self.carpeta_descarga)
                logger.info(f"Carpeta creada: {self.carpeta_descarga}")
            else:
                logger.info(f"Carpeta existe: {self.carpeta_descarga}")
                
            test_file = os.path.join(self.carpeta_descarga, "test_permisos.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                logger.info("Permisos de escritura verificados")
            except Exception as e:
                logger.error(f"Error de permisos en carpeta: {e}")
                self.carpeta_descarga = os.path.join(os.path.expanduser("~"), "Downloads", "alsua_archivos")
                os.makedirs(self.carpeta_descarga, exist_ok=True)
                logger.info(f"Usando carpeta alternativa: {self.carpeta_descarga}")
                
        except Exception as e:
            logger.error(f"Error al crear carpeta: {e}")
            self.carpeta_descarga = os.path.join(os.path.expanduser("~"), "Downloads", "alsua_archivos")
            os.makedirs(self.carpeta_descarga, exist_ok=True)
            logger.info(f"Carpeta fallback: {self.carpeta_descarga}")
    
    def inicializar_com(self):
        try:
            if not self.com_inicializado:
                logger.info("Inicializando COM para thread actual...")
                pythoncom.CoInitialize()
                self.com_inicializado = True
                logger.info("COM inicializado exitosamente")
                return True
        except Exception as e:
            logger.error(f"Error inicializando COM: {e}")
            return False
    
    def limpiar_com(self):
        try:
            if self.com_inicializado:
                logger.info("Limpiando inicialización COM...")
                pythoncom.CoUninitialize()
                self.com_inicializado = False
                logger.info("COM limpiado exitosamente")
        except Exception as e:
            logger.warning(f"Error limpiando COM: {e}")
    
    def ya_fue_procesado_correo_csv(self, mensaje):
        try:
            prefactura = self.extraer_prefactura_del_asunto(mensaje.Subject or "")
            if not prefactura:
                return False
            
            viaje_existente = viajes_log.verificar_viaje_existe(prefactura)
            
            if viaje_existente:
                logger.info(f"Correo ya procesado (encontrado en CSV): {prefactura}")
                logger.info(f"   Estatus en CSV: {viaje_existente.get('estatus')}")
                logger.info(f"   Timestamp: {viaje_existente.get('timestamp')}")
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
                
                logger.info("Viaje VACIO válido extraído:")
                logger.info(f"   Prefactura: {resultado['prefactura']}")
                logger.info(f"   Fecha: {resultado['fecha']}")
                logger.info(f"   Placa Tractor: {resultado['placa_tractor']}")
                logger.info(f"   Placa Remolque: {resultado['placa_remolque']}")
                logger.info(f"   Determinante: {resultado['clave_determinante']}")
                logger.info(f"   Importe: ${resultado['importe']}")
                
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
                    
                    logger.info(f"Extrayendo viaje: {prefactura}")
                    datos_viaje = self.extraer_datos_de_correo(mensaje)
                    
                    if datos_viaje:
                        # VALIDACIÓN DEFENSIVA AGREGADA
                        if isinstance(datos_viaje, list):
                            logger.error(f"ERROR CRÍTICO: datos_viaje es una lista cuando debería ser dict")
                            logger.error(f"Contenido: {datos_viaje}")
                            correos_saltados += 1
                            continue
                        
                        if not isinstance(datos_viaje, dict):
                            logger.error(f"ERROR CRÍTICO: datos_viaje no es dict. Tipo: {type(datos_viaje)}")
                            logger.error(f"Contenido: {datos_viaje}")
                            correos_saltados += 1
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
                return True
            else:
                logger.error("Error en login GM")
                return False
                
        except Exception as e:
            logger.error(f"Error crítico creando driver: {e}")
            self.driver = None
            return False
    
    def detectar_tipo_error(self, error):
        error_str = str(error).lower()
        
        if any(keyword in error_str for keyword in ['limit', 'limite', 'usuarios', 'user limit', 'maximum', 'conexiones']):
            return 'LOGIN_LIMIT'
        
        if any(keyword in error_str for keyword in ['invalid session', 'chrome not reachable', 'no such window', 'session deleted', 'connection refused']):
            return 'DRIVER_CORRUPTO'
        
        return 'VIAJE_FALLIDO'
    
    def procesar_viaje_individual(self, viaje_registro):
        try:
            viaje_id = viaje_registro.get('id')
            datos_viaje = viaje_registro.get('datos_viaje', {})
            prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')

            # Marcar viaje como en proceso en estado_robots.json
            robot_state_manager.marcar_viaje_actual(
                prefactura=prefactura,
                fase="Inicializando",
                placa_tractor=datos_viaje.get('placa_tractor', ''),
                placa_remolque=datos_viaje.get('placa_remolque', ''),
                determinante=datos_viaje.get('clave_determinante', '')
            )
            debug_logger.log_viaje_inicio(prefactura, datos_viaje)

            if viajes_log.verificar_viaje_existe(prefactura):
                logger.warning(f"DUPLICADO DETECTADO: {prefactura} ya fue procesado - saltando")
                robot_state_manager.limpiar_viaje_actual()
                return 'EXITOSO', 'duplicado_detectado'

            logger.info(f"Procesando viaje: {prefactura}")
            
            if not self.driver:
                logger.info("No hay driver, creando nuevo...")
                if not self.crear_driver_nuevo():
                    return 'LOGIN_LIMIT', 'gm_login'
            
            try:
                current_url = self.driver.current_url
                if "softwareparatransporte.com" not in current_url:
                    logger.warning("Driver en página incorrecta, recreando...")
                    if not self.crear_driver_nuevo():
                        return 'LOGIN_LIMIT', 'gm_login'
            except Exception as e:
                logger.warning(f"Driver corrupto detectado: {e}")
                if not self.crear_driver_nuevo():
                    return 'DRIVER_CORRUPTO', 'selenium_driver'
            
            try:
                automation = GMTransportAutomation(self.driver)
                automation.datos_viaje = datos_viaje
                
                resultado = automation.fill_viaje_form()
                
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
                    robot_state_manager.incrementar_fallidos(prefactura, "Error en automatización GM")
                    debug_logger.log_viaje_fallo(prefactura, "gm_transport_general", "Error en automatización")
                    return 'VIAJE_FALLIDO', 'gm_transport_general'
                    
            except Exception as automation_error:
                logger.error(f"Error durante automatización: {automation_error}")
                
                tipo_error = self.detectar_tipo_error(automation_error)
                
                if tipo_error == 'LOGIN_LIMIT':
                    robot_state_manager.limpiar_viaje_actual()
                    return 'LOGIN_LIMIT', 'gm_login'
                elif tipo_error == 'DRIVER_CORRUPTO':
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
                    robot_state_manager.incrementar_fallidos(prefactura, f"Error durante automatización: {modulo_error}")
                    debug_logger.log_viaje_fallo(prefactura, modulo_error, str(automation_error))
                    return 'VIAJE_FALLIDO', modulo_error
                
        except Exception as e:
            logger.error(f"Error general procesando viaje: {e}")
            try:
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
        logger.info("Estado inicial del sistema:")
        
        try:
            stats_cola = obtener_estadisticas_cola()
            logger.info(f"   Viajes en cola: {stats_cola.get('total_viajes', 0)}")
            logger.info(f"   Pendientes: {stats_cola.get('pendientes', 0)}")
            logger.info(f"   Procesando: {stats_cola.get('procesando', 0)}")
            
            if stats_cola.get('viajes_con_errores', 0) > 0:
                logger.info(f"   Con errores: {stats_cola.get('viajes_con_errores', 0)}")
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de cola: {e}")
    
    def ejecutar_bucle_continuo(self, mostrar_debug=False):
        logger.info("Iniciando sistema de automatización Alsua Transport")
        logger.info("FLUJO:")
        logger.info("   PRIORIDAD 1: Procesar cola existente")
        logger.info("   PRIORIDAD 2: Si cola vacía → buscar nuevos correos")
        logger.info("   RESULTADO: 1 viaje a la vez, sin acumulación")
        logger.info("=" * 70)

        # Marcar robot como ejecutando
        robot_state_manager.actualizar_estado_robot("ejecutando")
        debug_logger.info("Iniciando bucle continuo de automatización")

        self.mostrar_estadisticas_inicio()

        # Importar estado del sistema Flask si está disponible
        try:
            from app import sistema_estado
            flask_disponible = True
        except:
            flask_disponible = False
            sistema_estado = None

        try:
            contador_ciclos = 0
            while True:
                # Verificar si Flask pidió detener
                if flask_disponible and sistema_estado and not sistema_estado.get("ejecutando", True):
                    logger.info("🛑 Detención solicitada desde panel web")
                    break

                try:
                    contador_ciclos += 1
                    if mostrar_debug:
                        logger.info(f"Ciclo #{contador_ciclos}")
                    
                    viaje_registro = obtener_siguiente_viaje_cola()

                    # Actualizar cola en estado_robots.json
                    try:
                        stats = obtener_estadisticas_cola()
                        if stats.get('total_viajes', 0) > 0:
                            # Obtener lista de viajes pendientes para el panel
                            from cola_viajes import leer_cola
                            cola_actual = leer_cola()
                            viajes_pendientes = [
                                {
                                    'prefactura': v.get('datos_viaje', {}).get('prefactura', 'N/A'),
                                    'fecha': v.get('datos_viaje', {}).get('fecha', 'N/A'),
                                    'placa_tractor': v.get('datos_viaje', {}).get('placa_tractor', 'N/A'),
                                    'placa_remolque': v.get('datos_viaje', {}).get('placa_remolque', 'N/A')
                                }
                                for v in cola_actual.get('viajes', [])
                                if v.get('estatus') in ['pendiente', 'procesando']
                            ]
                            robot_state_manager.actualizar_cola(viajes_pendientes)
                    except:
                        pass

                    if viaje_registro:
                        viaje_id = viaje_registro.get('id')
                        datos_viaje = viaje_registro.get('datos_viaje', {})
                        prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
                        
                        logger.info(f"PROCESANDO VIAJE DE COLA: {prefactura}")
                        
                        resultado, modulo_error = self.procesar_viaje_individual(viaje_registro)
                        
                        if resultado == 'EXITOSO':
                            marcar_viaje_exitoso_cola(viaje_id)
                            logger.info(f"Viaje {prefactura} COMPLETADO - removido de cola")
                            logger.info("Esperando 1 minuto antes de continuar...")
                            time.sleep(60)
                            
                        elif resultado == 'LOGIN_LIMIT':
                            registrar_error_reintentable_cola(viaje_id, 'LOGIN_LIMIT', f'Límite de usuarios en {modulo_error}')
                            logger.warning(f"LOGIN LÍMITE - {prefactura} reintentará en 15 minutos")
                            logger.info("Esperando 15 minutos por límite de usuarios...")
                            time.sleep(15 * 60)
                            
                        elif resultado == 'DRIVER_CORRUPTO':
                            registrar_error_reintentable_cola(viaje_id, 'DRIVER_CORRUPTO', f'Driver corrupto en {modulo_error}')
                            logger.warning(f"DRIVER CORRUPTO - {prefactura} reintentará inmediatamente")
                            
                        else:
                            motivo_detallado = f"PROCESO FALLÓ EN: {modulo_error}"
                            marcar_viaje_fallido_cola(viaje_id, modulo_error, motivo_detallado)
                            logger.error(f"{prefactura} FALLÓ EN: {modulo_error} - removido de cola")
                            logger.info("Esperando 30 segundos después de viaje fallido...")
                            time.sleep(30)
                    
                    else:
                        if mostrar_debug:
                            logger.info("Cola vacía - buscando nuevos correos...")
                        
                        viajes_encontrados = self.revisar_y_extraer_correos(limite_viajes=3)
                        
                        if viajes_encontrados:
                            logger.info("Nuevos viajes VACIO encontrados y agregados a cola")
                        else:
                            if mostrar_debug:
                                logger.info("No se encontraron nuevos viajes VACIO")
                            time.sleep(10)
                    
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
            # Marcar robot como detenido
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
        logger.info("ESTADÍSTICAS DEL SISTEMA:")
        logger.info("   Sistema de cola persistente JSON")
        logger.info("   Reintentos selectivos inteligentes")
        logger.info("   Proceso GM completo automatizado")
        logger.info("   Extracción automática PDF")
        logger.info("   Registro CSV + MySQL")
        logger.info("   Compatible con interfaz web")
        
        try:
            stats = viajes_log.obtener_estadisticas()
            logger.info(f"   Total viajes en CSV: {stats['total_viajes']}")
            logger.info(f"   Exitosos: {stats['exitosos']}")
            logger.info(f"   Fallidos: {stats['fallidos']}")
            if stats['ultimo_viaje']:
                logger.info(f"   Último viaje: {stats['ultimo_viaje']}")
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas CSV: {e}")
        
        try:
            stats_cola = obtener_estadisticas_cola()
            logger.info(f"   Viajes en cola: {stats_cola.get('total_viajes', 0)}")
            logger.info(f"   Pendientes: {stats_cola.get('pendientes', 0)}")
            logger.info(f"   Procesando: {stats_cola.get('procesando', 0)}")
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de cola: {e}")

def main():
    print("Sistema de Automatización Alsua Transport")
    print("Procesamiento automático de viajes de carga")
    print("Flujo continuo con cola persistente")
    print("=" * 50)
    
    sistema = AlsuaMailAutomation()
    
    sistema.mostrar_estadisticas()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logger.info("MODO PRUEBA: Ejecutando revisión de test...")
        sistema.ejecutar_revision_unica()
    else:
        logger.info("MODO PRODUCCIÓN: Iniciando flujo continuo")
        logger.info("PROCESAMIENTO PERPETUO:")
        logger.info("   Revisar correos → Viaje VACIO → Cola → Procesar")
        logger.info("   Sin intervalos fijos innecesarios")
        logger.info("   Máxima robustez con cola persistente")
        logger.info("   Solo 2 errores reintentables")
        logger.info("Compatible con interfaz web Flask")
        sistema.ejecutar_bucle_continuo(mostrar_debug=False)

if __name__ == "__main__":
    main()