#!/usr/bin/env python3
"""
Script de limpieza de archivos temporales
Elimina PDFs, Excel y archivos Flask obsoletos de forma segura
"""

import os
import shutil
from pathlib import Path

def contar_archivos(carpeta, extension):
    """Cuenta archivos con extensión específica en una carpeta"""
    if not os.path.exists(carpeta):
        return 0
    return len(list(Path(carpeta).glob(f"**/*{extension}")))

def obtener_tamano(carpeta):
    """Obtiene tamaño de una carpeta en MB"""
    if not os.path.exists(carpeta):
        return 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(carpeta):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total += os.path.getsize(filepath)
            except:
                pass
    return total / (1024 * 1024)  # Convertir a MB

def limpiar_carpeta(carpeta, descripcion):
    """Elimina todos los archivos de una carpeta"""
    if not os.path.exists(carpeta):
        print(f"   ⚠️  {carpeta} no existe")
        return 0

    archivos_eliminados = 0
    for archivo in Path(carpeta).glob("*"):
        if archivo.is_file():
            try:
                os.remove(archivo)
                archivos_eliminados += 1
            except Exception as e:
                print(f"   ❌ Error eliminando {archivo.name}: {e}")

    return archivos_eliminados

def main():
    print("=" * 70)
    print("LIMPIEZA DE ARCHIVOS TEMPORALES - Alsua Automation")
    print("=" * 70)
    print()

    # Analizar qué se va a eliminar
    print("📊 ANÁLISIS DE ARCHIVOS:")
    print()

    # Carpeta archivos_descargados
    xls_count = contar_archivos("archivos_descargados", ".xls")
    xlsx_count = contar_archivos("archivos_descargados", ".xlsx")
    archivos_desc_size = obtener_tamano("archivos_descargados")
    print(f"1. archivos_descargados/")
    print(f"   • {xls_count} archivos .xls")
    print(f"   • {xlsx_count} archivos .xlsx")
    print(f"   • Tamaño total: {archivos_desc_size:.2f} MB")
    print()

    # Carpeta pdfs_temporales
    pdf_count = contar_archivos("pdfs_temporales", ".pdf")
    pdfs_size = obtener_tamano("pdfs_temporales")
    print(f"2. pdfs_temporales/")
    print(f"   • {pdf_count} archivos .pdf")
    print(f"   • Tamaño total: {pdfs_size:.2f} MB")
    print()

    # Template viejo
    index_exists = os.path.exists("templates/index.html")
    print(f"3. templates/index.html (Flask template obsoleto)")
    print(f"   • {'Existe' if index_exists else 'No existe'}")
    print(f"   • Flask usa: dashboard.html (el correcto)")
    print()

    # Total
    total_archivos = xls_count + xlsx_count + pdf_count + (1 if index_exists else 0)
    total_size = archivos_desc_size + pdfs_size
    print(f"📦 TOTAL A ELIMINAR:")
    print(f"   • {total_archivos} archivos")
    print(f"   • {total_size:.2f} MB liberados")
    print()

    # Confirmación
    print("=" * 70)
    respuesta = input("¿Deseas continuar con la limpieza? (SI/no): ").strip().upper()

    if respuesta != "SI":
        print("\n❌ Limpieza cancelada por el usuario")
        return

    print()
    print("=" * 70)
    print("🧹 INICIANDO LIMPIEZA...")
    print("=" * 70)
    print()

    # Limpiar archivos_descargados
    print("1. Limpiando archivos_descargados/")
    eliminados = limpiar_carpeta("archivos_descargados", "Excel descargados")
    print(f"   ✅ {eliminados} archivos eliminados")
    print()

    # Limpiar pdfs_temporales
    print("2. Limpiando pdfs_temporales/")
    eliminados = limpiar_carpeta("pdfs_temporales", "PDFs temporales")
    print(f"   ✅ {eliminados} archivos eliminados")
    print()

    # Eliminar index.html
    print("3. Eliminando templates/index.html")
    if index_exists:
        try:
            os.remove("templates/index.html")
            print(f"   ✅ Archivo eliminado")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print(f"   ⚠️  Archivo no existe")
    print()

    print("=" * 70)
    print("✅ LIMPIEZA COMPLETADA")
    print("=" * 70)
    print()
    print("NOTA: Las carpetas archivos_descargados/ y pdfs_temporales/ se")
    print("      volverán a llenar conforme el robot procese nuevos viajes.")
    print("      Esto es normal y esperado.")
    print()

if __name__ == "__main__":
    main()
