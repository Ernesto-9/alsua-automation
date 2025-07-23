#!/usr/bin/env python3
"""
Handler MySQL para sincronización desde viajes_log.csv
Flujo: CSV → MySQL con INSERT directo a tabla prefacturarobot
"""

import mysql.connector
from mysql.connector import Error
import logging
import csv
import os
from datetime import datetime
from viajes_log import viajes_log

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MYSQL_CONFIG = {
    'host': '104.251.211.6',
    'port': 3306,
    'user': 'alsua',
    'password': '&/?37jejJdirbt782@28',
    'database': 'alsua',
    'autocommit': True,
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

class MySQLSyncFromCSV:
    def __init__(self, archivo_csv="viajes_log.csv"):
        self.connection = None
        self.archivo_csv = os.path.abspath(archivo_csv)
        self.archivo_procesados = "mysql_sync_procesados.txt"
        
    def conectar(self):
        try:
            if self.connection and self.connection.is_connected():
                return True
                
            logger.info("Conectando a MySQL...")
                
            self.connection = mysql.connector.connect(**MYSQL_CONFIG)
            
            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                logger.info("Conexión MySQL establecida")
                return True
            else:
                logger.error("No se pudo conectar a MySQL")
                return False
                
        except Error as e:
            logger.error(f"Error conectando a MySQL: {e}")
            self.connection = None
            return False
        except Exception as e:
            logger.error(f"Error general conectando a MySQL: {e}")
            self.connection = None
            return False
    
    def desconectar(self):
        try:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                logger.info("Conexión MySQL cerrada")
        except Exception as e:
            logger.warning(f"Error cerrando conexión MySQL: {e}")
    
    def cargar_registros_procesados(self):
        try:
            if os.path.exists(self.archivo_procesados):
                with open(self.archivo_procesados, 'r', encoding='utf-8') as f:
                    procesados = set(line.strip() for line in f.readlines())
                logger.info(f"Cargados {len(procesados)} registros procesados")
                return procesados
            else:
                logger.info("No hay archivo de procesados - primer sync")
                return set()
        except Exception as e:
            logger.warning(f"Error cargando procesados: {e}")
            return set()
    
    def marcar_como_procesado(self, registro_id):
        try:
            with open(self.archivo_procesados, 'a', encoding='utf-8') as f:
                f.write(f"{registro_id}\n")
        except Exception as e:
            logger.warning(f"Error marcando como procesado: {e}")
    
    def generar_id_registro(self, row):
        prefactura = row.get('prefactura', '')
        timestamp = row.get('timestamp', '')
        estatus = row.get('estatus', '')
        return f"{prefactura}_{timestamp}_{estatus}".replace(' ', '_').replace(':', '-')
    
    def leer_registros_nuevos_del_csv(self):
        try:
            if not os.path.exists(self.archivo_csv):
                logger.warning(f"Archivo CSV no existe: {self.archivo_csv}")
                return []
            
            procesados = self.cargar_registros_procesados()
            registros_nuevos = []
            total_registros = 0
            
            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    total_registros += 1
                    registro_id = self.generar_id_registro(row)
                    
                    if registro_id not in procesados:
                        registros_nuevos.append(row)
                        logger.info(f"Nuevo registro: {row['prefactura']} - {row['estatus']}")
            
            logger.info(f"CSV leído: {total_registros} total, {len(registros_nuevos)} nuevos")
            return registros_nuevos
            
        except Exception as e:
            logger.error(f"Error leyendo CSV: {e}")
            return []
    
    def procesar_registro_exitoso(self, registro):
        try:
            prefactura = registro.get('prefactura')
            uuid = registro.get('uuid')
            viajegm = registro.get('viajegm')
            
            if not prefactura:
                logger.error("Registro sin prefactura, saltando")
                return False
                
            cursor = self.connection.cursor()
            
            # INSERT directo a tabla prefacturarobot
            insert_query = """
                INSERT INTO prefacturarobot 
                (NOPREFACTURA, VIAJEGM, FACTURAGM, UUID, USUARIO, estatus) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            logger.info(f"Procesando viaje exitoso: {prefactura}")
            cursor.execute(insert_query, (prefactura, viajegm, '0', uuid, 'ROBOT', 'EXITOSO'))
            
            logger.info(f"Viaje EXITOSO creado: {prefactura}")
            logger.info(f"UUID: {uuid} - VIAJEGM: {viajegm}")
            
            cursor.close()
            return True
                
        except Error as e:
            logger.error(f"Error MySQL procesando exitoso: {e}")
            return False
        except Exception as e:
            logger.error(f"Error general procesando exitoso: {e}")
            return False
    
    def procesar_registro_fallido(self, registro):
        try:
            prefactura = registro.get('prefactura')
            motivo_fallo = registro.get('motivo_fallo')
            
            if not prefactura:
                logger.error("Registro sin prefactura, saltando")
                return False
                
            cursor = self.connection.cursor()
            
            # INSERT directo a tabla prefacturarobot
            insert_query = """
                INSERT INTO prefacturarobot 
                (NOPREFACTURA, VIAJEGM, FACTURAGM, UUID, USUARIO, erroresrobot, estatus) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            logger.info(f"Procesando viaje fallido: {prefactura}")
            cursor.execute(insert_query, (prefactura, '0', '0', '0', 'ROBOT', motivo_fallo, 'FALLIDO'))
            
            logger.info(f"Viaje FALLIDO creado: {prefactura}")
            logger.info(f"Error: {motivo_fallo}")
            
            cursor.close()
            return True
                
        except Error as e:
            logger.error(f"Error MySQL procesando fallido: {e}")
            return False
        except Exception as e:
            logger.error(f"Error general procesando fallido: {e}")
            return False
    
    def sincronizar_desde_csv(self):
        try:
            logger.info("Iniciando sincronización CSV → MySQL")
            
            if not os.path.exists(self.archivo_csv):
                logger.warning(f"CSV no existe: {self.archivo_csv}")
                return {'procesados': 0, 'exitosos': 0, 'fallidos': 0, 'errores': 0}
            
            if not self.conectar():
                logger.error("No se pudo conectar a MySQL")
                return {'procesados': 0, 'exitosos': 0, 'fallidos': 0, 'errores': 1}
            
            registros_nuevos = self.leer_registros_nuevos_del_csv()
            
            if not registros_nuevos:
                logger.info("No hay registros nuevos para sincronizar")
                return {'procesados': 0, 'exitosos': 0, 'fallidos': 0, 'errores': 0}
            
            estadisticas = {'procesados': 0, 'exitosos': 0, 'fallidos': 0, 'errores': 0}
            
            for registro in registros_nuevos:
                try:
                    estatus = registro.get('estatus', '').upper()
                    prefactura = registro.get('prefactura', 'DESCONOCIDA')
                    
                    if estatus == 'EXITOSO':
                        exito = self.procesar_registro_exitoso(registro)
                        if exito:
                            estadisticas['exitosos'] += 1
                        else:
                            estadisticas['errores'] += 1
                            
                    elif estatus == 'FALLIDO':
                        exito = self.procesar_registro_fallido(registro)
                        if exito:
                            estadisticas['fallidos'] += 1
                        else:
                            estadisticas['errores'] += 1
                    else:
                        logger.warning(f"Estatus desconocido '{estatus}' para prefactura {prefactura}")
                        estadisticas['errores'] += 1
                        continue
                    
                    registro_id = self.generar_id_registro(registro)
                    self.marcar_como_procesado(registro_id)
                    estadisticas['procesados'] += 1
                    
                except Exception as e:
                    logger.error(f"Error procesando registro {registro.get('prefactura', 'DESCONOCIDA')}: {e}")
                    estadisticas['errores'] += 1
            
            logger.info("Sincronización completada:")
            logger.info(f"  Procesados: {estadisticas['procesados']}")
            logger.info(f"  Exitosos: {estadisticas['exitosos']}")
            logger.info(f"  Fallidos: {estadisticas['fallidos']}")
            logger.info(f"  Errores: {estadisticas['errores']}")
            
            return estadisticas
            
        except Exception as e:
            logger.error(f"Error general en sincronización: {e}")
            return {'procesados': 0, 'exitosos': 0, 'fallidos': 0, 'errores': 1}
        finally:
            self.desconectar()
    
    def obtener_estadisticas_sync(self):
        try:
            stats = {
                'registros_procesados': 0,
                'archivo_csv_existe': os.path.exists(self.archivo_csv),
                'archivo_procesados_existe': os.path.exists(self.archivo_procesados),
                'ultimo_sync': 'Nunca'
            }
            
            if stats['archivo_procesados_existe']:
                with open(self.archivo_procesados, 'r', encoding='utf-8') as f:
                    stats['registros_procesados'] = len(f.readlines())
            
            if stats['archivo_procesados_existe']:
                timestamp = os.path.getmtime(self.archivo_procesados)
                stats['ultimo_sync'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}

mysql_sync = MySQLSyncFromCSV()

def sincronizar_csv_a_mysql():
    return mysql_sync.sincronizar_desde_csv()

def obtener_estadisticas_mysql_sync():
    return mysql_sync.obtener_estadisticas_sync()

def cerrar_conexion():
    mysql_sync.desconectar()

def registrar_viaje_exitoso(prefactura, fecha_viaje, uuid=None, viajegm=None, placa_tractor=None, placa_remolque=None):
    logger.warning("Usando función legacy - considera usar viajes_log directamente")
    from viajes_log import registrar_viaje_exitoso as log_exitoso
    return log_exitoso(prefactura, None, fecha_viaje, placa_tractor, placa_remolque, uuid, viajegm)

def registrar_viaje_fallido(prefactura, fecha_viaje, motivo_fallo, placa_tractor=None, placa_remolque=None):
    logger.warning("Usando función legacy - considera usar viajes_log directamente")
    from viajes_log import registrar_viaje_fallido as log_fallido
    return log_fallido(prefactura, motivo_fallo, None, fecha_viaje, placa_tractor, placa_remolque)

if __name__ == "__main__":
    print("Probando sincronización CSV → MySQL con tabla prefacturarobot...")
    
    print("\nEstadísticas actuales:")
    stats = obtener_estadisticas_mysql_sync()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\nEjecutando sincronización...")
    resultado = sincronizar_csv_a_mysql()
    
    print("\nResultado de sincronización:")
    for key, value in resultado.items():
        print(f"   {key}: {value}")
    
    print("\nPrueba completada")