"""
Panel Web Alsua - Servidor Flask
Monitoreo en tiempo real del robot de automatización
"""

from flask import Flask, render_template, jsonify, redirect, url_for, request, send_from_directory
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
app.static_folder = 'static'

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


# ==============================
# PANEL DE REPROCESAMIENTO
# ==============================

@app.route("/admin/reprocesar")
def admin_reprocesar():
    """Panel de reprocesamiento de viajes fallidos"""
    return render_template("admin_reprocesar.html")


@app.route("/static/<path:filename>")
def serve_static(filename):
    """Sirve archivos estáticos"""
    return send_from_directory('static', filename)


@app.route("/api/viajes-fallidos", methods=["GET"])
def api_obtener_viajes_fallidos():
    """API que devuelve todos los viajes fallidos con historial de intentos"""
    from viajes_log import viajes_log, obtener_historial_viaje
    from cola_viajes import leer_cola

    try:
        # Leer viajes fallidos del CSV
        viajes_fallidos = viajes_log.leer_viajes_por_estatus("FALLIDO")

        # Leer cola para marcar viajes que ya están en cola
        cola = leer_cola()
        prefacturas_en_cola = set()
        for viaje_cola in cola.get("viajes", []):
            prefactura = viaje_cola.get("datos_viaje", {}).get("prefactura")
            if prefactura:
                prefacturas_en_cola.add(prefactura)

        # Enriquecer cada viaje con historial de intentos
        for viaje in viajes_fallidos:
            prefactura = viaje.get('prefactura')
            historial = obtener_historial_viaje(prefactura)
            viaje['num_intentos'] = len(historial.get('intentos', []))
            viaje['en_cola'] = prefactura in prefacturas_en_cola

        return jsonify({
            'success': True,
            'viajes': viajes_fallidos
        })

    except Exception as e:
        logger.error(f"Error obteniendo viajes fallidos: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@app.route("/api/viaje-historial/<prefactura>", methods=["GET"])
def api_obtener_historial_viaje(prefactura):
    """API que devuelve el historial de intentos de un viaje"""
    from viajes_log import obtener_historial_viaje

    try:
        historial = obtener_historial_viaje(prefactura)

        return jsonify({
            'success': True,
            'historial': historial
        })

    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@app.route("/api/viajes-fallidos/<prefactura>", methods=["PUT"])
def api_editar_viaje_fallido(prefactura):
    """API para editar un viaje fallido"""
    try:
        data = request.get_json()
        nueva_prefactura = data.get('prefactura', '').strip()
        determinante = data.get('determinante', '').strip()
        fecha_viaje = data.get('fecha_viaje', '').strip()
        placa_tractor = data.get('placa_tractor', '').strip()
        placa_remolque = data.get('placa_remolque', '').strip()

        if not all([nueva_prefactura, determinante, fecha_viaje, placa_tractor, placa_remolque]):
            return jsonify({
                'success': False,
                'mensaje': 'Todos los campos son obligatorios'
            }), 400

        # Leer CSV completo
        csv_path = 'viajes_log.csv'
        filas = []
        encontrado = False

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            for row in reader:
                if row.get('prefactura') == prefactura and row.get('estatus') == 'FALLIDO':
                    # Actualizar la fila
                    row['prefactura'] = nueva_prefactura
                    row['determinante'] = determinante
                    row['fecha_viaje'] = fecha_viaje
                    row['placa_tractor'] = placa_tractor
                    row['placa_remolque'] = placa_remolque
                    encontrado = True

                filas.append(row)

        if not encontrado:
            return jsonify({
                'success': False,
                'mensaje': f'Viaje {prefactura} no encontrado'
            }), 404

        # Escribir de vuelta al CSV
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filas)

        logger.info(f"Viaje fallido actualizado: {prefactura} -> {nueva_prefactura}")

        return jsonify({
            'success': True,
            'mensaje': 'Viaje actualizado exitosamente'
        })

    except Exception as e:
        logger.error(f"Error editando viaje: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@app.route("/api/viajes-fallidos/<prefactura>", methods=["DELETE"])
def api_eliminar_viaje_fallido(prefactura):
    """API para eliminar un viaje fallido del log"""
    from viajes_log import limpiar_historial_viaje

    try:
        csv_path = 'viajes_log.csv'
        filas = []
        encontrado = False

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            for row in reader:
                if row.get('prefactura') == prefactura and row.get('estatus') == 'FALLIDO':
                    encontrado = True
                    continue  # Saltar esta fila
                filas.append(row)

        if not encontrado:
            return jsonify({
                'success': False,
                'mensaje': f'Viaje {prefactura} no encontrado'
            }), 404

        # Escribir de vuelta al CSV
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filas)

        # Limpiar historial
        limpiar_historial_viaje(prefactura)

        logger.info(f"Viaje fallido eliminado: {prefactura}")

        return jsonify({
            'success': True,
            'mensaje': 'Viaje eliminado exitosamente'
        })

    except Exception as e:
        logger.error(f"Error eliminando viaje: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@app.route("/api/viajes-fallidos/edicion-masiva", methods=["POST"])
def api_edicion_masiva():
    """API para editar varios viajes fallidos a la vez"""
    try:
        data = request.get_json()
        prefacturas = data.get('prefacturas', [])
        cambios = data.get('cambios', {})

        if not prefacturas or not cambios:
            return jsonify({
                'success': False,
                'mensaje': 'Datos inválidos'
            }), 400

        csv_path = 'viajes_log.csv'
        filas = []
        actualizados = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            for row in reader:
                if row.get('prefactura') in prefacturas and row.get('estatus') == 'FALLIDO':
                    # Aplicar cambios
                    if 'determinante' in cambios:
                        row['determinante'] = cambios['determinante']
                    if 'placa_tractor' in cambios:
                        row['placa_tractor'] = cambios['placa_tractor']
                    if 'placa_remolque' in cambios:
                        row['placa_remolque'] = cambios['placa_remolque']
                    actualizados += 1

                filas.append(row)

        # Escribir de vuelta al CSV
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filas)

        logger.info(f"Edición masiva: {actualizados} viajes actualizados")

        return jsonify({
            'success': True,
            'actualizados': actualizados,
            'mensaje': f'{actualizados} viaje(s) actualizados exitosamente'
        })

    except Exception as e:
        logger.error(f"Error en edición masiva: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@app.route("/api/viajes-fallidos/eliminar-masivo", methods=["POST"])
def api_eliminar_masivo():
    """API para eliminar varios viajes fallidos a la vez"""
    from viajes_log import limpiar_historial_viaje

    try:
        data = request.get_json()
        prefacturas = data.get('prefacturas', [])

        if not prefacturas:
            return jsonify({
                'success': False,
                'mensaje': 'No se proporcionaron prefacturas'
            }), 400

        csv_path = 'viajes_log.csv'
        filas = []
        eliminados = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            for row in reader:
                if row.get('prefactura') in prefacturas and row.get('estatus') == 'FALLIDO':
                    eliminados += 1
                    continue  # Saltar esta fila
                filas.append(row)

        # Escribir de vuelta al CSV
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filas)

        # Limpiar historial de cada viaje eliminado
        for prefactura in prefacturas:
            limpiar_historial_viaje(prefactura)

        logger.info(f"Eliminación masiva: {eliminados} viajes eliminados")

        return jsonify({
            'success': True,
            'eliminados': eliminados,
            'mensaje': f'{eliminados} viaje(s) eliminados exitosamente'
        })

    except Exception as e:
        logger.error(f"Error en eliminación masiva: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@app.route("/api/reprocesar-viajes", methods=["POST"])
def api_reprocesar_viajes():
    """API para agregar viajes fallidos a la cola para reprocesarlos"""
    from viajes_log import viajes_log
    from cola_viajes import agregar_viaje_a_cola

    try:
        data = request.get_json()
        prefacturas = data.get('prefacturas', [])
        modo = data.get('modo', 'desde_cero')  # 'desde_cero' o 'desde_busqueda'

        if not prefacturas:
            return jsonify({
                'success': False,
                'mensaje': 'No se proporcionaron prefacturas'
            }), 400

        # Leer CSV de viajes para obtener datos completos
        csv_path = 'viajes_log.csv'
        viajes_a_reprocesar = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                if row.get('prefactura') in prefacturas and row.get('estatus') == 'FALLIDO':
                    viajes_a_reprocesar.append(row)

        if len(viajes_a_reprocesar) == 0:
            return jsonify({
                'success': False,
                'mensaje': 'No se encontraron viajes fallidos con esas prefacturas'
            }), 404

        # Agregar cada viaje a la cola con el modo de reprocesamiento
        agregados = 0
        duplicados = 0

        for viaje in viajes_a_reprocesar:
            datos_viaje = {
                'prefactura': viaje.get('prefactura'),
                'determinante': viaje.get('determinante'),
                'clave_determinante': viaje.get('determinante'),  # Alias
                'fecha_viaje': viaje.get('fecha_viaje'),
                'placa_tractor': viaje.get('placa_tractor'),
                'placa_remolque': viaje.get('placa_remolque'),
                'importe': viaje.get('importe'),
                'cliente_codigo': viaje.get('cliente_codigo'),
                'modo_reprocesar': modo  # Nuevo campo para indicar el modo
            }

            if agregar_viaje_a_cola(datos_viaje):
                agregados += 1
            else:
                duplicados += 1
                logger.warning(f"Viaje {datos_viaje['prefactura']} ya está en cola (duplicado)")

        mensaje = f'{agregados} viaje(s) agregados a la cola para reprocesamiento'
        if duplicados > 0:
            mensaje += f' ({duplicados} ya estaban en cola)'

        logger.info(mensaje)

        return jsonify({
            'success': True,
            'agregados': agregados,
            'duplicados': duplicados,
            'mensaje': mensaje
        })

    except Exception as e:
        logger.error(f"Error reprocesando viajes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@app.route("/api/agregar-viajes-excel", methods=["POST"])
def agregar_viajes_excel():
    """API para agregar viajes desde archivo Excel"""
    from cola_viajes import agregar_viaje_a_cola
    from viajes_log import verificar_viaje_existe
    import pandas as pd
    from datetime import datetime
    import re

    try:
        if 'excel_file' not in request.files:
            return jsonify({
                'success': False,
                'mensaje': 'No se proporcionó archivo Excel'
            }), 400

        file = request.files['excel_file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'mensaje': 'Archivo vacío'
            }), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'mensaje': 'Formato no válido. Solo .xlsx o .xls'
            }), 400

        df = pd.read_excel(file)

        columnas_requeridas = ['Numero Prefactura', 'Fecha Embarque', 'Determinante',
                              'Placa Tracto', 'Placa Remolque', 'Total Facturar']

        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if columnas_faltantes:
            return jsonify({
                'success': False,
                'mensaje': f'Columnas faltantes: {", ".join(columnas_faltantes)}'
            }), 400

        nuevos = 0
        a_reprocesar = 0
        exitosos_rechazados = 0
        duplicados_cola = 0
        rechazados = 0
        errores = []

        for idx, row in df.iterrows():
            try:
                es_reproceso = False
                prefactura = str(row['Numero Prefactura']).strip()

                if not prefactura or prefactura == 'nan':
                    rechazados += 1
                    errores.append({
                        'fila': idx + 2,
                        'prefactura': prefactura,
                        'razon': 'Prefactura vacía'
                    })
                    continue

                viaje_existente = verificar_viaje_existe(prefactura)
                if viaje_existente and viaje_existente.get('estatus') == 'EXITOSO':
                    exitosos_rechazados += 1
                    continue

                es_reproceso = viaje_existente and viaje_existente.get('estatus') == 'FALLIDO'

                determinante = str(row['Determinante']).strip()
                if not re.match(r'^\d{4}$', determinante):
                    rechazados += 1
                    errores.append({
                        'fila': idx + 2,
                        'prefactura': prefactura,
                        'razon': f'Determinante inválido: {determinante}'
                    })
                    continue

                fecha_embarque = row['Fecha Embarque']
                if pd.isna(fecha_embarque):
                    rechazados += 1
                    errores.append({
                        'fila': idx + 2,
                        'prefactura': prefactura,
                        'razon': 'Fecha vacía'
                    })
                    continue

                if isinstance(fecha_embarque, str):
                    fecha = fecha_embarque.split(' ')[0]
                else:
                    fecha = fecha_embarque.strftime('%d/%m/%Y')

                placa_tractor = str(row['Placa Tracto']).strip()
                placa_remolque = str(row['Placa Remolque']).strip()

                if not placa_tractor or placa_tractor == 'nan' or not placa_remolque or placa_remolque == 'nan':
                    rechazados += 1
                    errores.append({
                        'fila': idx + 2,
                        'prefactura': prefactura,
                        'razon': 'Placas vacías'
                    })
                    continue

                importe_str = str(row['Total Facturar']).replace('$', '').replace(',', '').strip()
                try:
                    importe = float(importe_str)
                    if importe <= 0:
                        raise ValueError("Importe debe ser mayor a 0")
                except:
                    rechazados += 1
                    errores.append({
                        'fila': idx + 2,
                        'prefactura': prefactura,
                        'razon': f'Importe inválido: {importe_str}'
                    })
                    continue

                datos_viaje = {
                    'prefactura': prefactura,
                    'fecha': fecha,
                    'clave_determinante': determinante,
                    'placa_tractor': placa_tractor,
                    'placa_remolque': placa_remolque,
                    'importe': importe,
                    'cliente_codigo': '040512',
                    'tipo_viaje': 'VACIO',
                    'determinante_fuente': 'EXCEL_MANUAL'
                }

                if agregar_viaje_a_cola(datos_viaje):
                    if es_reproceso:
                        a_reprocesar += 1
                    else:
                        nuevos += 1
                else:
                    duplicados_cola += 1

            except Exception as e:
                rechazados += 1
                errores.append({
                    'fila': idx + 2,
                    'prefactura': str(row.get('Numero Prefactura', 'DESCONOCIDA')),
                    'razon': str(e)
                })

        total_excel = len(df)
        agregados_cola = nuevos + a_reprocesar

        mensaje = (
            f"Viajes en excel: {total_excel}\n"
            f"Viajes nuevos: {nuevos}\n"
            f"Viajes a reintentar: {a_reprocesar}\n"
            f"Viajes agregados a la cola: {agregados_cola}\n"
            f"Viajes ignorados: {exitosos_rechazados}"
        )

        if rechazados > 0:
            mensaje += f"\nViajes con errores de validación: {rechazados}"

        logger.info(f"Excel procesado:\n{mensaje}")

        return jsonify({
            'success': True,
            'total_excel': total_excel,
            'nuevos': nuevos,
            'a_reprocesar': a_reprocesar,
            'agregados_cola': agregados_cola,
            'exitosos_rechazados': exitosos_rechazados,
            'rechazados': rechazados,
            'mensaje': mensaje,
            'errores': errores[:10]
        })

    except Exception as e:
        logger.error(f"Error procesando Excel: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


@app.route("/api/cola-reprocesamiento", methods=["GET"])
def api_obtener_cola():
    """Obtiene viajes en cola de reprocesamiento"""
    try:
        from cola_viajes import leer_cola
        cola_data = leer_cola()
        viajes_en_cola = cola_data.get('viajes', [])

        # Filtrar solo viajes pendientes o en proceso
        viajes_pendientes = [v for v in viajes_en_cola if v.get('estado') in ['PENDIENTE', 'EN_PROCESO']]

        return jsonify({
            'success': True,
            'cola': viajes_pendientes,
            'total': len(viajes_pendientes)
        })
    except Exception as e:
        logger.error(f"Error obteniendo cola: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/cola-reprocesamiento/<prefactura>", methods=["DELETE"])
def api_eliminar_de_cola(prefactura):
    """Elimina un viaje de la cola"""
    try:
        from cola_viajes import leer_cola
        import json

        cola_data = leer_cola()
        viajes = cola_data.get('viajes', [])

        # Filtrar viaje a eliminar
        viajes_filtrados = [v for v in viajes if v.get('prefactura') != prefactura]

        if len(viajes_filtrados) == len(viajes):
            return jsonify({'success': False, 'error': 'Viaje no encontrado en cola'}), 404

        # Guardar cola actualizada
        cola_data['viajes'] = viajes_filtrados
        with open('cola_viajes.json', 'w', encoding='utf-8') as f:
            json.dump(cola_data, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True, 'mensaje': 'Viaje eliminado de cola'})
    except Exception as e:
        logger.error(f"Error eliminando de cola: {e}")
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
