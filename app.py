"""
Panel Web Alsua - Servidor Flask
Monitoreo en tiempo real del robot de automatización
"""

from flask import Flask, render_template, jsonify, redirect, url_for, request
import threading
import os
import logging
import sys
import csv
from modules import robot_state_manager
from alsua_mail_automation import AlsuaMailAutomation

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


# ========== ENDPOINTS PARA ADMINISTRACIÓN DE DETERMINANTES ==========

CSV_DETERMINANTES = 'modules/clave_ruta_base.csv'

@app.route("/admin/determinantes")
def admin_determinantes():
    """Página de administración de determinantes"""
    return render_template("admin_determinantes.html")


@app.route("/api/determinantes")
def api_listar_determinantes():
    """Lista todas las claves determinantes del CSV"""
    try:
        if not os.path.exists(CSV_DETERMINANTES):
            return jsonify({'success': False, 'error': 'Archivo CSV no encontrado'}), 404

        determinantes = []
        with open(CSV_DETERMINANTES, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('determinante'):  # Ignorar líneas vacías
                    determinantes.append({
                        'determinante': row['determinante'],
                        'ruta_gm': row['ruta_gm'],
                        'base_origen': row['base_origen']
                    })

        return jsonify({'success': True, 'determinantes': determinantes})
    except Exception as e:
        logger.error(f"Error listando determinantes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/determinantes", methods=['POST'])
def api_agregar_determinante():
    """Agrega una nueva clave determinante"""
    try:
        data = request.get_json()
        determinante = data.get('determinante', '').strip()
        ruta_gm = data.get('ruta_gm', '').strip()
        base_origen = data.get('base_origen', '').strip()

        # Validaciones
        if not determinante or not ruta_gm or not base_origen:
            return jsonify({'success': False, 'error': 'Todos los campos son requeridos'}), 400

        if len(determinante) != 4 or not determinante.isdigit():
            return jsonify({'success': False, 'error': 'Determinante debe ser 4 dígitos'}), 400

        # Verificar si ya existe
        determinantes_existentes = []
        if os.path.exists(CSV_DETERMINANTES):
            with open(CSV_DETERMINANTES, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    determinantes_existentes.append(row)
                    if row.get('determinante') == determinante:
                        return jsonify({'success': False, 'error': f'Determinante {determinante} ya existe'}), 400

        # Agregar nueva determinante
        with open(CSV_DETERMINANTES, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['determinante', 'ruta_gm', 'base_origen'])
            writer.writerow({
                'determinante': determinante,
                'ruta_gm': ruta_gm,
                'base_origen': base_origen
            })

        logger.info(f"Determinante agregada: {determinante} -> Ruta: {ruta_gm}, Base: {base_origen}")
        return jsonify({'success': True, 'message': 'Determinante agregada correctamente'})

    except Exception as e:
        logger.error(f"Error agregando determinante: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/determinantes/<determinante>", methods=['PUT'])
def api_editar_determinante(determinante):
    """Edita una clave determinante existente"""
    try:
        data = request.get_json()
        nueva_ruta = data.get('ruta_gm', '').strip()
        nueva_base = data.get('base_origen', '').strip()

        if not nueva_ruta or not nueva_base:
            return jsonify({'success': False, 'error': 'Ruta y base son requeridos'}), 400

        # Leer todas las determinantes
        if not os.path.exists(CSV_DETERMINANTES):
            return jsonify({'success': False, 'error': 'Archivo CSV no encontrado'}), 404

        determinantes = []
        encontrado = False

        with open(CSV_DETERMINANTES, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('determinante') == determinante:
                    row['ruta_gm'] = nueva_ruta
                    row['base_origen'] = nueva_base
                    encontrado = True
                determinantes.append(row)

        if not encontrado:
            return jsonify({'success': False, 'error': f'Determinante {determinante} no encontrada'}), 404

        # Reescribir el archivo
        with open(CSV_DETERMINANTES, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['determinante', 'ruta_gm', 'base_origen'])
            writer.writeheader()
            for det in determinantes:
                if det.get('determinante'):  # No escribir líneas vacías
                    writer.writerow(det)

        logger.info(f"Determinante editada: {determinante} -> Ruta: {nueva_ruta}, Base: {nueva_base}")
        return jsonify({'success': True, 'message': 'Determinante actualizada correctamente'})

    except Exception as e:
        logger.error(f"Error editando determinante: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/determinantes/<determinante>", methods=['DELETE'])
def api_eliminar_determinante(determinante):
    """Elimina una clave determinante"""
    try:
        if not os.path.exists(CSV_DETERMINANTES):
            return jsonify({'success': False, 'error': 'Archivo CSV no encontrado'}), 404

        # Leer todas las determinantes excepto la que se va a eliminar
        determinantes = []
        encontrado = False

        with open(CSV_DETERMINANTES, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('determinante') == determinante:
                    encontrado = True
                    continue  # Saltar esta fila (eliminarla)
                if row.get('determinante'):  # No agregar líneas vacías
                    determinantes.append(row)

        if not encontrado:
            return jsonify({'success': False, 'error': f'Determinante {determinante} no encontrada'}), 404

        # Reescribir el archivo sin la determinante eliminada
        with open(CSV_DETERMINANTES, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['determinante', 'ruta_gm', 'base_origen'])
            writer.writeheader()
            for det in determinantes:
                writer.writerow(det)

        logger.info(f"Determinante eliminada: {determinante}")
        return jsonify({'success': True, 'message': 'Determinante eliminada correctamente'})

    except Exception as e:
        logger.error(f"Error eliminando determinante: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PANEL WEB ALSUA - INICIANDO")
    print("="*60)
    print("Servidor: http://localhost:5051")
    print("Acceso local: http://127.0.0.1:5051")
    print("Acceso red: http://<IP_COMPUTADORA>:5051")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5051, debug=True, use_reloader=False)
