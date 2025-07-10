# Módulo para analizar archivos Excel
import pandas as pd
import re
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_xls(ruta_archivo, determinante_from_asunto=None):
    try:
        logger.info(f"📄 Leyendo archivo: {ruta_archivo}")
        logger.info(f"🔍 Determinante del asunto recibida: {determinante_from_asunto}")

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
        entrega = str(fila.get("Entrega1", "")).strip()

        # ==========================================
        # LÓGICA MEJORADA PARA CLAVE DETERMINANTE
        # ==========================================
        
        determinante = None
        fuente_determinante = ""
        
        # PASO 1: Analizar determinante del asunto
        determinante_asunto_valida = False
        if determinante_from_asunto:
            # Extraer solo números del asunto
            numeros_asunto = re.findall(r'\d+', str(determinante_from_asunto))
            if numeros_asunto:
                numero_asunto = numeros_asunto[0]  # Tomar el primer número encontrado
                logger.info(f"🔍 Número extraído del asunto: '{numero_asunto}' (longitud: {len(numero_asunto)})")
                
                if len(numero_asunto) == 4 and numero_asunto.isdigit():
                    determinante = numero_asunto
                    fuente_determinante = "ASUNTO"
                    determinante_asunto_valida = True
                    logger.info(f"✅ Determinante válida del ASUNTO: {determinante}")
                else:
                    logger.info(f"⚠️ Determinante del asunto NO es de 4 dígitos: '{numero_asunto}' ({len(numero_asunto)} dígitos)")
        else:
            logger.info("ℹ️ No se recibió determinante del asunto")
        
        # PASO 2: Analizar determinante del Excel (Entrega1)
        determinante_excel_valida = False
        entrega_numero = ""
        if entrega:
            # Extraer solo números de Entrega1
            numeros_entrega = re.findall(r'\d+', entrega)
            if numeros_entrega:
                entrega_numero = numeros_entrega[0]  # Tomar el primer número
                logger.info(f"🔍 Número extraído de Entrega1: '{entrega_numero}' (longitud: {len(entrega_numero)})")
                
                if len(entrega_numero) == 4 and entrega_numero.isdigit():
                    determinante_excel_valida = True
                    logger.info(f"✅ Determinante válida del EXCEL: {entrega_numero}")
                else:
                    logger.info(f"⚠️ Determinante del Excel NO es de 4 dígitos: '{entrega_numero}' ({len(entrega_numero)} dígitos)")
            else:
                logger.info(f"⚠️ No se encontraron números en Entrega1: '{entrega}'")
        else:
            logger.info("⚠️ Campo Entrega1 está vacío")
        
        # PASO 3: Decidir qué determinante usar según la lógica de negocio
        if determinante_asunto_valida and not determinante_excel_valida:
            # Caso 1: Asunto válido, Excel no válido
            determinante = numero_asunto
            fuente_determinante = "ASUNTO"
            logger.info(f"🎯 CASO 1: Usando determinante del ASUNTO: {determinante}")
            
        elif not determinante_asunto_valida and determinante_excel_valida:
            # Caso 2: Asunto no válido, Excel válido  
            determinante = entrega_numero
            fuente_determinante = "EXCEL"
            logger.info(f"🎯 CASO 2: Usando determinante del EXCEL: {determinante}")
            
        elif determinante_asunto_valida and determinante_excel_valida:
            # Caso 3: Ambos válidos - VERIFICACIÓN CRUZADA
            if numero_asunto == entrega_numero:
                determinante = numero_asunto
                fuente_determinante = "AMBOS_COINCIDEN"
                logger.info(f"🎯 CASO 3A: Ambos válidos y COINCIDEN: {determinante}")
            else:
                # Ambos válidos pero diferentes - usar ASUNTO por defecto pero reportar discrepancia
                determinante = numero_asunto
                fuente_determinante = "ASUNTO_CON_DISCREPANCIA"
                logger.warning(f"🚨 CASO 3B: DISCREPANCIA detectada!")
                logger.warning(f"   📧 Asunto: {numero_asunto}")
                logger.warning(f"   📊 Excel: {entrega_numero}")
                logger.warning(f"   🎯 Usando ASUNTO por defecto: {determinante}")
                
        else:
            # Caso 4: Ninguno válido
            logger.error("❌ CASO 4: NO se encontró determinante válida en ninguna fuente")
            logger.error(f"   📧 Asunto: '{determinante_from_asunto}' -> '{numero_asunto if 'numero_asunto' in locals() else 'N/A'}'")
            logger.error(f"   📊 Excel: '{entrega}' -> '{entrega_numero if entrega_numero else 'N/A'}'")
            return {"error": f"No se encontró determinante válida (4 dígitos). Asunto: '{determinante_from_asunto}', Excel: '{entrega}'"}

        # PASO 4: Validación final
        if not determinante or len(determinante) != 4 or not determinante.isdigit():
            logger.error(f"❌ Determinante final no válida: '{determinante}'")
            return {"error": f"Determinante final no válida: '{determinante}'"}

        total_str = str(fila.get("$Total de Viaje a Facturar", "0")).replace("$", "").replace(",", "").strip()
        try:
            importe = float(total_str)
        except:
            importe = 0.0

        # Como no podemos leer celda F4 en .xls, dejamos prefactura vacía
        prefactura = ""
        
        # Código por defecto para Walmart
        cliente_codigo = "040512"

        # LOG FINAL
        logger.info("=" * 60)
        logger.info("📊 RESUMEN FINAL DE DETERMINANTE:")
        logger.info(f"   🎯 Determinante seleccionada: {determinante}")
        logger.info(f"   📍 Fuente: {fuente_determinante}")
        logger.info(f"   📧 Del asunto: {numero_asunto if 'numero_asunto' in locals() else 'N/A'} ({'✅' if determinante_asunto_valida else '❌'})")
        logger.info(f"   📊 Del Excel: {entrega_numero if entrega_numero else 'N/A'} ({'✅' if determinante_excel_valida else '❌'})")
        logger.info("=" * 60)

        return {
            "prefactura": prefactura,
            "fecha": fecha,
            "tipo_viaje": tipo_viaje,
            "placa_remolque": placa_remolque,
            "placa_tractor": placa_tractor,
            "clave_determinante": determinante,
            "importe": importe,
            "cliente_codigo": cliente_codigo,
            # NUEVO: Información adicional para debugging
            "determinante_fuente": fuente_determinante,
            "determinante_asunto_original": determinante_from_asunto,
            "determinante_excel_original": entrega
        }

    except Exception as e:
        logger.error(f"❌ Error general en parse_xls: {e}")
        return {"error": str(e)}