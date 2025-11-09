"""
Panel Web Alsua - Servidor Flask
Monitoreo en tiempo real del robot de automatización
"""

from flask import Flask, render_template, jsonify, redirect, url_for, request
import threading
import os
import csv
import logging
import sys
from modules import robot_state_manager
from modules.reprocessing_manager import reprocessing_manager
from modules.circuit_breaker import circuit_breaker
from modules.trip_validator import trip_validator
from modules import config
from alsua_mail_automation import AlsuaMailAutomation
from cola_viajes import agregar_viaje_a_cola

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Estado del sistema Flask
sistema_estado = {
    "ejecutando": False,
    "hilo": None,
    "instancia": None
}


def ejecutar_robot_bucle():
    """Función que ejecuta el bucle del robot en un hilo separado"""
    try:
        logger.info(">>> ejecutar_robot_bucle() INICIADO <<<")
        sys.stdout.flush()

        robot_state_manager.actualizar_estado_robot("ejecutando")
        logger.info(">>> Estado robot actualizado <<<")
        sys.stdout.flush()

        AlsuaMailAutomation.continuar_ejecutando = True
        logger.info(">>> Creando instancia AlsuaMailAutomation <<<")
        sys.stdout.flush()

        sistema = AlsuaMailAutomation()
        logger.info(">>> Instancia creada <<<")
        sys.stdout.flush()

        sistema_estado["instancia"] = sistema
        logger.info(">>> Robot iniciado desde panel web <<<")
        sys.stdout.flush()

        sistema.ejecutar_bucle_continuo()
    except Exception as e:
        logger.error(f">>> ERROR en ejecución del robot: {e} <<<")
        import traceback
        traceback.print_exc()
        robot_state_manager.actualizar_estado_robot("detenido")
    finally:
        logger.info(">>> ejecutar_robot_bucle() FINALIZANDO <<<")
        sys.stdout.flush()
        sistema_estado["ejecutando"] = False
        sistema_estado["instancia"] = None


@app.route("/")
def index():
    """Página principal del dashboard"""
    return render_template("dashboard.html")


@app.route("/api/estado")
def api_estado():
    """API que devuelve el estado completo del robot en JSON"""
    estado = robot_state_manager.obtener_estado_completo()
    robot = estado['robots']['robot_1']
    cola = estado['cola']

    # Verificar si está trabado
    trabado, mensaje_trabado = robot_state_manager.verificar_si_trabado()

    return jsonify({
        'robot': {
            'nombre': robot['nombre'],
            'estado': robot['estado'],
            'ultima_actividad': robot['ultima_actividad'],
            'viaje_actual': robot.get('viaje_actual'),
            'trabado': trabado,
            'mensaje_trabado': mensaje_trabado
        },
        'estadisticas': {
            'viajes_exitosos': robot['estadisticas']['viajes_exitosos'],
            'viajes_fallidos': robot['estadisticas']['viajes_fallidos'],
            'viajes_pendientes': len(cola.get('viajes', []))
        },
        'cola': cola,
        'viajes_exitosos': robot.get('viajes_exitosos_recientes', []),
        'viajes_fallidos': robot.get('viajes_fallidos_recientes', [])
    })


@app.route("/iniciar")
def iniciar_robot():
    """Inicia el robot de automatización en un hilo separado"""
    try:
        logger.info(">>> ENDPOINT /iniciar llamado <<<")
        sys.stdout.flush()

        if sistema_estado["ejecutando"]:
            logger.warning(">>> Robot ya está ejecutando - ignorando <<<")
            sys.stdout.flush()
            return redirect(url_for('index'))

        logger.info(">>> Creando thread del robot <<<")
        sys.stdout.flush()

        sistema_estado["ejecutando"] = True
        sistema_estado["hilo"] = threading.Thread(target=ejecutar_robot_bucle, daemon=True)

        logger.info(">>> Iniciando thread <<<")
        sys.stdout.flush()

        sistema_estado["hilo"].start()

        logger.info(">>> Thread iniciado exitosamente <<<")
        sys.stdout.flush()

        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f">>> ERROR en /iniciar: {e} <<<")
        sys.stdout.flush()
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))


