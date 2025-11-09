"""
Manejo centralizado de errores para GM Transport
Registro de errores en CSV y logs
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Maneja el registro de errores de viajes"""

    def __init__(self, viajes_log_function):
        """
        Args:
            viajes_log_function: Función para registrar viajes fallidos en CSV
        """
        self.log_viaje_fallido = viajes_log_function

    def registrar_error_viaje(self, datos_viaje, tipo_error, detalle=""):
        """
        Registra un error de viaje en el log CSV

        Args:
            datos_viaje: Dict con datos del viaje
            tipo_error: Tipo de error ocurrido
            detalle: Detalle adicional del error

        Returns:
            dict: Información del error registrado
        """
        prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
        placa_tractor = datos_viaje.get('placa_tractor', 'DESCONOCIDA')
        placa_remolque = datos_viaje.get('placa_remolque', 'DESCONOCIDA')
        determinante = datos_viaje.get('clave_determinante', 'DESCONOCIDO')
        fecha_viaje = datos_viaje.get('fecha', '')
        importe = datos_viaje.get('importe', '')
        cliente_codigo = datos_viaje.get('cliente_codigo', '')

        try:
            motivo_completo = f"{tipo_error}"
            if detalle:
                motivo_completo += f" - {detalle}"

            exito_log = self.log_viaje_fallido(
                prefactura=prefactura,
                motivo_fallo=motivo_completo,
                determinante=determinante,
                fecha_viaje=fecha_viaje,
                placa_tractor=placa_tractor,
                placa_remolque=placa_remolque,
                importe=importe,
                cliente_codigo=cliente_codigo
            )

            if exito_log:
                logger.info("Error registrado en log CSV")
            else:
                logger.warning("Error registrando en log CSV")

        except Exception as e:
            logger.warning(f"Error registrando en log CSV: {e}")

        # Log detallado del error
        logger.error("VIAJE REQUIERE ATENCIÓN MANUAL")
        logger.error(f"PREFACTURA: {prefactura}")
        logger.error(f"PLACA TRACTOR: {placa_tractor}")
        logger.error(f"PLACA REMOLQUE: {placa_remolque}")
        logger.error(f"DETERMINANTE: {determinante}")
        logger.error(f"ERROR: {tipo_error}")
        if detalle:
            logger.error(f"DETALLE: {detalle}")
        logger.error("ACCIÓN REQUERIDA: Revisar y completar manualmente en GM Transport")

        return {
            'timestamp': datetime.now().isoformat(),
            'prefactura': prefactura,
            'placa_tractor': placa_tractor,
            'placa_remolque': placa_remolque,
            'determinante': determinante,
            'tipo_error': tipo_error,
            'detalle': detalle
        }

    def registrar_determinante_faltante(self, datos_viaje, determinante_faltante):
        """
        Registra una determinante faltante en el CSV

        Args:
            datos_viaje: Dict con datos del viaje
            determinante_faltante: Código de determinante no encontrada

        Returns:
            bool: True si se registró exitosamente
        """
        try:
            prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
            fecha_viaje = datos_viaje.get('fecha', '')
            placa_tractor = datos_viaje.get('placa_tractor', '')
            placa_remolque = datos_viaje.get('placa_remolque', '')
            importe = datos_viaje.get('importe', '')
            cliente_codigo = datos_viaje.get('cliente_codigo', '')

            motivo_fallo = f"Determinante {determinante_faltante} no encontrada"

            exito_log = self.log_viaje_fallido(
                prefactura=prefactura,
                motivo_fallo=motivo_fallo,
                determinante=determinante_faltante,
                fecha_viaje=fecha_viaje,
                placa_tractor=placa_tractor,
                placa_remolque=placa_remolque,
                importe=importe,
                cliente_codigo=cliente_codigo
            )

            if exito_log:
                logger.error("DETERMINANTE FALTANTE REGISTRADA:")
                logger.error(f"Prefactura: {prefactura}")
                logger.error(f"Determinante faltante: {determinante_faltante}")
                logger.error(f"Placas: {placa_tractor} / {placa_remolque}")
                logger.error("ACCIÓN: Agregar determinante a clave_ruta_base.csv")
                return True
            else:
                logger.warning("Error registrando en log CSV")
                return False

        except Exception as e:
            logger.error(f"Error registrando determinante faltante: {e}")
            return False
