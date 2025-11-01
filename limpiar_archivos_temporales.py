#!/usr/bin/env python3
"""
Script de limpieza de archivos temporales
Elimina PDFs, Excel, logs y archivos Flask obsoletos de forma segura
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

def obtener_tamano_archivo(archivo):
    """Obtiene tamaño de un archivo en MB"""
    if not os.path.exists(archivo):
        return 0
    try:
        return os.path.getsize(archivo) / (1024 * 1024)
    except:
        return 0

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
    print(f"2. pdfs_temporales/ ⚠️  IMPORTANTE: Respalda estos PDFs antes de continuar")
    print(f"   • {pdf_count} archivos .pdf")
    print(f"   • Tamaño total: {pdfs_size:.2f} MB")
    print()

    # Template viejo
    index_exists = os.path.exists("templates/index.html")
    print(f"3. templates/index.html (Flask template obsoleto)")
    print(f"   • {'Existe' if index_exists else 'No existe'}")
    print(f"   • Flask usa: dashboard.html (el correcto)")
    print()

    # Logs de Flask (GRANDES)
    flask_stderr_size = obtener_tamano_archivo("flask_stderr.log")
    flask_stdout_size = obtener_tamano_archivo("flask_stdout.log")
    debug_log_size = obtener_tamano_archivo("debug.log")
    logs_existen = os.path.exists("flask_stderr.log") or os.path.exists("flask_stdout.log") or os.path.exists("debug.log")

    print(f"4. Logs de Flask (causa carga al sistema):")
    if os.path.exists("flask_stderr.log"):
        print(f"   • flask_stderr.log: {flask_stderr_size:.2f} MB")
    if os.path.exists("flask_stdout.log"):
        print(f"   • flask_stdout.log: {flask_stdout_size:.2f} MB")
    if os.path.exists("debug.log"):
        print(f"   • debug.log: {debug_log_size:.2f} MB")
    if not logs_existen:
        print(f"   • No hay logs (esto es normal)")
    print()

    # Archivos de análisis temporal (lista_*.txt)
    archivos_lista = [
        "lista_archivos.txt",
        "lista_templates.txt",
        "lista_modules.txt",
        "lista_pdfs_count.txt",
        "lista_excel_count.txt"
    ]
    listas_count = sum(1 for f in archivos_lista if os.path.exists(f))

    print(f"5. Archivos temporales de análisis:")
    print(f"   • {listas_count} archivos lista_*.txt")
    print()

    # Total
    total_archivos = xls_count + xlsx_count + pdf_count + (1 if index_exists else 0) + listas_count
    total_size = archivos_desc_size + pdfs_size + flask_stderr_size + flask_stdout_size + debug_log_size
    print(f"📦 TOTAL A ELIMINAR:")
    print(f"   • {total_archivos} archivos")
    print(f"   • {total_size:.2f} MB liberados")
    print()

    # ADVERTENCIA sobre PDFs
    if pdf_count > 0:
        print("=" * 70)
        print("⚠️  ADVERTENCIA: Se encontraron PDFs de facturas")
        print("=" * 70)
        print(f"Hay {pdf_count} archivos PDF en pdfs_temporales/")
        print()
        print("RECOMENDACIÓN: Copia estos PDFs a otra carpeta ANTES de continuar")
        print("               si quieres conservarlos como respaldo.")
        print()
        print("Ejemplo: Copia pdfs_temporales/ a C:\\Respaldos\\PDFs_facturas\\")
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

    total_eliminados = 0

    # Limpiar archivos_descargados
    print("1. Limpiando archivos_descargados/")
    eliminados = limpiar_carpeta("archivos_descargados", "Excel descargados")
    print(f"   ✅ {eliminados} archivos eliminados")
    total_eliminados += eliminados
    print()

    # Limpiar pdfs_temporales
    print("2. Limpiando pdfs_temporales/")
    eliminados = limpiar_carpeta("pdfs_temporales", "PDFs temporales")
    print(f"   ✅ {eliminados} archivos eliminados")
    total_eliminados += eliminados
    print()

    # Eliminar index.html
    print("3. Eliminando templates/index.html")
    if index_exists:
        try:
            os.remove("templates/index.html")
            print(f"   ✅ Archivo eliminado")
            total_eliminados += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print(f"   ⚠️  Archivo no existe")
    print()

    # Eliminar logs de Flask
    print("4. Eliminando logs de Flask")
    logs_eliminados = 0
    for log_file in ["flask_stderr.log", "flask_stdout.log", "debug.log"]:
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
                print(f"   ✅ {log_file} eliminado")
                logs_eliminados += 1
                total_eliminados += 1
            except Exception as e:
                print(f"   ❌ Error eliminando {log_file}: {e}")
    if logs_eliminados == 0:
        print(f"   ⚠️  No hay logs para eliminar")
    print()

    # Eliminar archivos de análisis temporal
    print("5. Eliminando archivos temporales de análisis")
    listas_eliminadas = 0
    for archivo in archivos_lista:
        if os.path.exists(archivo):
            try:
                os.remove(archivo)
                print(f"   ✅ {archivo} eliminado")
                listas_eliminadas += 1
                total_eliminados += 1
            except Exception as e:
                print(f"   ❌ Error eliminando {archivo}: {e}")
    if listas_eliminadas == 0:
        print(f"   ⚠️  No hay archivos temporales para eliminar")
    print()

    print("=" * 70)
    print("✅ LIMPIEZA COMPLETADA")
    print("=" * 70)
    print(f"Total de archivos eliminados: {total_eliminados}")
    print(f"Espacio liberado: {total_size:.2f} MB")
    print()
    print("NOTA: Las carpetas archivos_descargados/ y pdfs_temporales/ se")
    print("      volverán a llenar conforme el robot procese nuevos viajes.")
    print("      Los logs se regenerarán cuando Flask se ejecute nuevamente.")
    print("      Esto es normal y esperado.")
    print()

if __name__ == "__main__":
    main()
