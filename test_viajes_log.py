#!/usr/bin/env python3
"""
Script de diagnóstico para identificar por qué no se registran viajes en viajes_log.csv
"""

import os
import sys
import traceback
from datetime import datetime

def test_basic_csv_creation():
    """Prueba básica de creación de archivo CSV"""
    print("="*60)
    print("🧪 PRUEBA 1: Creación básica de archivo CSV")
    print("="*60)
    
    try:
        # Verificar directorio actual
        print(f"📁 Directorio actual: {os.getcwd()}")
        
        # Intentar crear archivo CSV básico
        csv_path = "viajes_log.csv"
        print(f"📄 Intentando crear: {csv_path}")
        
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("test,timestamp\n")
            f.write(f"PRUEBA,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print("✅ Archivo CSV creado exitosamente")
        
        # Verificar que se creó
        if os.path.exists(csv_path):
            print("✅ Archivo existe en disco")
            
            # Leer contenido
            with open(csv_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"📋 Contenido del archivo:\n{content}")
        else:
            print("❌ Archivo no existe después de crearlo")
            
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba básica: {e}")
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

def test_viajes_log_import():
    """Prueba de importación del módulo viajes_log"""
    print("\n" + "="*60)
    print("🧪 PRUEBA 2: Importación del módulo viajes_log")
    print("="*60)
    
    try:
        # Verificar que el archivo existe
        viajes_log_path = "viajes_log.py"
        if os.path.exists(viajes_log_path):
            print(f"✅ Archivo {viajes_log_path} existe")
        else:
            print(f"❌ Archivo {viajes_log_path} NO existe")
            return False
        
        # Intentar importar
        print("🔄 Intentando importar viajes_log...")
        import viajes_log
        print("✅ Módulo viajes_log importado exitosamente")
        
        # Verificar funciones principales
        if hasattr(viajes_log, 'registrar_viaje_exitoso'):
            print("✅ Función registrar_viaje_exitoso encontrada")
        else:
            print("❌ Función registrar_viaje_exitoso NO encontrada")
            
        if hasattr(viajes_log, 'registrar_viaje_fallido'):
            print("✅ Función registrar_viaje_fallido encontrada")
        else:
            print("❌ Función registrar_viaje_fallido NO encontrada")
            
        # Verificar instancia global
        if hasattr(viajes_log, 'viajes_log'):
            print("✅ Instancia global viajes_log encontrada")
        else:
            print("❌ Instancia global viajes_log NO encontrada")
            
        return True
        
    except Exception as e:
        print(f"❌ Error importando viajes_log: {e}")
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

def test_viajes_log_function():
    """Prueba de la función de registro de viajes"""
    print("\n" + "="*60)
    print("🧪 PRUEBA 3: Función de registro de viajes")
    print("="*60)
    
    try:
        # Importar el módulo
        import viajes_log
        
        # Datos de prueba (basados en tu log)
        datos_prueba = {
            'prefactura': '8076137',
            'determinante': '2899',  # Ejemplo
            'fecha_viaje': '15/01/2025',
            'placa_tractor': '007EY7',
            'placa_remolque': '60UJ4P',
            'uuid': '5A376C15-39CE-45DD-B28A-BD9D26392042',
            'viajegm': 'HMO-65063',
            'importe': '310.75',
            'cliente_codigo': '040512'
        }
        
        print("📋 Datos de prueba:")
        for key, value in datos_prueba.items():
            print(f"   {key}: {value}")
        
        print("\n🔄 Llamando a registrar_viaje_exitoso...")
        
        # Llamar a la función
        resultado = viajes_log.registrar_viaje_exitoso(
            prefactura=datos_prueba['prefactura'],
            determinante=datos_prueba['determinante'],
            fecha_viaje=datos_prueba['fecha_viaje'],
            placa_tractor=datos_prueba['placa_tractor'],
            placa_remolque=datos_prueba['placa_remolque'],
            uuid=datos_prueba['uuid'],
            viajegm=datos_prueba['viajegm'],
            importe=datos_prueba['importe'],
            cliente_codigo=datos_prueba['cliente_codigo']
        )
        
        print(f"📊 Resultado de la función: {resultado}")
        
        if resultado:
            print("✅ Función ejecutada exitosamente")
            
            # Verificar que el archivo se creó
            if os.path.exists("viajes_log.csv"):
                print("✅ Archivo viajes_log.csv creado")
                
                # Leer el contenido
                with open("viajes_log.csv", 'r', encoding='utf-8') as f:
                    content = f.read()
                    print("📋 Contenido del archivo CSV:")
                    print(content)
                    
                    # Verificar que contiene nuestros datos
                    if datos_prueba['prefactura'] in content:
                        print("✅ Datos de prefactura encontrados en CSV")
                    else:
                        print("❌ Datos de prefactura NO encontrados en CSV")
            else:
                print("❌ Archivo viajes_log.csv NO fue creado")
        else:
            print("❌ Función retornó False")
            
        return resultado
        
    except Exception as e:
        print(f"❌ Error en función de registro: {e}")
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

def test_csv_permissions():
    """Prueba de permisos del archivo CSV"""
    print("\n" + "="*60)
    print("🧪 PRUEBA 4: Permisos del archivo CSV")
    print("="*60)
    
    try:
        csv_path = "viajes_log.csv"
        
        # Verificar permisos de lectura
        if os.access(csv_path, os.R_OK):
            print("✅ Permisos de lectura: OK")
        else:
            print("❌ Permisos de lectura: FALLO")
            
        # Verificar permisos de escritura
        if os.access(csv_path, os.W_OK):
            print("✅ Permisos de escritura: OK")
        else:
            print("❌ Permisos de escritura: FALLO")
            
        # Información del archivo
        if os.path.exists(csv_path):
            stat = os.stat(csv_path)
            print(f"📊 Tamaño del archivo: {stat.st_size} bytes")
            print(f"📅 Última modificación: {datetime.fromtimestamp(stat.st_mtime)}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error verificando permisos: {e}")
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

def test_direct_csv_write():
    """Prueba de escritura directa en CSV"""
    print("\n" + "="*60)
    print("🧪 PRUEBA 5: Escritura directa en CSV")
    print("="*60)
    
    try:
        import csv
        
        # Campos del CSV
        campos = [
            'timestamp',
            'prefactura', 
            'determinante',
            'fecha_viaje',
            'placa_tractor',
            'placa_remolque',
            'estatus',
            'motivo_fallo',
            'uuid',
            'viajegm',
            'importe',
            'cliente_codigo'
        ]
        
        # Datos de prueba
        registro = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'prefactura': '8076137',
            'determinante': '2899',
            'fecha_viaje': '15/01/2025',
            'placa_tractor': '007EY7',
            'placa_remolque': '60UJ4P',
            'estatus': 'EXITOSO',
            'motivo_fallo': '',
            'uuid': '5A376C15-39CE-45DD-B28A-BD9D26392042',
            'viajegm': 'HMO-65063',
            'importe': '310.75',
            'cliente_codigo': '040512'
        }
        
        csv_path = "viajes_log_test.csv"
        
        print(f"📄 Escribiendo directamente en: {csv_path}")
        
        # Escribir con headers
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerow(registro)
            
        print("✅ Escritura directa exitosa")
        
        # Verificar contenido
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print("📋 Contenido del archivo:")
            print(content)
            
        return True
        
    except Exception as e:
        print(f"❌ Error en escritura directa: {e}")
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

