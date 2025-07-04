# Módulo para analizar archivos Excel
import pandas as pd

def parse_xls(ruta_archivo, determinante_from_asunto=None):
    try:
        print(f"📄 Leyendo archivo: {ruta_archivo}")

        # Forzar el uso de xlrd para archivos .xls
        df = pd.read_excel(ruta_archivo, skiprows=6, header=0, engine="xlrd")

        if df.empty:
            return {"error": "Archivo vacío"}

        fila = df.iloc[0]

        tipo_viaje = str(fila.get("Tipo de Viaje", "")).strip().upper()
        if tipo_viaje != "VACIO":
            return {"error": "El viaje no es tipo VACIO"}

        fecha = str(fila.get("Fecha de Embarque", "")).split(" ")[0]
        placa_remolque = str(fila.get("Placa Remolque", "")).strip()
        placa_tractor = str(fila.get("Placa Tractor", "")).strip()
        entrega = str(fila.get("Entrega1", ""))

        if len(entrega) == 4 and entrega.isdigit():
            determinante = entrega
        else:
            determinante = determinante_from_asunto or "0000"

        total_str = str(fila.get("$Total de Viaje a Facturar", "0")).replace("$", "").replace(",", "").strip()
        try:
            importe = float(total_str)
        except:
            importe = 0.0

        # Como no podemos leer celda F4 en .xls, dejamos prefactura vacía
        prefactura = ""
        
        # NUEVO: Agregar cliente_codigo por defecto
        cliente_codigo = "040512"  # Código por defecto para Walmart

        return {
            "prefactura": prefactura,
            "fecha": fecha,
            "tipo_viaje": tipo_viaje,
            "placa_remolque": placa_remolque,
            "placa_tractor": placa_tractor,
            "clave_determinante": determinante,
            "importe": importe,
            "cliente_codigo": cliente_codigo  # AGREGADO
        }

    except Exception as e:
        return {"error": str(e)}