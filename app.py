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
from datetime import datetime, timedelta
from modules import robot_state_manager
from alsua_mail_automation import AlsuaMailAutomation
from cola_reprocesamiento import cola_reprocesamiento
from viajes_log import viajes_log

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
                        'base_origen': row['base_origen'],
                        'tipo_documento': row.get('tipo_documento', 'FACTURA CFDI - W')
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
        tipo_documento = data.get('tipo_documento', 'FACTURA CFDI - W').strip()

        # Validaciones
        if not determinante or not ruta_gm or not base_origen or not tipo_documento:
            return jsonify({'success': False, 'error': 'Todos los campos son requeridos'}), 400

        if not determinante.isdigit():
            return jsonify({'success': False, 'error': 'Determinante debe contener solo números'}), 400

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
            writer = csv.DictWriter(f, fieldnames=['determinante', 'ruta_gm', 'base_origen', 'tipo_documento'])
            writer.writerow({
                'determinante': determinante,
                'ruta_gm': ruta_gm,
                'base_origen': base_origen,
                'tipo_documento': tipo_documento
            })

        logger.info(f"Determinante agregada: {determinante} -> Ruta: {ruta_gm}, Base: {base_origen}, Tipo Doc: {tipo_documento}")
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
        nuevo_tipo_doc = data.get('tipo_documento', '').strip()

        if not nueva_ruta or not nueva_base or not nuevo_tipo_doc:
            return jsonify({'success': False, 'error': 'Ruta, base y tipo de documento son requeridos'}), 400

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
                    row['tipo_documento'] = nuevo_tipo_doc
                    encontrado = True
                determinantes.append(row)

        if not encontrado:
            return jsonify({'success': False, 'error': f'Determinante {determinante} no encontrada'}), 404

        # Reescribir el archivo
        with open(CSV_DETERMINANTES, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['determinante', 'ruta_gm', 'base_origen', 'tipo_documento'])
            writer.writeheader()
            for det in determinantes:
                if det.get('determinante'):  # No escribir líneas vacías
                    writer.writerow(det)

        logger.info(f"Determinante editada: {determinante} -> Ruta: {nueva_ruta}, Base: {nueva_base}, Tipo Doc: {nuevo_tipo_doc}")
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
            writer = csv.DictWriter(f, fieldnames=['determinante', 'ruta_gm', 'base_origen', 'tipo_documento'])
            writer.writeheader()
            for det in determinantes:
                writer.writerow(det)

        logger.info(f"Determinante eliminada: {determinante}")
        return jsonify({'success': True, 'message': 'Determinante eliminada correctamente'})

    except Exception as e:
        logger.error(f"Error eliminando determinante: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== ENDPOINTS PARA VIAJES FALLIDOS Y REPROCESAMIENTO ==========

@app.route("/admin/viajes-fallidos")
def admin_viajes_fallidos():
    """Página de administración de viajes fallidos"""
    return render_template("admin_viajes_fallidos.html")


@app.route("/api/viajes-fallidos")
def api_listar_viajes_fallidos():
    """Lista todos los viajes fallidos con filtros opcionales"""
    try:
        # Obtener parámetros de filtro
        filtro_etapa = request.args.get('etapa', '')
        filtro_fecha = request.args.get('fecha', '')  # 'hoy', 'semana', 'mes'
        buscar = request.args.get('buscar', '').lower()

        # Leer viajes fallidos del CSV
        viajes_fallidos = []
        if os.path.exists('viajes_log.csv'):
            with open('viajes_log.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('estatus') == 'FALLIDO':
                        viajes_fallidos.append(row)

        # Aplicar filtros
        if filtro_fecha:
            ahora = datetime.now()
            if filtro_fecha == 'hoy':
                fecha_limite = ahora.date()
                viajes_fallidos = [v for v in viajes_fallidos
                                  if datetime.strptime(v['timestamp'].split()[0], '%Y-%m-%d').date() >= fecha_limite]
            elif filtro_fecha == 'semana':
                fecha_limite = ahora - timedelta(days=7)
                viajes_fallidos = [v for v in viajes_fallidos
                                  if datetime.strptime(v['timestamp'].split()[0], '%Y-%m-%d') >= fecha_limite]
            elif filtro_fecha == 'mes':
                fecha_limite = ahora - timedelta(days=30)
                viajes_fallidos = [v for v in viajes_fallidos
                                  if datetime.strptime(v['timestamp'].split()[0], '%Y-%m-%d') >= fecha_limite]

        if filtro_etapa:
            viajes_fallidos = [v for v in viajes_fallidos if filtro_etapa.upper() in v.get('motivo_fallo', '').upper()]

        if buscar:
            viajes_fallidos = [v for v in viajes_fallidos
                              if buscar in v.get('prefactura', '').lower()
                              or buscar in v.get('motivo_fallo', '').lower()]

        return jsonify({'success': True, 'viajes': viajes_fallidos})

    except Exception as e:
        logger.error(f"Error listando viajes fallidos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/cola-reprocesamiento")
def api_listar_cola():
    """Lista todos los viajes en cola de reprocesamiento"""
    try:
        pendientes = cola_reprocesamiento.obtener_pendientes()
        return jsonify({'success': True, 'cola': pendientes})
    except Exception as e:
        logger.error(f"Error listando cola: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/cola-reprocesamiento", methods=['POST'])
def api_agregar_a_cola():
    """Agrega un viaje a la cola de reprocesamiento"""
    try:
        data = request.get_json()

        # Validar datos requeridos
        campos_requeridos = ['prefactura', 'determinante', 'fecha_viaje',
                           'placa_tractor', 'placa_remolque', 'importe']
        for campo in campos_requeridos:
            if not data.get(campo):
                return jsonify({'success': False, 'error': f'Campo {campo} es requerido'}), 400

        # Agregar a cola
        exito = cola_reprocesamiento.agregar_a_cola(
            datos_viaje=data,
            modo_reproceso=data.get('modo_reproceso', 'completo'),
            viaje_gm=data.get('viaje_gm', ''),
            etapa_inicial=data.get('etapa_inicial', 'SALIDA')
        )

        if exito:
            return jsonify({'success': True, 'message': 'Viaje agregado a cola de reprocesamiento'})
        else:
            return jsonify({'success': False, 'error': 'No se pudo agregar a cola'}), 500

    except Exception as e:
        logger.error(f"Error agregando a cola: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/cola-reprocesamiento/<prefactura>", methods=['DELETE'])
def api_eliminar_de_cola(prefactura):
    """Elimina un viaje de la cola de reprocesamiento"""
    try:
        exito = cola_reprocesamiento.eliminar_de_cola(prefactura)
        if exito:
            return jsonify({'success': True, 'message': 'Viaje eliminado de cola'})
        else:
            return jsonify({'success': False, 'error': 'No se encontró el viaje'}), 404
    except Exception as e:
        logger.error(f"Error eliminando de cola: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/procesar-viaje/<prefactura>", methods=['POST'])
def api_procesar_viaje(prefactura):
    """Procesa un viaje específico de la cola AHORA"""
    try:
        # Obtener datos del viaje de la cola
        viaje = cola_reprocesamiento.obtener_viaje(prefactura)
        if not viaje:
            return jsonify({'success': False, 'error': 'Viaje no encontrado en cola'}), 404

        # Marcar como procesando
        cola_reprocesamiento.marcar_procesando(prefactura)

        # Aquí se procesará el viaje (lo integraremos con el robot después)
        # Por ahora solo retornamos éxito
        return jsonify({
            'success': True,
            'message': f'Viaje {prefactura} en proceso',
            'viaje': viaje
        })

    except Exception as e:
        logger.error(f"Error procesando viaje: {e}")
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
