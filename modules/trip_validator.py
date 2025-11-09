"""
Validación de viajes ANTES de enviar al CRM
Reduce fallos detectando problemas temprano
"""
import re
import os
import csv
import logging

logger = logging.getLogger(__name__)

class TripValidator:
    def __init__(self, determinantes_csv="modules/clave_ruta_base.csv"):
        self.determinantes_csv = determinantes_csv
        self._determinantes_validas = self._load_determinantes()

    def _load_determinantes(self):
        """Carga determinantes válidas del CSV"""
        try:
            if not os.path.exists(self.determinantes_csv):
                logger.warning(f"CSV de determinantes no existe: {self.determinantes_csv}")
                return set()

            determinantes = set()
            with open(self.determinantes_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    determinantes.add(row['determinante'])

            logger.info(f"Cargadas {len(determinantes)} determinantes válidas")
            return determinantes
        except Exception as e:
            logger.error(f"Error cargando determinantes: {e}")
            return set()

    def validate_trip(self, datos_viaje):
        """
        Valida viaje completo antes de CRM
        Returns: (is_valid, errors_list)
        """
        errors = []

        errors.extend(self._validate_format(datos_viaje))
        errors.extend(self._validate_determinante(datos_viaje))
        errors.extend(self._validate_business_logic(datos_viaje))

        return (len(errors) == 0, errors)

    def _validate_format(self, datos_viaje):
        """Validación de formato de campos"""
        errors = []

        prefactura = datos_viaje.get('prefactura', '')
        if not prefactura or not re.match(r'^\d{7}$', str(prefactura)):
            errors.append(f"Prefactura inválida: '{prefactura}' (debe ser 7 dígitos)")

        placa_tractor = datos_viaje.get('placa_tractor', '')
        if not placa_tractor or len(placa_tractor) < 3:
            errors.append(f"Placa tractor inválida: '{placa_tractor}'")

        placa_remolque = datos_viaje.get('placa_remolque', '')
        if not placa_remolque or len(placa_remolque) < 3:
            errors.append(f"Placa remolque inválida: '{placa_remolque}'")

        importe = datos_viaje.get('importe', '')
        try:
            importe_float = float(str(importe).replace(',', ''))
            if importe_float <= 0:
                errors.append(f"Importe inválido: {importe} (debe ser > 0)")
        except:
            errors.append(f"Importe no numérico: '{importe}'")

        return errors

    def _validate_determinante(self, datos_viaje):
        """Validación de determinante"""
        errors = []

        determinante = str(datos_viaje.get('clave_determinante', ''))
        if not determinante:
            errors.append("Determinante vacía")
        elif determinante not in self._determinantes_validas:
            errors.append(f"Determinante {determinante} NO existe en CSV")

        return errors

    def _validate_business_logic(self, datos_viaje):
        """Validación de lógica de negocio"""
        errors = []

        fecha = datos_viaje.get('fecha', '')
        if not fecha:
            errors.append("Fecha vacía")

        cliente_codigo = datos_viaje.get('cliente_codigo', '')
        if not cliente_codigo:
            errors.append("Código de cliente vacío")

        return errors

    def reload_determinantes(self):
        """Recarga determinantes del CSV"""
        self._determinantes_validas = self._load_determinantes()

trip_validator = TripValidator()
