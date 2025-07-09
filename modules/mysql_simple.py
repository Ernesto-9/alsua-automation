#!/usr/bin/env python3
"""
Handler MySQL con conexión real a la base de datos de la empresa
Registra viajes en tabla acumuladoprefactura
"""

import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime

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

class MySQLAcumuladoPrefactura:
    def __init__(self):
        self.connection = None
        
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
    
    def verificar_tabla(self):
        """Verifica que la tabla acumuladoprefactura existe y muestra su estructura"""
        try:
            if not self.conectar():
                return False
                
            cursor = self.connection.cursor()
            
            # Verificar que la tabla existe
            cursor.execute("SHOW TABLES LIKE 'acumuladoprefactura'")
            resultado = cursor.fetchone()
            
            if not resultado:
                logger.error("❌ Tabla 'acumuladoprefactura' no encontrada")
                cursor.close()
                return False
            
            # Mostrar estructura de la tabla
            cursor.execute("DESCRIBE acumuladoprefactura")
            columnas = cursor.fetchall()
            
            logger.info("📊 Estructura de la tabla 'acumuladoprefactura':")
            for columna in columnas:
                field, type_, null, key, default, extra = columna
                logger.info(f"   - {field}: {type_} (NULL: {null}, Key: {key})")
            
            cursor.close()
            return True
            
        except Error as e:
            logger.error(f"❌ Error verificando tabla: {e}")
            return False
    
    def registrar_viaje_exitoso(self, prefactura, fecha_viaje, uuide=None, viajegm=None):
        """Registra un viaje exitoso en la tabla"""
        return self._registrar_viaje(
            prefactura=prefactura,
            fecha_viaje=fecha_viaje,
            estatus='EXITOSO',
            anotaciones=None,
            uuide=uuide,
            viajegm=viajegm
        )
    
    def registrar_viaje_fallido(self, prefactura, fecha_viaje, motivo_fallo):
        """Registra un viaje fallido en la tabla"""
        return self._registrar_viaje(
            prefactura=prefactura,
            fecha_viaje=fecha_viaje,
            estatus='FALLIDO',
            anotaciones=motivo_fallo,
            uuide=None,
            viajegm=None
        )
    
    def _registrar_viaje(self, prefactura, fecha_viaje, estatus, anotaciones, uuide=None, viajegm=None):
        """Registra un viaje en la base de datos"""
        try:
            if not self.conectar():
                logger.warning("⚠️ No se pudo conectar a MySQL - guardando en archivo")
                self._guardar_fallback(prefactura, fecha_viaje, estatus, anotaciones, uuide, viajegm)
                return False
            
            cursor = self.connection.cursor()
            
            # Convertir fecha al formato correcto
            fecha_procesada = self._procesar_fecha(fecha_viaje)
            
            # Query INSERT
            query = """
                INSERT INTO acumuladoprefactura 
                (UUIDE, VIAJEGM, prefactura, fecha, estatus, anotaciones)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            valores = (uuide, viajegm, prefactura, fecha_procesada, estatus, anotaciones)
            cursor.execute(query, valores)
            
            logger.info(f"✅ Viaje registrado en MySQL:")
            logger.info(f"   📋 Prefactura: {prefactura}")
            logger.info(f"   📅 Fecha: {fecha_procesada}")
            logger.info(f"   📊 Estatus: {estatus}")
            if uuide:
                logger.info(f"   🆔 UUIDE: {uuide}")
            if viajegm:
                logger.info(f"   🚛 VIAJEGM: {viajegm}")
            if anotaciones:
                logger.info(f"   📝 Anotaciones: {anotaciones}")
            
            cursor.close()
            return True
            
        except Error as e:
            logger.error(f"❌ Error MySQL: {e}")
            logger.error(f"   Error Code: {e.errno}")
            self._guardar_fallback(prefactura, fecha_viaje, estatus, anotaciones, uuide, viajegm)
            return False
        except Exception as e:
            logger.error(f"❌ Error general: {e}")
            self._guardar_fallback(prefactura, fecha_viaje, estatus, anotaciones, uuide, viajegm)
            return False
    
    def _procesar_fecha(self, fecha_str):
        """Convierte fecha de DD/MM/YYYY a YYYY-MM-DD"""
        try:
            if '/' in fecha_str:
                # Formato DD/MM/YYYY
                dia, mes, año = fecha_str.split('/')
                return f"{año}-{mes.zfill(2)}-{dia.zfill(2)}"
            else:
                # Asumir que ya está en formato correcto
                return fecha_str
        except Exception as e:
            logger.warning(f"⚠️ Error procesando fecha {fecha_str}: {e}")
            # Usar fecha actual como fallback
            return datetime.now().strftime('%Y-%m-%d')
    
    def _guardar_fallback(self, prefactura, fecha_viaje, estatus, anotaciones, uuide, viajegm):
        """Guarda en archivo si MySQL no está disponible"""
        try:
            archivo_fallback = "viajes_fallback.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(archivo_fallback, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp}|{prefactura}|{fecha_viaje}|{estatus}|{anotaciones or ''}|{uuide or ''}|{viajegm or ''}\n")
                
            logger.warning(f"⚠️ Viaje guardado en archivo fallback: {archivo_fallback}")
            
        except Exception as e:
            logger.error(f"❌ Error crítico guardando fallback: {e}")
    
    def probar_conexion(self):
        """Prueba la conexión y muestra información de la base de datos"""
        logger.info("🧪 Probando conexión a MySQL...")
        
        if self.conectar():
            logger.info("✅ Conexión exitosa")
            
            # Verificar tabla
            if self.verificar_tabla():
                logger.info("✅ Tabla 'acumuladoprefactura' verificada")
                
                # Probar un INSERT de prueba (comentado por seguridad)
                logger.info("💡 Conexión lista para usar en producción")
                return True
            else:
                logger.error("❌ Problema con la tabla")
                return False
        else:
            logger.error("❌ Falló la conexión")
            return False

# Instancia global
mysql_acumulado = MySQLAcumuladoPrefactura()

# Funciones de conveniencia (compatibilidad con código existente)
def registrar_viaje_exitoso(prefactura, fecha_viaje, uuide=None, viajegm=None):
    """Registra un viaje exitoso"""
    return mysql_acumulado.registrar_viaje_exitoso(prefactura, fecha_viaje, uuide, viajegm)

def registrar_viaje_fallido(prefactura, fecha_viaje, motivo_fallo):
    """Registra un viaje fallido"""
    return mysql_acumulado.registrar_viaje_fallido(prefactura, fecha_viaje, motivo_fallo)

def cerrar_conexion():
    """Cierra la conexión MySQL"""
    mysql_acumulado.desconectar()

# Script de prueba
if __name__ == "__main__":
    print("🧪 Probando conexión a MySQL...")
    
    # Probar conexión
    exito_conexion = mysql_acumulado.probar_conexion()
    
    if exito_conexion:
        print("\n🧪 Probando registros de ejemplo...")
        
        # Ejemplo viaje exitoso
        exito1 = registrar_viaje_exitoso("7996845", "08/07/2025", "UUID123", "GM456")
        print(f"Viaje exitoso: {'✅' if exito1 else '❌'}")
        
        # Ejemplo viaje fallido
        exito2 = registrar_viaje_fallido("7996846", "08/07/2025", "Operador ocupado")
        print(f"Viaje fallido: {'✅' if exito2 else '❌'}")
    
    # Cerrar conexión
    cerrar_conexion()
    print("👋 Prueba completada")