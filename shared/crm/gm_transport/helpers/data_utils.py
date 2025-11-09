"""
Utilidades de datos para GM Transport
Lectura de CSVs, mapeo de determinantes, etc.
"""
import os
import csv
import logging

logger = logging.getLogger(__name__)


def obtener_ruta_y_base(determinante):
    """
    Obtiene la ruta GM y base origen desde el CSV de determinantes

    Args:
        determinante: Código de determinante a buscar

    Returns:
        tuple: (ruta_gm, base_origen, estado) donde estado puede ser:
               "ENCONTRADO", "DETERMINANTE_NO_ENCONTRADA", "ARCHIVO_CSV_NO_EXISTE",
               "ERROR_LECTURA_CSV"
    """
    csv_path = 'modules/clave_ruta_base.csv'

    logger.info(f"Buscando ruta para determinante: {determinante}")

    try:
        if not os.path.exists(csv_path):
            logger.error(f"No existe el archivo: {csv_path}")
            return None, None, "ARCHIVO_CSV_NO_EXISTE"

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            determinantes_disponibles = []

            for i, row in enumerate(reader):
                determinantes_disponibles.append(row['determinante'])

                if row['determinante'] == str(determinante):
                    logger.info(
                        f"Determinante {determinante} -> "
                        f"ruta {row['ruta_gm']}, base {row['base_origen']}"
                    )
                    return row['ruta_gm'], row['base_origen'], "ENCONTRADO"

            logger.error("DETERMINANTE NO ENCONTRADA")
            logger.error(f"Determinante buscada: {determinante}")
            logger.error("Esta determinante debe agregarse al archivo clave_ruta_base.csv")

            return None, None, "DETERMINANTE_NO_ENCONTRADA"

    except Exception as e:
        logger.error(f"Error al leer CSV: {e}")
        return None, None, "ERROR_LECTURA_CSV"


def validar_determinante_existe(determinante):
    """
    Verifica si una determinante existe en el CSV

    Args:
        determinante: Código de determinante a verificar

    Returns:
        bool: True si existe, False si no
    """
    _, _, estado = obtener_ruta_y_base(determinante)
    return estado == "ENCONTRADO"


def obtener_lista_determinantes():
    """
    Obtiene lista completa de determinantes disponibles

    Returns:
        list: Lista de códigos de determinantes
    """
    csv_path = 'modules/clave_ruta_base.csv'

    try:
        if not os.path.exists(csv_path):
            return []

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            return [row['determinante'] for row in reader]

    except Exception as e:
        logger.error(f"Error leyendo lista de determinantes: {e}")
        return []
