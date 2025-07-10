from flask import Flask, render_template, redirect
import threading
import time
from alsua_mail_automation import AlsuaMailAutomation
from modules.mysql_simple import mysql_acumulado

app = Flask(__name__)
estado = {"ejecutando": False, "hilo": None}

def ejecutar_bucle():
    sistema = AlsuaMailAutomation()
    sistema.ejecutar_bucle_continuo(intervalo_minutos=5)

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
        estado["ejecutando"] = True
        estado["hilo"] = threading.Thread(target=ejecutar_bucle)
        estado["hilo"].start()
    return redirect("/")

@app.route("/detener")
def detener():
    if estado["ejecutando"]:
        estado["ejecutando"] = False
        # Esto solo detiene el flag, no mata el hilo de inmediato
        # Si quieres control más fino habría que modificar el bucle
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
