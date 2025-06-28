import os
import win32com.client
from modules.parser import parse_xls
from datetime import datetime

def process_emails():
    print("📬 Iniciando lectura de correos...")

    carpeta_descarga = "archivos_descargados"
    if not os.path.exists(carpeta_descarga):
        os.makedirs(carpeta_descarga)

    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    inbox = outlook.GetDefaultFolder(6)  # Bandeja de entrada

    mensajes = inbox.Items
    mensajes.Sort("[ReceivedTime]", True)  # Más recientes primero

    for mensaje in mensajes:
        try:
            asunto = mensaje.Subject or ""
            remitente = mensaje.SenderEmailAddress or ""
            adjuntos = mensaje.Attachments

            # Evitamos correos no deseados
            if "cancelado" in asunto.lower() or "no-reply" in remitente.lower():
                continue

            if adjuntos.Count == 0:
                continue

            print(f"📩 Procesando: {asunto}")

            # Buscar clave determinante de 4 dígitos en el asunto
            import re
            match = re.search(r"\b\d{4}\b", asunto)
            clave_determinante = match.group(0) if match else None

            for i in range(1, adjuntos.Count + 1):
                archivo = adjuntos.Item(i)
                nombre = archivo.FileName

                if not nombre.endswith(".xls"):
                    continue

                ruta_local = os.path.join(carpeta_descarga, nombre)
                if os.path.exists(ruta_local):
                    print(f"⚠️ Ya existe: {ruta_local}, omitiendo.")
                    continue

                archivo.SaveAsFile(ruta_local)
                print(f"📥 Guardado: {ruta_local}")

                resultado = parse_xls(ruta_local, determinante_from_asunto=clave_determinante)

                if "error" in resultado:
                    print(f"❌ No válido: {resultado['error']}")
                    os.remove(ruta_local)  # Limpieza opcional
                else:
                    print("✅ Viaje válido tipo VACIO:")
                    print(resultado)

        except Exception as e:
            print(f"❗ Error al procesar correo: {e}")
