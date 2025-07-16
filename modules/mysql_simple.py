#!/usr/bin/env python3
"""
Handler MySQL MODIFICADO para leer desde viajes_log.csv
NUEVO FLUJO: CSV → MySQL (fuente única de verdad es el CSV)
LIMPIO: Sin archivos de fallback - todo va al CSV unificado
ACTUALIZADO: Campos completos UUID, VIAJEGM, erroresrobot, estatusr, USUARIO
"""

import mysql.connector
from mysql.connector import Error
import logging
import csv
import os
from datetime import datetime
from viajes_log import viajes_log

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# DATOS REALES DE CONEXIÓN
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
        """
        Inicializa el sincronizador MySQL que lee desde CSV
        
        Args:
            archivo_csv: Archivo CSV fuente de datos
        """
        self.connection = None
        self.archivo_csv = os.path.abspath(archivo_csv)
        self.archivo_procesados = "mysql_sync_procesados.txt"  # Archivo para trackear qué se procesó
        
    def conectar(self):
        """Establecer conexión con MySQL"""
        try:
            if self.connection and self.connection.is_connected():
                return True
                
            logger.info("🔌 Conectando a MySQL...")
            logger.info(f"   Host: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
            logger.info(f"   Base de datos: {MYSQL_CONFIG['database']}")
            logger.info(f"   Usuario: {MYSQL_CONFIG['user']}")
                
            self.connection = mysql.connector.connect(**MYSQL_CONFIG)
            
            if self.connection.is_connected():
                # Obtener info del servidor
                db_info = self.connection.get_server_info()
                logger.info(f"✅ Conexión MySQL establecida exitosamente")
                logger.info(f"   Versión del servidor: {db_info}")
                return True
            else:
                logger.error("❌ No se pudo establecer conexión MySQL")
                return False
                
        except Error as e:
            logger.error(f"❌ Error conectando a MySQL: {e}")
            logger.error(f"   Error Code: {e.errno}")
            logger.error(f"   SQLSTATE: {e.sqlstate}")
            self.connection = None
            return False
        except Exception as e:
            logger.error(f"❌ Error general conectando a MySQL: {e}")
            self.connection = None
            return False
    
    def desconectar(self):
        """Cerrar conexión MySQL"""
        try:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                logger.info("✅ Conexión MySQL cerrada")
        except Exception as e:
            logger.warning(f"⚠️ Error cerrando conexión MySQL: {e}")
    
    def cargar_registros_procesados(self):
        """Carga la lista de registros ya procesados en MySQL"""
        try:
            if os.path.exists(self.archivo_procesados):
                with open(self.archivo_procesados, 'r', encoding='utf-8') as f:
                    procesados = set(line.strip() for line in f.readlines())
                logger.info(f"📁 Cargados {len(procesados)} registros ya procesados")
                return procesados
            else:
                logger.info("📁 No hay archivo de procesados - primer sync")
                return set()
        except Exception as e:
            logger.warning(f"⚠️ Error cargando procesados: {e}")
            return set()
    
    def marcar_como_procesado(self, registro_id):
        """Marca un registro como ya procesado en MySQL"""
        try:
            with open(self.archivo_procesados, 'a', encoding='utf-8') as f:
                f.write(f"{registro_id}\n")
        except Exception as e:
            logger.warning(f"⚠️ Error marcando como procesado: {e}")
    
    def generar_id_registro(self, row):
        """Genera un ID único para cada registro del CSV"""
        # Combinar campos únicos para crear ID
        prefactura = row.get('prefactura', '')
        timestamp = row.get('timestamp', '')
        estatus = row.get('estatus', '')
        return f"{prefactura}_{timestamp}_{estatus}".replace(' ', '_').replace(':', '-')
    
    def leer_registros_nuevos_del_csv(self):
        """
        Lee el CSV y retorna solo los registros que NO han sido procesados aún
        
        Returns:
            List[Dict]: Lista de registros nuevos
        """
        try:
            if not os.path.exists(self.archivo_csv):
                logger.warning(f"⚠️ Archivo CSV no existe: {self.archivo_csv}")
                return []
            
            # Cargar registros ya procesados
            procesados = self.cargar_registros_procesados()
            
            # Leer CSV completo
            registros_nuevos = []
            total_registros = 0
            
            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    total_registros += 1
                    registro_id = self.generar_id_registro(row)
                    
                    if registro_id not in procesados:
                        registros_nuevos.append(row)
                        logger.info(f"📋 Nuevo registro: {row['prefactura']} - {row['estatus']}")
            
            logger.info(f"📊 CSV leído: {total_registros} total, {len(registros_nuevos)} nuevos")
            return registros_nuevos
            
        except Exception as e:
            logger.error(f"❌ Error leyendo CSV: {e}")
            return []
    
    def verificar_prefactura_existe(self, prefactura):
        """Verifica si una prefactura ya existe en la base de datos"""
        try:
            if not self.conectar():
                return False
                
            cursor = self.connection.cursor()
            
            query = "SELECT COUNT(*) FROM acumuladoprefactura WHERE NOPREFACTURA = %s"
            cursor.execute(query, (prefactura,))
            
            resultado = cursor.fetchone()
            existe = resultado[0] > 0
            
            cursor.close()
            
            if existe:
                logger.info(f"✅ Prefactura {prefactura} EXISTE en base de datos")
            else:
                logger.warning(f"⚠️ Prefactura {prefactura} NO EXISTE en base de datos")
                
            return existe
            
        except Error as e:
            logger.error(f"❌ Error verificando prefactura: {e}")
            return False
    
    def procesar_registro_exitoso(self, registro):
        """
        Procesa un registro EXITOSO del CSV hacia MySQL
        ACTUALIZADO: Incluye UUID, VIAJEGM, estatusr, USUARIO
        
        Args:
            registro: Dict con datos del registro CSV
            
        Returns:
            bool: True si se procesó correctamente
        """
        try:
            prefactura = registro.get('prefactura')
            uuid = registro.get('uuid')
            viajegm = registro.get('viajegm')
            
            if not prefactura:
                logger.error("❌ Registro sin prefactura, saltando")
                return False
            
            # Verificar que la prefactura existe en la BD
            if not self.verificar_prefactura_existe(prefactura):
                logger.warning(f"⚠️ Prefactura {prefactura} no existe en BD - no se puede actualizar")
                logger.warning(f"💡 Considera agregar prefactura {prefactura} manualmente a la BD")
                return False
            
            cursor = self.connection.cursor()
            
            # Query UPDATE para completar TODOS los datos de viaje exitoso
            query = """
                UPDATE acumuladoprefactura 
                SET UUID = %s, VIAJEGM = %s, estatusr = %s, USUARIO = %s
                WHERE NOPREFACTURA = %s
            """
            
            valores = (uuid, viajegm, 'EXITOSO', 'ROBOT', prefactura)
            
            logger.info(f"🔄 Ejecutando query para viaje EXITOSO:")
            logger.info(f"   📋 NOPREFACTURA: {prefactura}")
            logger.info(f"   🆔 UUID: {uuid}")
            logger.info(f"   🚛 VIAJEGM: {viajegm}")
            logger.info(f"   📊 estatusr: EXITOSO")
            logger.info(f"   👤 USUARIO: ROBOT")
            
            cursor.execute(query, valores)
            filas_afectadas = cursor.rowcount
            
            if filas_afectadas > 0:
                logger.info(f"✅ Viaje EXITOSO sincronizado completamente en MySQL:")
                logger.info(f"   📋 NOPREFACTURA: {prefactura}")
                logger.info(f"   🆔 UUID: {uuid}")
                logger.info(f"   🚛 VIAJEGM: {viajegm}")
                logger.info(f"   📊 estatusr: EXITOSO")
                logger.info(f"   👤 USUARIO: ROBOT")
                
                # Actualizar placas si están disponibles
                placa_tractor = registro.get('placa_tractor')
                placa_remolque = registro.get('placa_remolque')
                if placa_tractor or placa_remolque:
                    self._actualizar_placas(cursor, prefactura, placa_tractor, placa_remolque)
                
                cursor.close()
                return True
            else:
                logger.error(f"❌ No se actualizó ninguna fila para prefactura: {prefactura}")
                cursor.close()
                return False
                
        except Error as e:
            logger.error(f"❌ Error MySQL procesando exitoso: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error general procesando exitoso: {e}")
            return False
    
    def procesar_registro_fallido(self, registro):
        """
        Procesa un registro FALLIDO del CSV hacia MySQL
        ACTUALIZADO: Incluye erroresrobot, estatusr, USUARIO
        
        Args:
            registro: Dict con datos del registro CSV
            
        Returns:
            bool: True si se procesó correctamente
        """
        try:
            prefactura = registro.get('prefactura')
            motivo_fallo = registro.get('motivo_fallo')
            
            if not prefactura:
                logger.error("❌ Registro sin prefactura, saltando")
                return False
            
            # Verificar que la prefactura existe en la BD
            if not self.verificar_prefactura_existe(prefactura):
                logger.warning(f"⚠️ Prefactura {prefactura} no existe en BD")
                logger.warning(f"💡 Considera agregar prefactura {prefactura} manualmente a la BD")
                return False
            
            cursor = self.connection.cursor()
            
            # Query UPDATE para marcar como fallido con TODOS los campos requeridos
            query = """
                UPDATE acumuladoprefactura 
                SET erroresrobot = %s, estatusr = %s, USUARIO = %s
                WHERE NOPREFACTURA = %s
            """
            
            valores = (motivo_fallo, 'FALLIDO', 'ROBOT', prefactura)
            
            logger.info(f"🔄 Ejecutando query para viaje FALLIDO:")
            logger.info(f"   📋 NOPREFACTURA: {prefactura}")
            logger.info(f"   🤖 erroresrobot: {motivo_fallo}")
            logger.info(f"   📊 estatusr: FALLIDO")
            logger.info(f"   👤 USUARIO: ROBOT")
            
            cursor.execute(query, valores)
            filas_afectadas = cursor.rowcount
            
            if filas_afectadas > 0:
                logger.info(f"✅ Viaje FALLIDO sincronizado completamente en MySQL:")
                logger.info(f"   📋 NOPREFACTURA: {prefactura}")
                logger.info(f"   🤖 erroresrobot: {motivo_fallo}")
                logger.info(f"   📊 estatusr: FALLIDO")
                logger.info(f"   👤 USUARIO: ROBOT")
                
                # Actualizar placas si están disponibles
                placa_tractor = registro.get('placa_tractor')
                placa_remolque = registro.get('placa_remolque')
                if placa_tractor or placa_remolque:
                    self._actualizar_placas(cursor, prefactura, placa_tractor, placa_remolque)
                
                cursor.close()
                return True
            else:
                logger.error(f"❌ No se actualizó ninguna fila para prefactura: {prefactura}")
                cursor.close()
                return False
                
        except Error as e:
            logger.error(f"❌ Error MySQL procesando fallido: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error general procesando fallido: {e}")
            return False
    
    def _actualizar_placas(self, cursor, prefactura, placa_tractor, placa_remolque):
        """Función auxiliar para actualizar placas"""
        try:
            if placa_tractor or placa_remolque:
                campos = []
                valores = []
                
                if placa_tractor:
                    campos.append("PLACATRACTOR = %s")
                    valores.append(placa_tractor)
                    
                if placa_remolque:
                    campos.append("PLACAREMOLQUE = %s")
                    valores.append(placa_remolque)
                
                if campos:
                    query = f"UPDATE acumuladoprefactura SET {', '.join(campos)} WHERE NOPREFACTURA = %s"
                    valores.append(prefactura)
                    
                    cursor.execute(query, valores)
                    logger.info(f"✅ Placas actualizadas: Tractor={placa_tractor}, Remolque={placa_remolque}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Error actualizando placas: {e}")
    
    def sincronizar_desde_csv(self):
        """
        FUNCIÓN PRINCIPAL: Sincroniza todos los registros nuevos del CSV hacia MySQL
        
        Returns:
            Dict: Estadísticas de la sincronización
        """
        try:
            logger.info("🔄 Iniciando sincronización CSV → MySQL")
            
            # Verificar que el CSV existe
            if not os.path.exists(self.archivo_csv):
                logger.warning(f"⚠️ CSV no existe: {self.archivo_csv}")
                return {'procesados': 0, 'exitosos': 0, 'fallidos': 0, 'errores': 0}
            
            # Intentar conectar a MySQL
            if not self.conectar():
                logger.error("❌ No se pudo conectar a MySQL - sincronización cancelada")
                return {'procesados': 0, 'exitosos': 0, 'fallidos': 0, 'errores': 1}
            
            # Leer registros nuevos del CSV
            registros_nuevos = self.leer_registros_nuevos_del_csv()
            
            if not registros_nuevos:
                logger.info("ℹ️ No hay registros nuevos para sincronizar")
                return {'procesados': 0, 'exitosos': 0, 'fallidos': 0, 'errores': 0}
            
            # Procesar cada registro
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
                        logger.warning(f"⚠️ Estatus desconocido '{estatus}' para prefactura {prefactura}")
                        estadisticas['errores'] += 1
                        continue
                    
                    # Marcar como procesado (incluso si falló, para evitar reintentarlo)
                    registro_id = self.generar_id_registro(registro)
                    self.marcar_como_procesado(registro_id)
                    estadisticas['procesados'] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error procesando registro {registro.get('prefactura', 'DESCONOCIDA')}: {e}")
                    estadisticas['errores'] += 1
            
            # Log final de estadísticas
            logger.info("📊 SINCRONIZACIÓN COMPLETADA:")
            logger.info(f"   📋 Registros procesados: {estadisticas['procesados']}")
            logger.info(f"   ✅ Exitosos sincronizados: {estadisticas['exitosos']}")
            logger.info(f"   ❌ Fallidos sincronizados: {estadisticas['fallidos']}")
            logger.info(f"   🚨 Errores: {estadisticas['errores']}")
            
            return estadisticas
            
        except Exception as e:
            logger.error(f"❌ Error general en sincronización: {e}")
            return {'procesados': 0, 'exitosos': 0, 'fallidos': 0, 'errores': 1}
        finally:
            self.desconectar()
    
    def obtener_estadisticas_sync(self):
        """Obtiene estadísticas de sincronización"""
        try:
            stats = {
                'registros_procesados': 0,
                'archivo_csv_existe': os.path.exists(self.archivo_csv),
                'archivo_procesados_existe': os.path.exists(self.archivo_procesados),
                'ultimo_sync': 'Nunca'
            }
            
            # Contar registros procesados
            if stats['archivo_procesados_existe']:
                with open(self.archivo_procesados, 'r', encoding='utf-8') as f:
                    stats['registros_procesados'] = len(f.readlines())
            
            # Último sync (fecha de modificación del archivo procesados)
            if stats['archivo_procesados_existe']:
                timestamp = os.path.getmtime(self.archivo_procesados)
                stats['ultimo_sync'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {'error': str(e)}

# Instancia global
mysql_sync = MySQLSyncFromCSV()

# Funciones de conveniencia (NUEVAS - reemplazan las antiguas)
def sincronizar_csv_a_mysql():
    """Función principal para sincronizar CSV a MySQL"""
    return mysql_sync.sincronizar_desde_csv()

def obtener_estadisticas_mysql_sync():
    """Obtiene estadísticas de sincronización"""
    return mysql_sync.obtener_estadisticas_sync()

def cerrar_conexion():
    """Cierra la conexión MySQL"""
    mysql_sync.desconectar()

# FUNCIONES LEGACY (para compatibilidad temporal)
def registrar_viaje_exitoso(prefactura, fecha_viaje, uuid=None, viajegm=None, placa_tractor=None, placa_remolque=None):
    """FUNCIÓN LEGACY: Ahora redirige al sistema CSV"""
    logger.warning("⚠️ Usando función legacy - considera usar viajes_log directamente")
    from viajes_log import registrar_viaje_exitoso as log_exitoso
    return log_exitoso(prefactura, None, fecha_viaje, placa_tractor, placa_remolque, uuid, viajegm)

def registrar_viaje_fallido(prefactura, fecha_viaje, motivo_fallo, placa_tractor=None, placa_remolque=None):
    """FUNCIÓN LEGACY: Ahora redirige al sistema CSV"""
    logger.warning("⚠️ Usando función legacy - considera usar viajes_log directamente")
    from viajes_log import registrar_viaje_fallido as log_fallido
    return log_fallido(prefactura, motivo_fallo, None, fecha_viaje, placa_tractor, placa_remolque)

# Script de prueba
if __name__ == "__main__":
    print("🧪 Probando sincronización CSV → MySQL con campos completos...")
    
    # Mostrar estadísticas actuales
    print("\n📊 Estadísticas actuales:")
    stats = obtener_estadisticas_mysql_sync()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Ejecutar sincronización
    print("\n🔄 Ejecutando sincronización...")
    resultado = sincronizar_csv_a_mysql()
    
    print("\n📋 Resultado de sincronización:")
    for key, value in resultado.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Prueba completada")
    print("🔍 Verificar MySQL: UUID, VIAJEGM, erroresrobot, estatusr, USUARIO")