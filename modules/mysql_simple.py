#!/usr/bin/env python3
"""
Handler MySQL simplificado - solo registra viajes exitosos y fallidos
"""

import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MySQLSimple:
    def __init__(self):
        self.connection = None
        
    def conectar(self):
        """Establecer conexión con MySQL"""
        try:
            if self.connection and self.connection.is_connected():
                return True
                
            self.connection = mysql.connector.connect(
                host=MYSQL_HOST,
                database=MYSQL_DATABASE,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                autocommit=True
            )
            
            if self.connection.is_connected():
                logger.info("✅ Conexión MySQL establecida")
                return True
            else:
                logger.error("❌ No se pudo establecer conexión MySQL")
                return False
                
        except Error as e:
            logger.error(f"❌ Error conectando a MySQL: {e}")
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
    
    def registrar_viaje_exitoso(self, prefactura, fecha_viaje):
        """Registra un viaje exitoso"""
        return self._registrar_viaje(prefactura, fecha_viaje, 'EXITOSO', None)
    
    def registrar_viaje_fallido(self, prefactura, fecha_viaje, motivo_fallo):
        """Registra un viaje fallido"""
        return self._registrar_viaje(prefactura, fecha_viaje, 'FALLO', motivo_fallo)
    
    def _registrar_viaje(self, prefactura, fecha_viaje, estatus, notas):
        """Registra un viaje en la base de datos"""
        try:
            if not self.conectar():
                logger.warning("⚠️ No se pudo conectar a MySQL - guardando en archivo")
                self._guardar_fallback(prefactura, fecha_viaje, estatus, notas)
                return False
            
            cursor = self.connection.cursor()
            
            # Convertir fecha al formato correcto
            fecha_procesada = self._procesar_fecha(fecha_viaje)
            
            query = """
                INSERT INTO viajes_alsua 
                (prefactura, fecha_viaje, estatus, notas)
                VALUES (%s, %s, %s, %s)
            """
            
            valores = (prefactura, fecha_procesada, estatus, notas)
            cursor.execute(query, valores)
            
            logger.info(f"✅ Viaje registrado en MySQL:")
            logger.info(f"   📋 Prefactura: {prefactura}")
            logger.info(f"   📅 Fecha: {fecha_procesada}")
            logger.info(f"   📊 Estatus: {estatus}")
            if notas:
                logger.info(f"   📝 Notas: {notas}")
            
            cursor.close()
            return True
            
        except Error as e:
            logger.error(f"❌ Error MySQL: {e}")
            self._guardar_fallback(prefactura, fecha_viaje, estatus, notas)
            return False
        except Exception as e:
            logger.error(f"❌ Error general: {e}")
            self._guardar_fallback(prefactura, fecha_viaje, estatus, notas)
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
    
    def _guardar_fallback(self, prefactura, fecha_viaje, estatus, notas):
        """Guarda en archivo si MySQL no está disponible"""
        try:
            archivo_fallback = "viajes_fallback.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(archivo_fallback, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp}|{prefactura}|{fecha_viaje}|{estatus}|{notas or ''}\n")
                
            logger.warning(f"⚠️ Viaje guardado en archivo fallback: {archivo_fallback}")
            
        except Exception as e:
            logger.error(f"❌ Error crítico guardando fallback: {e}")

# Instancia global
mysql_simple = MySQLSimple()

# Funciones de conveniencia
def registrar_viaje_exitoso(prefactura, fecha_viaje):
    """Registra un viaje exitoso"""
    return mysql_simple.registrar_viaje_exitoso(prefactura, fecha_viaje)

def registrar_viaje_fallido(prefactura, fecha_viaje, motivo_fallo):
    """Registra un viaje fallido"""
    return mysql_simple.registrar_viaje_fallido(prefactura, fecha_viaje, motivo_fallo)

def cerrar_conexion():
    """Cierra la conexión MySQL"""
    mysql_simple.desconectar()

# Ejemplo de uso
if __name__ == "__main__":
    # Probar conexión y registro
    print("Probando conexión y registro...")
    
    # Viaje exitoso
    exito1 = registrar_viaje_exitoso("7996845", "08/07/2025")
    print(f"Viaje exitoso: {'✅' if exito1 else '❌'}")
    
    # Viaje fallido
    exito2 = registrar_viaje_fallido("7996846", "08/07/2025", "Operador ocupado - BTN_OK detectado")
    print(f"Viaje fallido: {'✅' if exito2 else '❌'}")
    
    # Cerrar conexión
    cerrar_conexion()