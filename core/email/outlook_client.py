import os
import re
import logging
from datetime import datetime
import win32com.client
import pythoncom

logger = logging.getLogger(__name__)

class OutlookEmailClient:
    def __init__(self):
        self.com_inicializado = False
        self.emails_fallidos = {}

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

    def ya_fue_procesado_correo_csv(self, mensaje, viajes_log):
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

    def extraer_datos_de_correo(self, mensaje, carpeta_descarga, parse_xls, viajes_log):
        try:
            if self.ya_fue_procesado_correo_csv(mensaje, viajes_log):
                logger.info("Saltando correo ya procesado (encontrado en CSV)")
                mensaje.UnRead = False
                return None

            asunto = mensaje.Subject or ""
            remitente = mensaje.SenderEmailAddress or ""

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
                ruta_local = os.path.join(carpeta_descarga, nombre_unico)

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

    def revisar_y_extraer_correos(self, carpeta_descarga, parse_xls, viajes_log, agregar_viaje_a_cola, limite_viajes=3):
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
                    datos_viaje = self.extraer_datos_de_correo(mensaje, carpeta_descarga, parse_xls, viajes_log)

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
