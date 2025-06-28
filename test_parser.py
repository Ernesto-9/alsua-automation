from modules.parser import parse_xls

ruta = "archivos_descargados/NWM9709244W4_7866919.xls"
datos = parse_xls(ruta, determinante_from_asunto="8080")

print("Resultado:")
print(datos)