@app.route("/detener")
def detener_robot():
    """Detiene el robot de automatización"""
    sistema_estado["ejecutando"] = False
    AlsuaMailAutomation.continuar_ejecutando = False  # Señal para detener
    robot_state_manager.actualizar_estado_robot("detenido")

    logger.info(" Señal de detención enviada al robot")

    return redirect(url_for('index'))


@app.route("/api/limpiar_zombies")
def api_limpiar_zombies():
    """Endpoint para limpiar viajes zombie manualmente"""
    try:
        from cola_viajes import limpiar_viajes_zombie
        eliminados = limpiar_viajes_zombie()
        return jsonify({
            'success': True,
            'eliminados': eliminados,
            'mensaje': f'{eliminados} viaje(s) zombie eliminado(s)' if eliminados > 0 else 'No hay zombies'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/screenshots")
def listar_screenshots():
    """Lista los screenshots disponibles"""
    carpeta = "screenshots_errores"
    if not os.path.exists(carpeta):
        return jsonify([])

    screenshots = []
    for archivo in os.listdir(carpeta):
        if archivo.endswith('.png'):
            screenshots.append({
                'nombre': archivo,
                'ruta': f'/screenshot/{archivo}'
            })

    return jsonify(screenshots)


@app.route("/screenshot/<nombre>")
def ver_screenshot(nombre):
    """Sirve un screenshot específico"""
    from flask import send_from_directory
    return send_from_directory('screenshots_errores', nombre)


@app.route("/determinantes")
def determinantes():
    """Página de gestión de determinantes"""
    return render_template("determinantes.html")

@app.route("/viajes_fallidos")
def viajes_fallidos_page():
    """Página de viajes fallidos"""
    return render_template("viajes_fallidos.html")

@app.route("/api/determinantes")
def api_determinantes():
    """Lista todas las determinantes"""
    try:
        determinantes = []
        with open('modules/clave_ruta_base.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            determinantes = list(reader)
        return jsonify({'success': True, 'determinantes': determinantes})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/determinantes/add", methods=['POST'])
def api_add_determinante():
    """Agrega nueva determinante"""
    try:
        data = request.json
        determinante = data.get('determinante')
        ruta_gm = data.get('ruta_gm')
        base_origen = data.get('base_origen')

        with open('modules/clave_ruta_base.csv', 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['determinante', 'ruta_gm', 'base_origen'])
            writer.writerow({
                'determinante': determinante,
                'ruta_gm': ruta_gm,
                'base_origen': base_origen
            })

        trip_validator.reload_determinantes()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/determinantes/delete", methods=['POST'])
def api_delete_determinante():
    """Elimina determinante"""
    try:
        data = request.json
        determinante_to_delete = data.get('determinante')

        determinantes = []
        with open('modules/clave_ruta_base.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            determinantes = [row for row in reader if row['determinante'] != determinante_to_delete]

        with open('modules/clave_ruta_base.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['determinante', 'ruta_gm', 'base_origen'])
            writer.writeheader()
            writer.writerows(determinantes)

        trip_validator.reload_determinantes()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/viajes_fallidos")
def api_viajes_fallidos():
    """Lista viajes fallidos"""
    estado = request.args.get('estado')
    trips = reprocessing_manager.get_failed_trips(estado)
    return jsonify({'success': True, 'viajes': trips})

@app.route("/api/viajes_fallidos/reprocess", methods=['POST'])
def api_reprocess_trip():
    """Reprocesa viaje fallido"""
    try:
        data = request.json
        filename = data.get('filename')

        trips = reprocessing_manager.get_failed_trips()
        trip = next((t for t in trips if t['filename'] == filename), None)

        if not trip:
            return jsonify({'success': False, 'error': 'Viaje no encontrado'})

        agregado = agregar_viaje_a_cola(trip['datos_viaje'])
        if agregado:
            reprocessing_manager.mark_as_reprocessed(filename, False)
            return jsonify({'success': True, 'message': 'Viaje agregado a cola'})
        else:
            return jsonify({'success': False, 'error': 'No se pudo agregar a cola'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/viajes_fallidos/delete", methods=['POST'])
def api_delete_failed_trip():
    """Elimina viaje fallido"""
    try:
        data = request.json
        filename = data.get('filename')
        reprocessing_manager.delete_failed_trip(filename)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/circuit_breaker")
def api_circuit_breaker_status():
    """Estado del circuit breaker"""
    return jsonify(circuit_breaker.get_status())

@app.route("/api/circuit_breaker/reset", methods=['POST'])
def api_circuit_breaker_reset():
    """Resetea circuit breaker"""
    try:
        circuit_breaker.reset()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/configuracion")
def configuracion():
    """Página de configuración"""
    return render_template("configuracion.html")

@app.route("/api/config")
def api_config():
    """Obtiene configuración actual"""
    try:
        config_data = {
            'LIMITE_VIAJES_POR_CICLO': config.LIMITE_VIAJES_POR_CICLO,
            'TIEMPO_ESPERA_EXITOSO': config.TIEMPO_ESPERA_EXITOSO,
            'TIEMPO_ESPERA_FALLIDO': config.TIEMPO_ESPERA_FALLIDO,
            'TIEMPO_ESPERA_LOGIN_LIMIT': config.TIEMPO_ESPERA_LOGIN_LIMIT,
            'CIRCUIT_BREAKER_ENABLED': config.CIRCUIT_BREAKER_ENABLED,
            'CIRCUIT_BREAKER_MAX_SAME_ERROR': config.CIRCUIT_BREAKER_MAX_SAME_ERROR,
            'CIRCUIT_BREAKER_MAX_ERROR_RATE': config.CIRCUIT_BREAKER_MAX_ERROR_RATE,
            'AUTO_SAVE_FAILED_TRIPS': config.AUTO_SAVE_FAILED_TRIPS,
            'FAILED_TRIPS_DIR': config.FAILED_TRIPS_DIR,
            'LOG_LEVEL': config.LOG_LEVEL,
            'LOG_JSON_ENABLED': config.LOG_JSON_ENABLED,
            'LOG_DIR': config.LOG_DIR,
            'MYSQL_HOST': config.MYSQL_HOST,
            'MYSQL_USER': config.MYSQL_USER,
            'MYSQL_PASSWORD': '***' if config.MYSQL_PASSWORD else '',
            'MYSQL_DATABASE': config.MYSQL_DATABASE,
            'CRM_URL': config.CRM_URL,
            'CRM_USER': config.CRM_USER,
            'CRM_PASSWORD': '***' if config.CRM_PASSWORD else ''
        }
        return jsonify({'success': True, 'config': config_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/config/save", methods=['POST'])
def api_config_save():
    """Guarda configuración en archivo .env"""
    try:
        data = request.json
        config_data = data.get('config', {})

        env_lines = []
        for key, value in config_data.items():
            if key.endswith('_PASSWORD') and value == '***':
                continue

            if isinstance(value, bool):
                value = 'true' if value else 'false'
            elif isinstance(value, (int, float)):
                value = str(value)

            env_lines.append(f"{key}={value}")

        with open('.env', 'w', encoding='utf-8') as f:
            f.write('\n'.join(env_lines))

        return jsonify({'success': True, 'message': 'Configuración guardada. Reinicia el sistema.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PANEL WEB ALSUA - INICIANDO")
    print("="*60)
    print("Servidor: http://localhost:5051")
    print("Acceso local: http://127.0.0.1:5051")
    print("Acceso red: http://<IP_COMPUTADORA>:5051")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5051, debug=True, use_reloader=False)
