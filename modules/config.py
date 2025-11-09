"""
Configuración centralizada del sistema
Carga desde .env o usa valores por defecto
"""
import os
from pathlib import Path

def get_env(key, default=None, cast=str):
    """Obtiene variable de entorno con cast"""
    value = os.getenv(key, default)
    if value is None:
        return None
    if cast == bool:
        return value.lower() in ('true', '1', 'yes')
    return cast(value)

try:
    from dotenv import load_dotenv
    env_path = Path('.') / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

MYSQL_HOST = get_env('MYSQL_HOST', 'localhost')
MYSQL_USER = get_env('MYSQL_USER', 'root')
MYSQL_PASSWORD = get_env('MYSQL_PASSWORD', '')
MYSQL_DATABASE = get_env('MYSQL_DATABASE', 'alsua_transport')

CRM_URL = get_env('CRM_URL', 'https://softwareparatransporte.com')
CRM_USER = get_env('CRM_USER', '')
CRM_PASSWORD = get_env('CRM_PASSWORD', '')

LIMITE_VIAJES_POR_CICLO = get_env('LIMITE_VIAJES_POR_CICLO', 3, int)
TIEMPO_ESPERA_EXITOSO = get_env('TIEMPO_ESPERA_EXITOSO', 60, int)
TIEMPO_ESPERA_FALLIDO = get_env('TIEMPO_ESPERA_FALLIDO', 30, int)
TIEMPO_ESPERA_LOGIN_LIMIT = get_env('TIEMPO_ESPERA_LOGIN_LIMIT', 900, int)

CIRCUIT_BREAKER_ENABLED = get_env('CIRCUIT_BREAKER_ENABLED', True, bool)
CIRCUIT_BREAKER_MAX_SAME_ERROR = get_env('CIRCUIT_BREAKER_MAX_SAME_ERROR', 10, int)
CIRCUIT_BREAKER_MAX_ERROR_RATE = get_env('CIRCUIT_BREAKER_MAX_ERROR_RATE', 0.90, float)

FAILED_TRIPS_DIR = get_env('FAILED_TRIPS_DIR', 'data/failed_trips')
AUTO_SAVE_FAILED_TRIPS = get_env('AUTO_SAVE_FAILED_TRIPS', True, bool)

LOG_LEVEL = get_env('LOG_LEVEL', 'INFO')
LOG_JSON_ENABLED = get_env('LOG_JSON_ENABLED', False, bool)
LOG_DIR = get_env('LOG_DIR', 'data/logs')
