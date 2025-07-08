#!/usr/bin/env python3
"""
Script de limpieza COMPLETA para resolver problemas de duplicados
Incluye limpieza de archivos Excel descargados
"""

import os
import pickle
import glob
import win32com.client
from datetime import datetime, timedelta

def limpiar_correos_procesados():
    """Elimina el archivo de correos procesados"""
    archivo = "correos_procesados.pkl"
    if os.path.exists(archivo):
        os.remove(archivo)
        print("✅ Archivo de correos procesados eliminado")
    else:
        print("ℹ️ No existe archivo de correos procesados")

def limpiar_viajes_creados():
    """Elimina el archivo de viajes creados"""
    archivo = "viajes_creados.pkl"
    if os.path.exists(archivo):
        os.remove(archivo)
        print("✅ Archivo de viajes creados eliminado")
    else:
        print("ℹ️ No existe archivo de viajes creados")

def limpiar_archivos_excel():
    """Elimina TODOS los archivos Excel descargados"""
    carpetas_posibles = [
        "archivos_descargados",
        os.path.join(os.path.expanduser("~"), "Downloads", "alsua_archivos")
    ]
    
    total_eliminados = 0
    
    for carpeta in carpetas_posibles:
        if os.path.exists(carpeta):
            print(f"📁 Limpiando carpeta: {carpeta}")
            
            # Buscar archivos .xls
            archivos_xls = glob.glob(os.path.join(carpeta, "*.xls"))
            
            for archivo in archivos_xls:
                try:
                    os.remove(archivo)
                    total_eliminados += 1
                    print(f"   🗑️ Eliminado: {os.path.basename(archivo)}")
                except Exception as e:
                    print(f"   ❌ Error eliminando {os.path.basename(archivo)}: {e}")
    
    if total_eliminados > 0:
        print(f"✅ Total archivos Excel eliminados: {total_eliminados}")
    else:
        print("ℹ️ No se encontraron archivos Excel para eliminar")

def limpiar_logs():
    """Elimina archivos de log"""
    archivos_log = [
        "alsua_automation.log",
        "viajes_requieren_revision.log",
        "errores_viajes.log"
    ]
    
    eliminados = 0
    for archivo in archivos_log:
        if os.path.exists(archivo):
            os.remove(archivo)
            eliminados += 1
            print(f"✅ Log eliminado: {archivo}")
    
    if eliminados == 0:
        print("ℹ️ No se encontraron archivos de log")

def marcar_correos_como_leidos():
    """Marca todos los correos de Walmart como leídos"""
    try:
        print("📧 Conectando a Outlook...")
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.GetDefaultFolder(6)
        
        # Filtrar correos de Walmart no leídos
        filtro = "[UnRead] = True AND [SenderEmailAddress] LIKE '%walmart.com%'"
        mensajes = inbox.Items.Restrict(filtro)
        
        count = 0
        for mensaje in mensajes:
            try:
                mensaje.UnRead = False
                count += 1
            except:
                continue
                
        print(f"✅ {count} correos de Walmart marcados como leídos")
        
    except Exception as e:
        print(f"❌ Error marcando correos: {e}")

