"""
Robot State Manager - Gestión Automática del Estado de Robots

Funcionalidades:
- Gestiona estado_robots.json automáticamente
- Actualiza estado del robot (ejecutando/detenido/procesando)
- Marca viaje actual en proceso con toda su información
- Incrementa contadores de viajes exitosos/fallidos
- Detecta si el robot está trabado (>15 min sin actividad)
- Actualiza cola de viajes pendientes
- Mantiene listas de viajes recientes (últimos 10 exitosos/fallidos)
"""

import json
import os
from datetime import datetime
from pathlib import Path


ARCHIVO_ESTADO = "estado_robots.json"


def _leer_estado():
    """
    Lee el archivo de estado. Si no existe, crea uno con estructura inicial.

    Returns:
        dict: Estado completo del sistema
    """
    if not os.path.exists(ARCHIVO_ESTADO):
        # Estructura inicial si el archivo no existe
        return {
            "robots": {
                "robot_1": {
                    "nombre": "Robot Alsua VACIO",
                    "estado": "detenido",
                    "ultima_actividad": datetime.now().isoformat(),
                    "viaje_actual": None,
                    "estadisticas": {
                        "viajes_exitosos": 0,
                        "viajes_fallidos": 0,
                        "ultimo_viaje_exitoso": None,
                        "ultimo_viaje_fallido": None
                    },
                    "viajes_exitosos_recientes": [],
                    "viajes_fallidos_recientes": []
                }
            },
            "cola": {
                "viajes": [],
                "ultima_actualizacion": datetime.now().isoformat()
            }
        }

    try:
        with open(ARCHIVO_ESTADO, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error al leer estado: {e}")
        # Retornar estructura vacía en caso de error
        return _leer_estado()  # Recursión para crear nuevo archivo


def _guardar_estado(estado):
    """
    Guarda el estado en el archivo JSON

    Args:
        estado: Dict con el estado completo del sistema
    """
    try:
        with open(ARCHIVO_ESTADO, 'w', encoding='utf-8') as f:
            json.dump(estado, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error al guardar estado: {e}")


def actualizar_estado_robot(nuevo_estado):
    """
    Actualiza el estado general del robot

    Args:
        nuevo_estado: 'ejecutando', 'detenido' o 'procesando'
    """
    estado = _leer_estado()
    estado['robots']['robot_1']['estado'] = nuevo_estado
    estado['robots']['robot_1']['ultima_actividad'] = datetime.now().isoformat()
    _guardar_estado(estado)


def marcar_viaje_actual(prefactura, fase, placa_tractor="", placa_remolque="", determinante=""):
    """
    Marca un viaje como actualmente en proceso

    Args:
        prefactura: Número de prefactura
        fase: Fase actual ('Inicializando', 'Facturación', 'Salida', 'Llegada')
        placa_tractor: Placa del tractor (opcional)
        placa_remolque: Placa del remolque (opcional)
        determinante: Clave determinante (opcional)
    """
    estado = _leer_estado()
    estado['robots']['robot_1']['viaje_actual'] = {
        "prefactura": prefactura,
        "fase": fase,
        "placa_tractor": placa_tractor,
        "placa_remolque": placa_remolque,
        "determinante": determinante,
        "inicio": datetime.now().isoformat()
    }
    estado['robots']['robot_1']['ultima_actividad'] = datetime.now().isoformat()
    estado['robots']['robot_1']['estado'] = 'procesando'
    _guardar_estado(estado)


def actualizar_fase_viaje(nueva_fase):
    """
    Actualiza solo la fase del viaje actual (más eficiente)

    Args:
        nueva_fase: Nueva fase ('Facturación', 'Salida', 'Llegada')
    """
    estado = _leer_estado()
    if estado['robots']['robot_1']['viaje_actual']:
        estado['robots']['robot_1']['viaje_actual']['fase'] = nueva_fase
        estado['robots']['robot_1']['ultima_actividad'] = datetime.now().isoformat()
        _guardar_estado(estado)


def limpiar_viaje_actual():
    """Limpia el viaje actual (cuando termina exitoso o fallido)"""
    estado = _leer_estado()
    estado['robots']['robot_1']['viaje_actual'] = None
    _guardar_estado(estado)


def incrementar_exitosos(prefactura):
    """
    Incrementa contador de viajes exitosos y registra en lista reciente

    Args:
        prefactura: Número de prefactura que fue exitosa
    """
    estado = _leer_estado()
    robot = estado['robots']['robot_1']

    # Incrementar contador
    robot['estadisticas']['viajes_exitosos'] += 1
    robot['estadisticas']['ultimo_viaje_exitoso'] = {
        "prefactura": prefactura,
        "timestamp": datetime.now().isoformat()
    }

    # Agregar a lista reciente (mantener últimos 10)
    robot['viajes_exitosos_recientes'].insert(0, {
        "prefactura": prefactura,
        "timestamp": datetime.now().isoformat()
    })
    robot['viajes_exitosos_recientes'] = robot['viajes_exitosos_recientes'][:10]

    # Limpiar viaje actual
    robot['viaje_actual'] = None

    _guardar_estado(estado)


def incrementar_fallidos(prefactura, motivo_error):
    """
    Incrementa contador de viajes fallidos y registra en lista reciente

    Args:
        prefactura: Número de prefactura que falló
        motivo_error: Descripción del error que causó el fallo
    """
    estado = _leer_estado()
    robot = estado['robots']['robot_1']

    # Incrementar contador
    robot['estadisticas']['viajes_fallidos'] += 1
    robot['estadisticas']['ultimo_viaje_fallido'] = {
        "prefactura": prefactura,
        "motivo": motivo_error,
        "timestamp": datetime.now().isoformat()
    }

    # Agregar a lista reciente (mantener últimos 10)
    robot['viajes_fallidos_recientes'].insert(0, {
        "prefactura": prefactura,
        "motivo": motivo_error,
        "timestamp": datetime.now().isoformat()
    })
    robot['viajes_fallidos_recientes'] = robot['viajes_fallidos_recientes'][:10]

    # Limpiar viaje actual
    robot['viaje_actual'] = None

    _guardar_estado(estado)


def actualizar_cola(lista_viajes):
    """
    Actualiza la cola de viajes pendientes

    Args:
        lista_viajes: Lista de dicts con información de viajes pendientes
                      Cada dict debe tener: prefactura, fecha, placa_tractor, placa_remolque
    """
    estado = _leer_estado()
    estado['cola']['viajes'] = lista_viajes
    estado['cola']['ultima_actualizacion'] = datetime.now().isoformat()
    _guardar_estado(estado)


def verificar_si_trabado():
    """
    Verifica si el robot está trabado (más de 15 minutos sin actividad mientras procesa)

    Returns:
        tuple: (trabado: bool, mensaje: str o None)
               - (True, "mensaje") si está trabado
               - (False, None) si está OK
    """
    estado = _leer_estado()
    robot = estado['robots']['robot_1']

    # Solo verificar si está en estado "procesando"
    if robot['estado'] != 'procesando':
        return False, None

    try:
        # Calcular tiempo sin actividad
        ultima_act = datetime.fromisoformat(robot['ultima_actividad'])
        ahora = datetime.now()
        minutos_sin_actividad = (ahora - ultima_act).total_seconds() / 60

        # Si han pasado más de 15 minutos sin actividad
        if minutos_sin_actividad > 15:
            viaje = robot.get('viaje_actual', {})
            prefactura = viaje.get('prefactura', 'DESCONOCIDO')
            fase = viaje.get('fase', 'DESCONOCIDA')

            mensaje = (
                f"Robot trabado procesando {prefactura} - "
                f"Fase: {fase} - "
                f"{int(minutos_sin_actividad)} minutos sin actividad"
            )
            return True, mensaje

    except Exception as e:
        print(f"⚠️ Error al verificar si trabado: {e}")

    return False, None


def obtener_estado_completo():
    """
    Obtiene el estado completo del sistema para el API

    Returns:
        dict: Estado completo con información de robots, cola y estadísticas
    """
    return _leer_estado()


def obtener_estadisticas():
    """
    Obtiene solo las estadísticas del robot

    Returns:
        dict: Estadísticas de viajes exitosos y fallidos
    """
    estado = _leer_estado()
    return estado['robots']['robot_1']['estadisticas']


def obtener_cola():
    """
    Obtiene solo la información de la cola

    Returns:
        dict: Información de la cola de viajes pendientes
    """
    estado = _leer_estado()
    return estado['cola']


if __name__ == "__main__":
    print("Robot State Manager - Gestión Automática de Estado")
    print("=" * 60)
    print(f"Archivo de estado: {ARCHIVO_ESTADO}")
    print("Funciones disponibles:")
    print("  - actualizar_estado_robot(estado)")
    print("  - marcar_viaje_actual(prefactura, fase, ...)")
    print("  - incrementar_exitosos(prefactura)")
    print("  - incrementar_fallidos(prefactura, motivo)")
    print("  - verificar_si_trabado()")
    print("  - actualizar_cola(lista_viajes)")
    print("=" * 60)

    # Test básico
    estado = obtener_estado_completo()
    print(f"\n✓ Estado actual: {estado['robots']['robot_1']['estado']}")
    print(f"✓ Viajes exitosos: {estado['robots']['robot_1']['estadisticas']['viajes_exitosos']}")
    print(f"✓ Viajes fallidos: {estado['robots']['robot_1']['estadisticas']['viajes_fallidos']}")
