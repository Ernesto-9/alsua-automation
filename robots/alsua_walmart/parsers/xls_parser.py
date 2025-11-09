import pandas as pd
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_xls(ruta_archivo, determinante_from_asunto=None):
    try:
        logger.info(f"Leyendo archivo: {ruta_archivo}")

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
        entrega = str(fila.get("Entrega1", "")).strip()

        determinante = None
        fuente_determinante = ""
        
        determinante_asunto_valida = False
        if determinante_from_asunto:
            numeros_asunto = re.findall(r'\d+', str(determinante_from_asunto))
            if numeros_asunto:
                numero_asunto = numeros_asunto[0]
                
                if len(numero_asunto) == 4 and numero_asunto.isdigit():
                    determinante = numero_asunto
                    fuente_determinante = "ASUNTO"
                    determinante_asunto_valida = True
        
        determinante_excel_valida = False
        entrega_numero = ""
        if entrega:
            numeros_entrega = re.findall(r'\d+', entrega)
            if numeros_entrega:
                entrega_numero = numeros_entrega[0]
                
                if len(entrega_numero) == 4 and entrega_numero.isdigit():
                    determinante_excel_valida = True
        
        if determinante_asunto_valida and not determinante_excel_valida:
            determinante = numero_asunto
            fuente_determinante = "ASUNTO"
            
        elif not determinante_asunto_valida and determinante_excel_valida:
            determinante = entrega_numero
            fuente_determinante = "EXCEL"
            
        elif determinante_asunto_valida and determinante_excel_valida:
            if numero_asunto == entrega_numero:
                determinante = numero_asunto
                fuente_determinante = "AMBOS_COINCIDEN"
            else:
                determinante = numero_asunto
                fuente_determinante = "ASUNTO_CON_DISCREPANCIA"
                logger.warning(f"Discrepancia en determinantes - Asunto: {numero_asunto}, Excel: {entrega_numero}")
                
        else:
            logger.error(f"No se encontró determinante válida - Asunto: '{determinante_from_asunto}', Excel: '{entrega}'")
            return {"error": f"No se encontró determinante válida (4 dígitos). Asunto: '{determinante_from_asunto}', Excel: '{entrega}'"}

        if not determinante or len(determinante) != 4 or not determinante.isdigit():
            logger.error(f"Determinante final no válida: '{determinante}'")
            return {"error": f"Determinante final no válida: '{determinante}'"}

        total_str = str(fila.get("$Total de Viaje a Facturar", "0")).replace("$", "").replace(",", "").strip()
        try:
            importe = float(total_str)
        except:
            importe = 0.0

        prefactura = ""
        cliente_codigo = "040512"

        logger.info(f"Determinante: {determinante} (Fuente: {fuente_determinante})")

        return {
            "prefactura": prefactura,
            "fecha": fecha,
            "tipo_viaje": tipo_viaje,
            "placa_remolque": placa_remolque,
            "placa_tractor": placa_tractor,
            "clave_determinante": determinante,
            "importe": importe,
            "cliente_codigo": cliente_codigo,
            "determinante_fuente": fuente_determinante,
            "determinante_asunto_original": determinante_from_asunto,
            "determinante_excel_original": entrega
        }

    except Exception as e:
        logger.error(f"Error en parse_xls: {e}")
        return {"error": str(e)}