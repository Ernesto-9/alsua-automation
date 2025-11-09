"""
Sistema de Logging Detallado para Alsua Automation

Funcionalidades:
- Log completo y detallado en archivo debug.log
- Formato mejorado con timestamp, archivo y número de línea
- Rotación automática: cuando llega a 10MB, crea backup
- Mantiene 5 backups históricos
- Funciones especiales para logging de viajes
"""

import logging
from logging.handlers import RotatingFileHandler
import os


class DebugLogger:
    """Sistema de logging detallado con rotación automática"""

    def __init__(self, log_file="debug.log"):
        """
        Inicializa el sistema de logging

        Args:
            log_file: Nombre del archivo de log (default: debug.log)
        """
        self.logger = logging.getLogger("AlsuaDebug")
        self.logger.setLevel(logging.DEBUG)

        # Evitar duplicación de handlers si ya existe
        if self.logger.handlers:
            return

        # Handler con rotación automática
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )

        # Formato detallado con timestamp, archivo y línea
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_viaje_inicio(self, prefactura, datos_viaje):
        """
        Registra el inicio de procesamiento de un viaje

        Args:
            prefactura: Número de prefactura
            datos_viaje: Dict con información del viaje
        """
        self.logger.info("=" * 80)
        self.logger.info(f"INICIO PROCESAMIENTO VIAJE: {prefactura}")
        self.logger.info(f"  Fecha: {datos_viaje.get('fecha', 'N/A')}")
        self.logger.info(f"  Placa tractor: {datos_viaje.get('placa_tractor', 'N/A')}")
        self.logger.info(f"  Placa remolque: {datos_viaje.get('placa_remolque', 'N/A')}")
        self.logger.info(f"  Determinante: {datos_viaje.get('clave_determinante', 'N/A')}")
        self.logger.info(f"  Operador: {datos_viaje.get('operador', 'N/A')}")
        self.logger.info("=" * 80)

    def log_viaje_exito(self, prefactura, uuid=None, viajegm=None):
        """
        Registra un viaje exitoso

        Args:
            prefactura: Número de prefactura
            uuid: UUID generado (opcional)
            viajegm: Número de viaje GM (opcional)
        """
        mensaje = f" VIAJE EXITOSO: {prefactura}"
        if uuid:
            mensaje += f" | UUID: {uuid}"
        if viajegm:
            mensaje += f" | ViajeGM: {viajegm}"
        self.logger.info(mensaje)

    def log_viaje_fallo(self, prefactura, modulo, detalle_error):
        """
        Registra un viaje fallido

        Args:
            prefactura: Número de prefactura
            modulo: Módulo donde falló (ej: gm_salida, gm_llegada)
            detalle_error: Descripción del error
        """
        self.logger.error("-" * 80)
        self.logger.error(f" VIAJE FALLIDO: {prefactura}")
        self.logger.error(f"  Módulo: {modulo}")
        self.logger.error(f"  Error: {detalle_error}")
        self.logger.error("-" * 80)

    def debug(self, mensaje):
        """Log nivel DEBUG"""
        self.logger.debug(mensaje)

    def info(self, mensaje):
        """Log nivel INFO"""
        self.logger.info(mensaje)

    def warning(self, mensaje):
        """Log nivel WARNING"""
        self.logger.warning(mensaje)

    def error(self, mensaje):
        """Log nivel ERROR"""
        self.logger.error(mensaje)

    def critical(self, mensaje):
        """Log nivel CRITICAL"""
        self.logger.critical(mensaje)

    def log_paso(self, prefactura, paso, detalle=""):
        """
        Registra un paso específico del proceso

        Args:
            prefactura: Número de prefactura
            paso: Nombre del paso (ej: "Clic en Salida")
            detalle: Información adicional (opcional)
        """
        mensaje = f"[{prefactura}] PASO: {paso}"
        if detalle:
            mensaje += f" - {detalle}"
        self.logger.debug(mensaje)

    def log_excepcion(self, prefactura, paso, excepcion):
        """
        Registra una excepción con traceback completo

        Args:
            prefactura: Número de prefactura
            paso: Paso donde ocurrió la excepción
            excepcion: Objeto Exception
        """
        self.logger.error(f"[{prefactura}] EXCEPCIÓN en paso '{paso}': {str(excepcion)}")
        self.logger.exception("Traceback completo:")


# Instancia global para uso en todo el proyecto
debug_logger = DebugLogger()


# Funciones de conveniencia para importación directa
def log_viaje_inicio(prefactura, datos_viaje):
    """Registra inicio de viaje (wrapper)"""
    debug_logger.log_viaje_inicio(prefactura, datos_viaje)


def log_viaje_exito(prefactura, uuid=None, viajegm=None):
    """Registra viaje exitoso (wrapper)"""
    debug_logger.log_viaje_exito(prefactura, uuid, viajegm)


def log_viaje_fallo(prefactura, modulo, detalle_error):
    """Registra viaje fallido (wrapper)"""
    debug_logger.log_viaje_fallo(prefactura, modulo, detalle_error)


def log_paso(prefactura, paso, detalle=""):
    """Registra un paso del proceso (wrapper)"""
    debug_logger.log_paso(prefactura, paso, detalle)


def log_excepcion(prefactura, paso, excepcion):
    """Registra excepción con traceback (wrapper)"""
    debug_logger.log_excepcion(prefactura, paso, excepcion)


if __name__ == "__main__":
    print("Debug Logger - Sistema de Logging Detallado")
    print("=" * 60)
    print(f"Archivo de log: debug.log")
    print(f"Tamaño máximo: 10MB")
    print(f"Backups: 5 archivos históricos")
    print(f"Formato: timestamp - [archivo:línea] - nivel - mensaje")
    print("=" * 60)

    # Test básico
    debug_logger.info("Sistema de logging inicializado correctamente")
    debug_logger.debug("Modo debug activado")
    print("\n Sistema de logging listo para usar")
