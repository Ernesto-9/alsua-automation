"""
Gestor de Cola de Reprocesamiento de Viajes Fallidos
Maneja viajes que necesitan ser reprocesados manualmente
"""

import csv
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ColaReprocesamiento:
    """Maneja la cola de viajes para reprocesar"""

    def __init__(self, archivo_csv="cola_reprocesamiento.csv"):
        self.archivo_csv = os.path.abspath(archivo_csv)
        self.campos = [
            'timestamp',
            'prefactura',
            'determinante',
            'fecha_viaje',
            'placa_tractor',
            'placa_remolque',
            'importe',
            'cliente_codigo',
            'modo_reproceso',  # 'completo' o 'continuar'
            'viaje_gm',        # Número de viaje en GM (si modo=continuar)
            'etapa_inicial',   # De dónde continuar (si modo=continuar)
            'estado',          # 'pendiente' o 'procesando'
            'motivo_original'  # Por qué falló originalmente
        ]
        self._verificar_archivo()

    def _verificar_archivo(self):
        """Crea el archivo CSV con headers si no existe"""
        try:
            if not os.path.exists(self.archivo_csv):
                with open(self.archivo_csv, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=self.campos)
                    writer.writeheader()
        except Exception as e:
            logger.error(f"Error verificando archivo cola reprocesamiento: {e}")

    def agregar_a_cola(self, datos_viaje, modo_reproceso='completo', viaje_gm='', etapa_inicial='SALIDA'):
        """
        Agrega un viaje a la cola de reprocesamiento

        Args:
            datos_viaje: Dict con datos del viaje
            modo_reproceso: 'completo' o 'continuar'
            viaje_gm: Número de viaje en GM (si modo=continuar)
            etapa_inicial: Etapa desde donde continuar
        """
        try:
            registro = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'prefactura': datos_viaje.get('prefactura', ''),
                'determinante': datos_viaje.get('determinante', ''),
                'fecha_viaje': datos_viaje.get('fecha_viaje', ''),
                'placa_tractor': datos_viaje.get('placa_tractor', ''),
                'placa_remolque': datos_viaje.get('placa_remolque', ''),
                'importe': datos_viaje.get('importe', ''),
                'cliente_codigo': datos_viaje.get('cliente_codigo', '040512'),
                'modo_reproceso': modo_reproceso,
                'viaje_gm': viaje_gm,
                'etapa_inicial': etapa_inicial,
                'estado': 'pendiente',
                'motivo_original': datos_viaje.get('motivo_fallo', '')
            }

            with open(self.archivo_csv, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos)
                writer.writerow(registro)

            logger.info(f"Viaje {registro['prefactura']} agregado a cola de reprocesamiento")
            return True

        except Exception as e:
            logger.error(f"Error agregando a cola: {e}")
            return False

    def obtener_pendientes(self):
        """Obtiene todos los viajes pendientes de reprocesar"""
        try:
            if not os.path.exists(self.archivo_csv):
                return []

            pendientes = []
            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('estado') == 'pendiente':
                        pendientes.append(row)

            return pendientes

        except Exception as e:
            logger.error(f"Error obteniendo pendientes: {e}")
            return []

    def marcar_procesando(self, prefactura):
        """Marca un viaje como procesando"""
        return self._cambiar_estado(prefactura, 'procesando')

    def eliminar_de_cola(self, prefactura):
        """Elimina un viaje de la cola (después de procesarlo exitosamente)"""
        try:
            if not os.path.exists(self.archivo_csv):
                return False

            # Leer todos los registros excepto el que se va a eliminar
            registros = []
            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('prefactura') != prefactura:
                        registros.append(row)

            # Reescribir el archivo
            with open(self.archivo_csv, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos)
                writer.writeheader()
                for reg in registros:
                    writer.writerow(reg)

            return True

        except Exception as e:
            logger.error(f"Error eliminando de cola: {e}")
            return False

    def _cambiar_estado(self, prefactura, nuevo_estado):
        """Cambia el estado de un viaje en la cola"""
        try:
            if not os.path.exists(self.archivo_csv):
                return False

            registros = []
            encontrado = False

            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('prefactura') == prefactura:
                        row['estado'] = nuevo_estado
                        encontrado = True
                    registros.append(row)

            if not encontrado:
                return False

            # Reescribir el archivo
            with open(self.archivo_csv, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos)
                writer.writeheader()
                for reg in registros:
                    writer.writerow(reg)

            return True

        except Exception as e:
            logger.error(f"Error cambiando estado: {e}")
            return False

    def obtener_viaje(self, prefactura):
        """Obtiene los datos de un viaje específico de la cola"""
        try:
            if not os.path.exists(self.archivo_csv):
                return None

            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('prefactura') == prefactura:
                        return row

            return None

        except Exception as e:
            logger.error(f"Error obteniendo viaje: {e}")
            return None


# Instancia global
cola_reprocesamiento = ColaReprocesamiento()
