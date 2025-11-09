"""
Sistema de reprocesamiento de viajes fallidos
Guarda viajes fallidos en JSON para reprocesar sin email original
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ReprocessingManager:
    def __init__(self, failed_trips_dir="data/failed_trips"):
        self.failed_trips_dir = failed_trips_dir
        self._ensure_directory()

    def _ensure_directory(self):
        os.makedirs(self.failed_trips_dir, exist_ok=True)

    def save_failed_trip(self, datos_viaje, motivo_fallo, modulo_error=""):
        """Guarda viaje fallido en JSON"""
        try:
            prefactura = datos_viaje.get('prefactura', 'DESCONOCIDA')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefactura}_{timestamp}.json"
            filepath = os.path.join(self.failed_trips_dir, filename)

            failed_trip = {
                'timestamp': datetime.now().isoformat(),
                'prefactura': prefactura,
                'motivo_fallo': motivo_fallo,
                'modulo_error': modulo_error,
                'datos_viaje': datos_viaje,
                'estado': 'pendiente_reproceso'
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(failed_trip, f, indent=2, ensure_ascii=False)

            logger.info(f"Viaje fallido guardado: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error guardando viaje fallido: {e}")
            return False

    def get_failed_trips(self, estado=None):
        """Obtiene lista de viajes fallidos"""
        try:
            trips = []
            for filename in os.listdir(self.failed_trips_dir):
                if not filename.endswith('.json'):
                    continue

                filepath = os.path.join(self.failed_trips_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    trip = json.load(f)
                    if estado is None or trip.get('estado') == estado:
                        trip['filename'] = filename
                        trips.append(trip)

            return sorted(trips, key=lambda x: x['timestamp'], reverse=True)
        except Exception as e:
            logger.error(f"Error leyendo viajes fallidos: {e}")
            return []

    def mark_as_reprocessed(self, filename, exitoso=True):
        """Marca viaje como reprocesado"""
        try:
            filepath = os.path.join(self.failed_trips_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                trip = json.load(f)

            trip['estado'] = 'reprocesado_exitoso' if exitoso else 'reprocesado_fallido'
            trip['fecha_reproceso'] = datetime.now().isoformat()

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(trip, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            logger.error(f"Error marcando reproceso: {e}")
            return False

    def delete_failed_trip(self, filename):
        """Elimina viaje fallido"""
        try:
            filepath = os.path.join(self.failed_trips_dir, filename)
            os.remove(filepath)
            logger.info(f"Viaje fallido eliminado: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error eliminando viaje: {e}")
            return False

reprocessing_manager = ReprocessingManager()