def mostrar_estadisticas():
    """Muestra estadísticas de archivos de tracking y archivos"""
    print("\n" + "="*60)
    print("📊 ESTADÍSTICAS COMPLETAS DEL SISTEMA")
    print("="*60)
    
    # Correos procesados
    archivo_correos = "correos_procesados.pkl"
    if os.path.exists(archivo_correos):
        try:
            with open(archivo_correos, 'rb') as f:
                correos = pickle.load(f)
            print(f"📧 Correos procesados: {len(correos)}")
            
            # Mostrar últimos 5
            if correos:
                print("   Últimos procesados:")
                items = list(correos.items())[-5:]
                for key, value in items:
                    fecha = value.get('fecha_procesado', 'Desconocida')
                    estado = value.get('estado', 'Desconocido')
                    prefactura = value.get('prefactura', 'Sin prefactura')
                    print(f"     - {prefactura} | {estado} | {fecha}")
        except Exception as e:
            print(f"❌ Error leyendo correos: {e}")
    else:
        print("📧 No hay archivo de correos procesados")
    
    # Viajes creados
    archivo_viajes = "viajes_creados.pkl"
    if os.path.exists(archivo_viajes):
        try:
            with open(archivo_viajes, 'rb') as f:
                viajes = pickle.load(f)
            print(f"🚛 Viajes creados: {len(viajes)}")
            
            # Mostrar últimos 5
            if viajes:
                print("   Últimos creados:")
                items = list(viajes.items())[-5:]
                for key, value in items:
                    fecha = value.get('fecha_creado', 'Desconocida')
                    estado = value.get('estado', 'Desconocido')
                    datos = value.get('datos', {})
                    prefactura = datos.get('prefactura', 'Sin prefactura')
                    print(f"     - {prefactura} | {estado} | {fecha}")
        except Exception as e:
            print(f"❌ Error leyendo viajes: {e}")
    else:
        print("🚛 No hay archivo de viajes creados")
    
    # Archivos Excel
    carpetas_posibles = [
        "archivos_descargados",
        os.path.join(os.path.expanduser("~"), "Downloads", "alsua_archivos")
    ]
    
    total_excel = 0
    for carpeta in carpetas_posibles:
        if os.path.exists(carpeta):
            archivos = glob.glob(os.path.join(carpeta, "*.xls"))
            if archivos:
                print(f"📁 Archivos Excel en {carpeta}: {len(archivos)}")
                total_excel += len(archivos)
                # Mostrar algunos ejemplos
                for archivo in archivos[:3]:
                    print(f"     - {os.path.basename(archivo)}")
                if len(archivos) > 3:
                    print(f"     ... y {len(archivos) - 3} más")
    
    if total_excel == 0:
        print("📁 No hay archivos Excel almacenados")
    
    # Logs
    archivos_log = ["alsua_automation.log", "viajes_requieren_revision.log", "errores_viajes.log"]
    logs_existentes = [log for log in archivos_log if os.path.exists(log)]
    
    if logs_existentes:
        print(f"📋 Archivos de log: {len(logs_existentes)}")
        for log in logs_existentes:
            try:
                size = os.path.getsize(log) / 1024  # KB
                print(f"     - {log} ({size:.1f} KB)")
            except:
                print(f"     - {log}")
    else:
        print("📋 No hay archivos de log")

def menu_principal():
    """Menú principal de limpieza COMPLETA"""
    while True:
        print("\n" + "="*60)
        print("🧹 HERRAMIENTA DE LIMPIEZA COMPLETA ALSUA")
        print("="*60)
        print("1. Mostrar estadísticas completas")
        print("2. Limpiar SOLO correos procesados")
        print("3. Limpiar SOLO viajes creados")
        print("4. Limpiar SOLO archivos Excel descargados")
        print("5. Limpiar SOLO logs del sistema")
        print("6. Marcar correos Walmart como leídos")
        print("7. Limpiar TODO (tracking + Excel + logs)")
        print("8. RESET PARA REPROCESAR (borra todo para procesar de nuevo)")
        print("9. RESET SOLO LIMPIEZA (borra archivos pero marca correos como procesados)")
        print("0. Salir")
        print("="*60)
        
        opcion = input("Selecciona una opción: ").strip()
        
        if opcion == "1":
            mostrar_estadisticas()
        elif opcion == "2":
            limpiar_correos_procesados()
        elif opcion == "3":
            limpiar_viajes_creados()
        elif opcion == "4":
            limpiar_archivos_excel()
        elif opcion == "5":
            limpiar_logs()
        elif opcion == "6":
            marcar_correos_como_leidos()
        elif opcion == "7":
            print("🧹 LIMPIEZA COMPLETA DE ARCHIVOS...")
            limpiar_correos_procesados()
            limpiar_viajes_creados()
            limpiar_archivos_excel()
            limpiar_logs()
            print("✅ Limpieza completa de archivos realizada")
        elif opcion == "8":
            print("🔄 RESET PARA REPROCESAR - Borrando todo para que vuelva a procesar correos...")
            limpiar_correos_procesados()
            limpiar_viajes_creados()
            limpiar_archivos_excel()
            limpiar_logs()
            # NO marcar correos como leídos - los volverá a procesar
            print("✅ RESET PARA REPROCESAR COMPLETADO")
            print("🔄 El sistema volverá a procesar todos los correos no leídos")
        elif opcion == "9":
            print("🧹 RESET SOLO LIMPIEZA - Borrando archivos pero marcando correos como procesados...")
            limpiar_correos_procesados()
            limpiar_viajes_creados()
            limpiar_archivos_excel()
            limpiar_logs()
            marcar_correos_como_leidos()  # SÍ marcar como leídos
            print("✅ RESET SOLO LIMPIEZA COMPLETADO")
            print("🧹 Archivos limpiados, correos marcados como procesados")
        elif opcion == "0":
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    menu_principal()