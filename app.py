from flask import Flask, render_template, redirect
import threading
import time
from alsua_mail_automation import AlsuaMailAutomation
from modules.mysql_simple import mysql_acumulado

app = Flask(_name_)
estado = {"ejecutando": False, "hilo": None}

def ejecutar_bucle():
    print(">>> Iniciando hilo de automatización desde Flask <<<")
    try:
        sistema = AlsuaMailAutomation()
        print(">>> Instancia creada, ejecutando bucle continuo <<<")
        sistema.ejecutar_bucle_continuo(intervalo_minutos=5)
    except Exception as e:
        print(f"Error en ejecución del bucle: {e}")

@app.route("/")
def index():
    try:
        if not mysql_acumulado.conectar():
            viajes = []
        else:
            cursor = mysql_acumulado.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    NOPREFACTURA as prefactura, 
                    FECHA as fecha, 
                    TOTALFACTURA2 as importe, 
                    estatus, 
                    anotaciones 
                FROM acumuladoprefactura 
                WHERE estatus IN ('EXITOSO', 'FALLIDO')
                ORDER BY FECHA DESC, NUMERO DESC
                LIMIT 15
            """)
            viajes = cursor.fetchall()
            cursor.close()
    except Exception as e:
        print(f"Error leyendo viajes: {e}")
        viajes = []

    return render_template("index.html", estado=estado, viajes=viajes)

@app.route("/iniciar")
def iniciar():
    if not estado["ejecutando"]:
        print(">>> Botón Iniciar presionado <<<")
        estado["ejecutando"] = True
        estado["hilo"] = threading.Thread(target=ejecutar_bucle)
        estado["hilo"].start()
    else:
        print(">>> Ya se estaba ejecutando la automatización <<<")
    return redirect("/")

@app.route("/detener")
def detener():
    if estado["ejecutando"]:
        print(">>> Botón Detener presionado <<<")
        estado["ejecutando"] = False
        # Solo detiene el flag, no mata el hilo de inmediato
    return redirect("/")

if _name_ == "_main_":
    app.run(debug=False, host="0.0.0.0", port=5050)