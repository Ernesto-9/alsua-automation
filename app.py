"""
Panel Web Alsua - Servidor Flask
Monitoreo en tiempo real del robot de automatización
"""

from flask import Flask, render_template, jsonify, redirect, url_for
import threading
import os
import logging
from modules import robot_state_manager
from alsua_mail_automation import AlsuaMailAutomation

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
        print(">>> ejecutar_robot_bucle() INICIADO <<<")
        robot_state_manager.actualizar_estado_robot("ejecutando")
        print(">>> Estado robot actualizado <<<")

        AlsuaMailAutomation.continuar_ejecutando = True
        print(">>> Creando instancia AlsuaMailAutomation <<<")
        sistema = AlsuaMailAutomation()
        print(">>> Instancia creada <<<")

        sistema_estado["instancia"] = sistema
        print(">>> Robot iniciado desde panel web <<<")

        sistema.ejecutar_bucle_continuo()
    except Exception as e:
        print(f">>> ERROR en ejecución del robot: {e} <<<")
        import traceback
        traceback.print_exc()
        robot_state_manager.actualizar_estado_robot("detenido")
    finally:
        print(">>> ejecutar_robot_bucle() FINALIZANDO <<<")
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
        print(">>> ENDPOINT /iniciar llamado <<<")

        if sistema_estado["ejecutando"]:
            print(">>> Robot ya está ejecutando <<<")
            return redirect(url_for('index'))

        print(">>> Creando thread del robot <<<")
        sistema_estado["ejecutando"] = True
        sistema_estado["hilo"] = threading.Thread(target=ejecutar_robot_bucle, daemon=True)
        sistema_estado["hilo"].start()
        print(">>> Thread iniciado <<<")

        return redirect(url_for('index'))
    except Exception as e:
        print(f">>> ERROR en /iniciar: {e} <<<")
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


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PANEL WEB ALSUA - INICIANDO")
    print("="*60)
    print("Servidor: http://localhost:5051")
    print("Acceso local: http://127.0.0.1:5051")
    print("Acceso red: http://<IP_COMPUTADORA>:5051")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5051, debug=True, use_reloader=False)