def main():
    """Función principal de diagnóstico"""
    print("🔍 DIAGNÓSTICO DE VIAJES_LOG.CSV")
    print("=" * 80)
    print("Este script identificará por qué no se registran los viajes en CSV")
    print("=" * 80)
    
    # Lista de pruebas
    pruebas = [
        ("Creación básica de CSV", test_basic_csv_creation),
        ("Importación de viajes_log", test_viajes_log_import),
        ("Función de registro", test_viajes_log_function),
        ("Permisos del archivo", test_csv_permissions),
        ("Escritura directa CSV", test_direct_csv_write)
    ]
    
    resultados = []
    
    for nombre, prueba in pruebas:
        print(f"\n🚀 Ejecutando: {nombre}")
        try:
            resultado = prueba()
            resultados.append((nombre, resultado))
            
            if resultado:
                print(f"✅ {nombre}: EXITOSO")
            else:
                print(f"❌ {nombre}: FALLIDO")
                
        except Exception as e:
            print(f"💥 {nombre}: ERROR CRÍTICO - {e}")
            resultados.append((nombre, False))
    
    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN DEL DIAGNÓSTICO")
    print("="*80)
    
    exitosos = 0
    for nombre, resultado in resultados:
        status = "✅ EXITOSO" if resultado else "❌ FALLIDO"
        print(f"{status}: {nombre}")
        if resultado:
            exitosos += 1
    
    print(f"\n📈 Resultado: {exitosos}/{len(resultados)} pruebas exitosas")
    
    if exitosos == len(resultados):
        print("🎉 ¡Todas las pruebas pasaron! El problema podría estar en el flujo de ejecución.")
    else:
        print("🚨 Se encontraron problemas. Revisa los fallos arriba.")
    
    print("\n💡 Próximos pasos:")
    print("1. Revisa los resultados de las pruebas fallidas")
    print("2. Si todas pasaron, el problema está en el flujo de la aplicación")
    print("3. Comparte estos resultados para análisis adicional")

if __name__ == "__main__":
    main()