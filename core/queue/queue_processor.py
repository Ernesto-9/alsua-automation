"""
Procesador de la cola de viajes
Gestiona el flujo de viajes desde la cola hasta su procesamiento
"""
import time
import logging

logger = logging.getLogger(__name__)

class QueueProcessor:
    """Procesa viajes de la cola de manera continua"""

    def __init__(self, trip_processor, cola_functions, robot_state_manager):
        """
        Args:
            trip_processor: Instancia de TripProcessor
            cola_functions: Dict con funciones de la cola
            robot_state_manager: Gestor de estado del robot
        """
        self.trip_processor = trip_processor
        self.cola_functions = cola_functions
        self.robot_state_manager = robot_state_manager

    def procesar_cola_simple(self, gm_automation_class):
        """
        Procesa todos los viajes en cola de manera simple (sin bucle continuo)

        Args:
            gm_automation_class: Clase GMTransportAutomation

        Returns:
            bool: True si procesó al menos un viaje
        """
        try:
            logger.info("Iniciando procesamiento de cola de viajes...")

            while True:
                viaje_registro = self.cola_functions['obtener_siguiente']()

                if not viaje_registro:
                    logger.info("No hay más viajes en cola")
                    break

                viaje_id = viaje_registro.get('id')
                datos_viaje = viaje_registro.get('datos_viaje', {})
                prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')

                resultado, modulo_error = self.trip_processor.procesar_viaje(
                    viaje_registro,
                    gm_automation_class
                )

                if resultado == 'EXITOSO':
                    self.cola_functions['marcar_exitoso'](viaje_id)
                    logger.info(f"Viaje {prefactura} completado y removido de cola")

                    logger.info("Esperando 1 minuto antes del siguiente viaje...")
                    time.sleep(60)

                elif resultado == 'LOGIN_LIMIT':
                    self.cola_functions['registrar_error'](
                        viaje_id,
                        'LOGIN_LIMIT',
                        f'Límite de usuarios en {modulo_error}'
                    )
                    logger.warning(f"Límite de usuarios - {prefactura} reintentará en 15 minutos")

                    logger.info("Esperando 15 minutos por límite de usuarios...")
                    time.sleep(15 * 60)

                elif resultado == 'DRIVER_CORRUPTO':
                    self.cola_functions['registrar_error'](
                        viaje_id,
                        'DRIVER_CORRUPTO',
                        f'Driver corrupto en {modulo_error}'
                    )
                    logger.warning(f"Driver corrupto - {prefactura} reintentará inmediatamente")

                else:
                    motivo_detallado = f"PROCESO FALLÓ EN: {modulo_error}"
                    self.cola_functions['marcar_fallido'](viaje_id, modulo_error, motivo_detallado)
                    logger.error(f"{prefactura} FALLÓ EN: {modulo_error} - removido de cola")

                    logger.info("Esperando 30 segundos después de viaje fallido...")
                    time.sleep(30)

            return True

        except KeyboardInterrupt:
            logger.info("Interrupción manual del procesamiento")
            return False
        except Exception as e:
            logger.error(f"Error en procesamiento de cola: {e}")
            return False

    def procesar_un_viaje(self, gm_automation_class):
        """
        Procesa un solo viaje de la cola

        Args:
            gm_automation_class: Clase GMTransportAutomation

        Returns:
            tuple: (resultado, modulo_error, prefactura)
        """
        viaje_registro = self.cola_functions['obtener_siguiente']()

        if not viaje_registro:
            return None, None, None

        viaje_id = viaje_registro.get('id')
        datos_viaje = viaje_registro.get('datos_viaje', {})
        prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')

        logger.info(f"Procesando: {prefactura}")

        resultado, modulo_error = self.trip_processor.procesar_viaje(
            viaje_registro,
            gm_automation_class
        )

        # Actualizar cola según resultado
        if resultado == 'EXITOSO':
            self.cola_functions['marcar_exitoso'](viaje_id)
            self.robot_state_manager.limpiar_viaje_actual()
            logger.info(f"{prefactura} COMPLETADO")

        elif resultado == 'LOGIN_LIMIT':
            self.cola_functions['registrar_error'](
                viaje_id,
                'LOGIN_LIMIT',
                f'Límite de usuarios en {modulo_error}'
            )
            logger.warning(f"LOGIN LÍMITE - {prefactura}")

        elif resultado == 'DRIVER_CORRUPTO':
            self.cola_functions['registrar_error'](
                viaje_id,
                'DRIVER_CORRUPTO',
                f'Driver corrupto en {modulo_error}'
            )
            self.robot_state_manager.limpiar_viaje_actual()
            logger.warning(f"DRIVER CORRUPTO - {prefactura}")

        else:
            motivo_detallado = f"PROCESO FALLÓ EN: {modulo_error}"
            self.cola_functions['marcar_fallido'](viaje_id, modulo_error, motivo_detallado)
            self.robot_state_manager.limpiar_viaje_actual()
            logger.error(f"{prefactura} FALLÓ: {modulo_error}")

        return resultado, modulo_error, prefactura
