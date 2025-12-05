"""
Panel Web Alsua - Servidor Flask
Monitoreo en tiempo real del robot de automatización
"""

from flask import Flask, render_template, jsonify, redirect, url_for
import threading
import os
import logging
import sys
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


@app.route("/admin/claves")
def admin_claves():
    """Panel de administración de claves determinantes"""
    return render_template("admin_claves.html")


@app.route("/api/claves", methods=["GET"])
def api_obtener_claves():
    """API que devuelve todas las claves determinantes del CSV"""
    import csv
    csv_path = os.path.join('modules', 'clave_ruta_base.csv')

    try:
        claves = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                claves.append({
                    'determinante': row.get('determinante', ''),
                    'ruta_gm': row.get('ruta_gm', ''),
                    'base_origen': row.get('base_origen', ''),
                    'tipo_documento': row.get('tipo_documento', '')
                })

        return jsonify({
            'success': True,
            'claves': claves
        })
    except Exception as e:
        logger.error(f"Error al leer claves: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error al leer archivo: {str(e)}'
        }), 500


@app.route("/api/claves", methods=["POST"])
def api_agregar_clave():
    """API para agregar una nueva clave determinante"""
    import csv
    from flask import request

    csv_path = os.path.join('modules', 'clave_ruta_base.csv')

    try:
        data = request.get_json()
        nueva_determinante = data.get('determinante', '').strip()
        ruta_gm = data.get('ruta_gm', '').strip()
        base_origen = data.get('base_origen', '').strip()
        tipo_documento = data.get('tipo_documento', '').strip()

        # Validar campos
        if not all([nueva_determinante, ruta_gm, base_origen, tipo_documento]):
            return jsonify({
                'success': False,
                'mensaje': 'Todos los campos son obligatorios'
            }), 400

        # Validar que determinante sea solo números
        if not nueva_determinante.isdigit():
            return jsonify({
                'success': False,
                'mensaje': 'La determinante debe contener solo números'
            }), 400

        # Verificar si ya existe
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('determinante') == nueva_determinante:
                    return jsonify({
                        'success': False,
                        'mensaje': f'La determinante {nueva_determinante} ya existe'
                    }), 400

        # Agregar al CSV
        with open(csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([nueva_determinante, ruta_gm, base_origen, tipo_documento])

        logger.info(f"Nueva clave agregada: {nueva_determinante}")

        return jsonify({
            'success': True,
            'mensaje': f'Determinante {nueva_determinante} agregada exitosamente'
        })

    except Exception as e:
        logger.error(f"Error al agregar clave: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error al guardar: {str(e)}'
        }), 500


@app.route("/api/claves/<determinante>", methods=["PUT"])
def api_editar_clave(determinante):
    """API para editar una clave determinante existente"""
    import csv
    from flask import request

    csv_path = os.path.join('modules', 'clave_ruta_base.csv')

    try:
        data = request.get_json()
        nueva_determinante = data.get('determinante', '').strip()
        ruta_gm = data.get('ruta_gm', '').strip()
        base_origen = data.get('base_origen', '').strip()
        tipo_documento = data.get('tipo_documento', '').strip()

        # Validar campos
        if not all([nueva_determinante, ruta_gm, base_origen, tipo_documento]):
            return jsonify({
                'success': False,
                'mensaje': 'Todos los campos son obligatorios'
            }), 400

        # Validar que determinante sea solo números
        if not nueva_determinante.isdigit():
            return jsonify({
                'success': False,
                'mensaje': 'La determinante debe contener solo números'
            }), 400

        # Leer todas las filas
        filas = []
        encontrado = False
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            for row in reader:
                if row.get('determinante') == determinante:
                    # Si cambió el número de determinante, verificar que no exista el nuevo
                    if nueva_determinante != determinante:
                        # Verificar si el nuevo número ya existe
                        with open(csv_path, 'r', encoding='utf-8') as f2:
                            reader2 = csv.DictReader(f2)
                            for row2 in reader2:
                                if row2.get('determinante') == nueva_determinante:
                                    return jsonify({
                                        'success': False,
                                        'mensaje': f'La determinante {nueva_determinante} ya existe'
                                    }), 400

                    # Actualizar la fila
                    row['determinante'] = nueva_determinante
                    row['ruta_gm'] = ruta_gm
                    row['base_origen'] = base_origen
                    row['tipo_documento'] = tipo_documento
                    encontrado = True

                filas.append(row)

        if not encontrado:
            return jsonify({
                'success': False,
                'mensaje': f'Determinante {determinante} no encontrada'
            }), 404

        # Escribir de vuelta al CSV
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filas)

        logger.info(f"Clave actualizada: {determinante} -> {nueva_determinante}")

        return jsonify({
            'success': True,
            'mensaje': f'Determinante actualizada exitosamente'
        })

    except Exception as e:
        logger.error(f"Error al editar clave: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error al actualizar: {str(e)}'
        }), 500


@app.route("/api/claves/<determinante>", methods=["DELETE"])
def api_eliminar_clave(determinante):
    """API para eliminar una clave determinante"""
    import csv

    csv_path = os.path.join('modules', 'clave_ruta_base.csv')

    try:
        # Leer todas las filas excepto la que se va a eliminar
        filas = []
        encontrado = False
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            for row in reader:
                if row.get('determinante') == determinante:
                    encontrado = True
                    continue  # Saltar esta fila
                filas.append(row)

        if not encontrado:
            return jsonify({
                'success': False,
                'mensaje': f'Determinante {determinante} no encontrada'
            }), 404

        # Escribir de vuelta al CSV sin la fila eliminada
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filas)

        logger.info(f"Clave eliminada: {determinante}")

        return jsonify({
            'success': True,
            'mensaje': f'Determinante {determinante} eliminada exitosamente'
        })

    except Exception as e:
        logger.error(f"Error al eliminar clave: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error al eliminar: {str(e)}'
        }), 500


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PANEL WEB ALSUA - INICIANDO")
    print("="*60)
    print("Servidor: http://localhost:5051")
    print("Acceso local: http://127.0.0.1:5051")
    print("Acceso red: http://<IP_COMPUTADORA>:5051")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5051, debug=True, use_reloader=False)
