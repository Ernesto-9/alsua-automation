#!/usr/bin/env python3
"""
Script para eliminar la columna NF de la tabla acumuladoprefactura
Solo ejecutar UNA VEZ y después borrar este archivo
"""

import mysql.connector
from mysql.connector import Error

# Datos de conexión
MYSQL_CONFIG = {
    'host': '104.251.211.6',
    'port': 3306,
    'user': 'alsua',
    'password': '&/?37jejJdirbt782@28',
    'database': 'alsua'
}

def eliminar_columna_nf():
    try:
        print("🔌 Conectando a MySQL...")
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Verificar que la columna NF existe
            print("🔍 Verificando si la columna NF existe...")
            cursor.execute("DESCRIBE acumuladoprefactura")
            columnas = cursor.fetchall()
            
            nf_existe = any(columna[0] == 'NF' for columna in columnas)
            
            if nf_existe:
                print("✅ Columna NF encontrada")
                
                # Eliminar la columna NF
                print("🗑️ Eliminando columna NF...")
                cursor.execute("ALTER TABLE acumuladoprefactura DROP COLUMN NF")
                connection.commit()
                
                print("✅ Columna NF eliminada exitosamente")
                
                # Verificar que se eliminó
                print("🔍 Verificando eliminación...")
                cursor.execute("DESCRIBE acumuladoprefactura")
                columnas_nuevas = cursor.fetchall()
                
                nf_eliminada = not any(columna[0] == 'NF' for columna in columnas_nuevas)
                
                if nf_eliminada:
                    print("🎉 ¡ÉXITO! Columna NF eliminada correctamente")
                    print("📊 Estructura actualizada de la tabla:")
                    for columna in columnas_nuevas[:10]:  # Mostrar solo las primeras 10
                        field, type_, null, key, default, extra = columna
                        print(f"   - {field}: {type_}")
                    if len(columnas_nuevas) > 10:
                        print(f"   ... y {len(columnas_nuevas) - 10} columnas más")
                else:
                    print("❌ La columna NF aún existe")
            else:
                print("ℹ️ La columna NF ya no existe en la tabla")
            
            cursor.close()
            connection.close()
            print("✅ Conexión cerrada")
            
        else:
            print("❌ No se pudo conectar a MySQL")
            return False
            
    except Error as e:
        print(f"❌ Error MySQL: {e}")
        print(f"   Error Code: {e.errno}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚨 ADVERTENCIA: Este script eliminará la columna NF de la tabla acumuladoprefactura")
    confirmar = input("¿Estás seguro de que quieres continuar? (escribe 'SI' para confirmar): ")
    
    if confirmar.upper() == 'SI':
        exito = eliminar_columna_nf()
        
        if exito:
            print("\n" + "="*60)
            print("🎉 PROCESO COMPLETADO EXITOSAMENTE")
            print("📝 Ahora puedes:")
            print("   1. Borrar este archivo (eliminar_columna_nf.py)")
            print("   2. Probar el mysql_simple.py corregido")
            print("   3. Continuar con la automatización")
            print("="*60)
        else:
            print("\n❌ PROCESO FALLÓ - Revisa los errores arriba")
    else:
        print("❌ Operación cancelada por el usuario")