"""
Procesador de viajes individuales de Walmart
Coordina la automatización de un viaje desde inicio hasta fin
"""
import os
import csv
import logging

logger = logging.getLogger(__name__)

class TripProcessor:
    """Procesa un viaje individual a través del sistema GM"""

    def __init__(self, driver_manager, viajes_log, robot_state_manager, debug_logger):
        """
        Args:
            driver_manager: Instancia de DriverManager
            viajes_log: Instancia de ViajesLog para registro
            robot_state_manager: Gestor de estado del robot
            debug_logger: Logger de debug
        """
        self.driver_manager = driver_manager
        self.viajes_log = viajes_log
        self.robot_state_manager = robot_state_manager
        self.debug_logger = debug_logger

    def determinar_modulo_error(self, error):
        """
        Determina qué módulo causó el error basado en el mensaje

        Args:
            error: Exception o string con el error

        Returns:
            str: Nombre del módulo que causó el error
        """
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

    def procesar_viaje(self, viaje_registro, gm_automation_class):
        """
        Procesa un viaje individual completo

        Args:
            viaje_registro: Dict con datos del viaje de la cola
            gm_automation_class: Clase GMTransportAutomation

        Returns:
            tuple: (resultado, modulo_error) donde resultado es:
                   'EXITOSO', 'VIAJE_FALLIDO', 'DRIVER_CORRUPTO', 'LOGIN_LIMIT'
        """
        try:
            viaje_id = viaje_registro.get('id')
            datos_viaje = viaje_registro.get('datos_viaje', {})
            prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')

            # Marcar viaje como en proceso
            self.robot_state_manager.marcar_viaje_actual(
                prefactura=prefactura,
                fase="Inicializando",
                placa_tractor=datos_viaje.get('placa_tractor', ''),
                placa_remolque=datos_viaje.get('placa_remolque', ''),
                determinante=datos_viaje.get('clave_determinante', '')
            )
            self.debug_logger.log_viaje_inicio(prefactura, datos_viaje)

            # Verificar duplicados
            try:
                if self.viajes_log.verificar_viaje_existe(prefactura):
                    logger.warning(f"DUPLICADO DETECTADO: {prefactura} ya fue procesado - saltando")
                    self.robot_state_manager.limpiar_viaje_actual()
                    return 'EXITOSO', 'duplicado_detectado'
            except Exception as e:
                logger.error(f"Error verificando duplicados: {e}")

            logger.info(f"Procesando viaje: {prefactura}")

            # Validar o crear driver
            if not self.driver_manager.driver:
                logger.info("No hay driver, creando nuevo...")
                if not self.driver_manager.crear_driver_nuevo():
                    if self.driver_manager.ultimo_error_driver:
                        tipo_error = self.driver_manager.detectar_tipo_error(
                            self.driver_manager.ultimo_error_driver
                        )
                        return tipo_error, 'gm_login'
                    return 'DRIVER_CORRUPTO', 'gm_login'

            # Validar que el driver esté en página correcta
            if not self.driver_manager.validar_driver():
                if not self.driver_manager.crear_driver_nuevo():
                    if self.driver_manager.ultimo_error_driver:
                        tipo_error = self.driver_manager.detectar_tipo_error(
                            self.driver_manager.ultimo_error_driver
                        )
                        return tipo_error, 'gm_login'
                    return 'DRIVER_CORRUPTO', 'gm_login'

            # Ejecutar automatización GM
            try:
                automation = gm_automation_class(self.driver_manager.driver)
                automation.datos_viaje = datos_viaje

                resultado = automation.fill_viaje_form()

                if resultado == "OPERADOR_OCUPADO":
                    logger.warning(f"Operador ocupado: {prefactura}")
                    self.driver_manager.driver = None
                    return 'VIAJE_FALLIDO', 'gm_salida'

                elif resultado:
                    logger.info(f"Viaje completado exitosamente: {prefactura}")
                    logger.info("Datos completos (UUID, Viaje GM, placas) registrados automáticamente")
                    logger.info("MySQL sincronizado automáticamente desde CSV")

                    # Actualizar estado: viaje exitoso
                    self.robot_state_manager.incrementar_exitosos(prefactura)
                    self.debug_logger.log_viaje_exito(prefactura)

                    # Limpiar archivo descargado
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

                    self.robot_state_manager.incrementar_fallidos(prefactura, mensaje_error)
                    self.debug_logger.log_viaje_fallo(prefactura, "gm_transport_general", mensaje_error)
                    return 'VIAJE_FALLIDO', 'gm_transport_general'

            except Exception as automation_error:
                logger.error(f"Error durante automatización: {automation_error}")

                tipo_error = self.driver_manager.detectar_tipo_error(automation_error)

                if tipo_error == 'LOGIN_LIMIT':
                    self.robot_state_manager.limpiar_viaje_actual()
                    return 'LOGIN_LIMIT', 'gm_login'
                elif tipo_error == 'DRIVER_CORRUPTO':
                    self.driver_manager.limpiar_driver()
                    self.robot_state_manager.limpiar_viaje_actual()
                    return 'DRIVER_CORRUPTO', 'selenium_driver'
                else:
                    modulo_error = self.determinar_modulo_error(automation_error)
                    self.robot_state_manager.incrementar_fallidos(
                        prefactura,
                        f"Error durante automatización: {modulo_error}"
                    )
                    self.debug_logger.log_viaje_fallo(prefactura, modulo_error, str(automation_error))
                    return 'VIAJE_FALLIDO', modulo_error

        except Exception as e:
            logger.error(f"Error general procesando viaje: {e}")
            try:
                self.robot_state_manager.limpiar_viaje_actual()
                self.robot_state_manager.incrementar_fallidos(prefactura, f"Error general: {str(e)}")
                self.debug_logger.log_viaje_fallo(prefactura, 'sistema_general', str(e))
            except:
                pass
            return 'VIAJE_FALLIDO', 'sistema_general'
