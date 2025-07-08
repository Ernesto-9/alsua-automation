#!/usr/bin/env python3
"""
Script de limpieza para resolver problemas de duplicados
Ejecutar cuando haya conflictos de operadores ocupados
"""

import os
import pickle
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

def marcar_correos_como_leidos():
    """Marca todos los correos de Walmart como leídos"""
    try:
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
    """Muestra estadísticas de archivos de tracking"""
    print("\n" + "="*50)
    print("📊 ESTADÍSTICAS DE TRACKING")
    print("="*50)
    
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

def menu_principal():
    """Menú principal de limpieza"""
    while True:
        print("\n" + "="*50)
        print("🧹 HERRAMIENTA DE LIMPIEZA ALSUA")
        print("="*50)
        print("1. Mostrar estadísticas")
        print("2. Limpiar SOLO correos procesados")
        print("3. Limpiar SOLO viajes creados")
        print("4. Limpiar TODO (correos + viajes)")
        print("5. Marcar correos Walmart como leídos")
        print("6. RESET COMPLETO (limpiar todo + marcar leídos)")
        print("0. Salir")
        print("="*50)
        
        opcion = input("Selecciona una opción: ").strip()
        
        if opcion == "1":
            mostrar_estadisticas()
        elif opcion == "2":
            limpiar_correos_procesados()
        elif opcion == "3":
            limpiar_viajes_creados()
        elif opcion == "4":
            limpiar_correos_procesados()
            limpiar_viajes_creados()
            print("✅ Limpieza completa realizada")
        elif opcion == "5":
            marcar_correos_como_leidos()
        elif opcion == "6":
            print("⚠️ RESET COMPLETO - Esto limpiará TODA la información de tracking")
            confirmar = input("¿Estás seguro? (sí/no): ").strip().lower()
            if confirmar in ['sí', 'si', 'yes', 'y']:
                limpiar_correos_procesados()
                limpiar_viajes_creados()
                marcar_correos_como_leidos()
                print("🎉 Reset completo realizado")
            else:
                print("❌ Operación cancelada")
        elif opcion == "0":
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    menu_principal()