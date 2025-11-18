"""
Sistema de seguimiento de errores detallados
Genera mensajes descriptivos sin spam en terminal
"""

class ErrorTracker:
    """Rastrea el progreso de un viaje y genera mensajes de error detallados"""

    def __init__(self):
        self.ultimo_paso_exitoso = None
        self.ultimo_campo_exitoso = None
        self.ultimo_valor_exitoso = None
        self.paso_actual = None
        self.accion_actual = None
        self.valor_intentado = None

    def registrar_exito(self, paso, campo, valor):
        """Registra un paso exitoso"""
        self.ultimo_paso_exitoso = paso
        self.ultimo_campo_exitoso = campo
        self.ultimo_valor_exitoso = valor

    def registrar_intento(self, paso, accion, valor):
        """Registra qué se está intentando hacer"""
        self.paso_actual = paso
        self.accion_actual = accion
        self.valor_intentado = valor

    def generar_mensaje_error(self, error_original=""):
        """Genera un mensaje de error descriptivo"""
        partes = []

        # Paso donde falló
        if self.paso_actual:
            partes.append(f"Falló en {self.paso_actual}")

        # Qué estaba intentando hacer
        if self.accion_actual and self.valor_intentado:
            partes.append(f"al intentar {self.accion_actual} con valor '{self.valor_intentado}'")

        # Último campo exitoso
        if self.ultimo_campo_exitoso and self.ultimo_valor_exitoso:
            partes.append(f"Último éxito: {self.ultimo_campo_exitoso}='{self.ultimo_valor_exitoso}'")

        mensaje = ". ".join(partes)

        # Agregar error original si existe y es útil
        if error_original and len(error_original) < 100:
            mensaje += f". Error: {error_original}"

        return mensaje

    def reset(self):
        """Reinicia el tracker para un nuevo viaje"""
        self.__init__()


# Mapeo de etapas para mensajes consistentes
ETAPAS = {
    'PARSER': 'VALIDACIÓN-DATOS',
    'DETERMINANTE': 'VALIDACIÓN-DETERMINANTE',
    'SALIDA_FECHA': 'SALIDA-FECHA',
    'SALIDA_SUCURSAL': 'SALIDA-SUCURSAL',
    'SALIDA_RUTA': 'SALIDA-RUTA',
    'SALIDA_PLACA_TRACTOR': 'SALIDA-PLACA-TRACTOR',
    'SALIDA_PLACA_REMOLQUE': 'SALIDA-PLACA-REMOLQUE',
    'SALIDA_OPERADOR': 'SALIDA-OPERADOR',
    'SALIDA_GUARDAR': 'SALIDA-GUARDAR',
    'LLEGADA_ESTADO': 'LLEGADA-CAMBIO-ESTADO',
    'LLEGADA_FACTURAR': 'LLEGADA-BOTON-FACTURAR',
    'FACTURA_TIPO_DOC': 'FACTURA-TIPO-DOCUMENTO',
    'FACTURA_TOTAL': 'FACTURA-TOTAL',
    'FACTURA_GUARDAR': 'FACTURA-GUARDAR',
    'FACTURA_PDF': 'FACTURA-DESCARGA-PDF',
    'FACTURA_UUID': 'FACTURA-EXTRACCION-UUID'
}
