#!/usr/bin/env python3
"""
Handler MySQL con conexión real a la base de datos de la empresa
MODIFICADO: Actualiza registros existentes en lugar de crear nuevos
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
    
    def verificar_prefactura_existe(self, prefactura):
        """
        NUEVA FUNCIÓN: Verifica si una prefactura ya existe en la base de datos
        
        Args:
            prefactura: Número de prefactura a verificar
            
        Returns:
            bool: True si existe, False si no existe
        """
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
    
    def registrar_viaje_exitoso(self, prefactura, fecha_viaje, uuid=None, viajegm=None, placa_tractor=None, placa_remolque=None):
        """
        FUNCIÓN MODIFICADA: Actualiza registro existente con UUID y VIAJEGM
        
        Args:
            prefactura: Número de prefactura (debe existir)
            fecha_viaje: Fecha del viaje
            uuid: UUID extraído del PDF
            viajegm: Código del viaje en GM
            placa_tractor: Placa del tractor (opcional)
            placa_remolque: Placa del remolque (opcional)
            
        Returns:
            bool: True si se actualizó correctamente
        """
        return self._actualizar_viaje_exitoso(
            prefactura=prefactura,
            fecha_viaje=fecha_viaje,
            uuid=uuid,
            viajegm=viajegm,
            placa_tractor=placa_tractor,
            placa_remolque=placa_remolque
        )
    
    def registrar_viaje_fallido(self, prefactura, fecha_viaje, motivo_fallo, placa_tractor=None, placa_remolque=None):
        """
        FUNCIÓN MODIFICADA: Actualiza registro existente marcándolo como fallido
        
        Args:
            prefactura: Número de prefactura (debe existir)
            fecha_viaje: Fecha del viaje
            motivo_fallo: Razón del fallo
            placa_tractor: Placa del tractor (opcional)
            placa_remolque: Placa del remolque (opcional)
            
        Returns:
            bool: True si se actualizó correctamente
        """
        return self._actualizar_viaje_fallido(
            prefactura=prefactura,
            fecha_viaje=fecha_viaje,
            motivo_fallo=motivo_fallo,
            placa_tractor=placa_tractor,
            placa_remolque=placa_remolque
        )
    
    def _actualizar_viaje_exitoso(self, prefactura, fecha_viaje, uuid, viajegm, placa_tractor=None, placa_remolque=None):
        """
        NUEVA FUNCIÓN: Actualiza registro existente con datos de viaje exitoso
        """
        try:
            if not self.conectar():
                logger.warning("⚠️ No se pudo conectar a MySQL - guardando en archivo")
                self._guardar_fallback(prefactura, fecha_viaje, "EXITOSO", None, uuid, viajegm, placa_tractor, placa_remolque)
                return False
            
            # Verificar que la prefactura existe
            if not self.verificar_prefactura_existe(prefactura):
                logger.error(f"❌ No se puede actualizar: Prefactura {prefactura} no existe en base de datos")
                logger.error("💡 La empresa debe crear primero el registro de la prefactura")
                return False
            
            cursor = self.connection.cursor()
            
            # Query UPDATE para completar los datos faltantes
            query = """
                UPDATE acumuladoprefactura 
                SET UUID = %s, VIAJEGM = %s, estatus = 'EXITOSO'
                WHERE NOPREFACTURA = %s
            """
            
            valores = (uuid, viajegm, prefactura)
            cursor.execute(query, valores)
            
            # Verificar cuántas filas se actualizaron
            filas_afectadas = cursor.rowcount
            
            if filas_afectadas > 0:
                logger.info(f"✅ Viaje EXITOSO actualizado en MySQL:")
                logger.info(f"   📋 NOPREFACTURA: {prefactura}")
                logger.info(f"   🆔 UUID: {uuid}")
                logger.info(f"   🚛 VIAJEGM: {viajegm}")
                logger.info(f"   📊 estatus: EXITOSO")
                logger.info(f"   ✅ Filas actualizadas: {filas_afectadas}")
                
                # Si tenemos placas, actualizar también esos campos
                if placa_tractor or placa_remolque:
                    self._actualizar_placas(cursor, prefactura, placa_tractor, placa_remolque)
                
                cursor.close()
                return True
            else:
                logger.error(f"❌ No se actualizó ninguna fila para prefactura: {prefactura}")
                cursor.close()
                return False
            
        except Error as e:
            logger.error(f"❌ Error MySQL: {e}")
            logger.error(f"   Error Code: {e.errno}")
            self._guardar_fallback(prefactura, fecha_viaje, "EXITOSO", None, uuid, viajegm, placa_tractor, placa_remolque)
            return False
        except Exception as e:
            logger.error(f"❌ Error general: {e}")
            self._guardar_fallback(prefactura, fecha_viaje, "EXITOSO", None, uuid, viajegm, placa_tractor, placa_remolque)
            return False
    
    def _actualizar_viaje_fallido(self, prefactura, fecha_viaje, motivo_fallo, placa_tractor=None, placa_remolque=None):
        """
        NUEVA FUNCIÓN: Actualiza registro existente marcándolo como fallido
        """
        try:
            if not self.conectar():
                logger.warning("⚠️ No se pudo conectar a MySQL - guardando en archivo")
                self._guardar_fallback(prefactura, fecha_viaje, "FALLIDO", motivo_fallo, None, None, placa_tractor, placa_remolque)
                return False
            
            # Verificar que la prefactura existe
            if not self.verificar_prefactura_existe(prefactura):
                logger.warning(f"⚠️ Prefactura {prefactura} no existe - guardando en archivo fallback")
                self._guardar_fallback(prefactura, fecha_viaje, "FALLIDO", motivo_fallo, None, None, placa_tractor, placa_remolque)
                return False
            
            cursor = self.connection.cursor()
            
            # Query UPDATE para marcar como fallido Y registrar el error
            query = """
                UPDATE acumuladoprefactura 
                SET estatus = 'FALLIDO', erroresrobot = %s
                WHERE NOPREFACTURA = %s
            """
            
            cursor.execute(query, (motivo_fallo, prefactura))
            
            # Verificar cuántas filas se actualizaron
            filas_afectadas = cursor.rowcount
            
            if filas_afectadas > 0:
                logger.info(f"✅ Viaje FALLIDO actualizado en MySQL:")
                logger.info(f"   📋 NOPREFACTURA: {prefactura}")
                logger.info(f"   📊 estatus: FALLIDO")
                logger.info(f"   🤖 erroresrobot: {motivo_fallo}")
                logger.info(f"   ✅ Filas actualizadas: {filas_afectadas}")
                
                # Si tenemos placas, actualizar también esos campos
                if placa_tractor or placa_remolque:
                    self._actualizar_placas(cursor, prefactura, placa_tractor, placa_remolque)
                
                cursor.close()
                return True
            else:
                logger.error(f"❌ No se actualizó ninguna fila para prefactura: {prefactura}")
                cursor.close()
                return False
                
        except Error as e:
            logger.error(f"❌ Error MySQL: {e}")
            self._guardar_fallback(prefactura, fecha_viaje, "FALLIDO", motivo_fallo, None, None, placa_tractor, placa_remolque)
            return False
        except Exception as e:
            logger.error(f"❌ Error general: {e}")
            self._guardar_fallback(prefactura, fecha_viaje, "FALLIDO", motivo_fallo, None, None, placa_tractor, placa_remolque)
            return False
    
    def _actualizar_placas(self, cursor, prefactura, placa_tractor, placa_remolque):
        """
        FUNCIÓN AUXILIAR: Actualiza las placas si están disponibles
        """
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
    
    def actualizar_uuid_viajegm(self, prefactura, fecha_viaje, uuid, viajegm):
        """
        FUNCIÓN MODIFICADA: Actualiza UUID y VIAJEGM de un registro existente
        Ahora usa la nueva lógica de UPDATE
        """
        return self._actualizar_viaje_exitoso(prefactura, fecha_viaje, uuid, viajegm)
    
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
    
    def _guardar_fallback(self, prefactura, fecha_viaje, estatus, anotaciones, uuid, viajegm, placa_tractor, placa_remolque):
        """Guarda en archivo si MySQL no está disponible"""
        try:
            archivo_fallback = "viajes_fallback.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(archivo_fallback, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp}|{prefactura}|{fecha_viaje}|{estatus}|{anotaciones or ''}|{uuid or ''}|{viajegm or ''}|{placa_tractor or ''}|{placa_remolque or ''}\n")
                
            logger.warning(f"⚠️ Viaje guardado en archivo fallback: {archivo_fallback}")
            
        except Exception as e:
            logger.error(f"❌ Error crítico guardando fallback: {e}")
    
    def consultar_prefactura(self, prefactura):
        """
        NUEVA FUNCIÓN: Consulta los datos actuales de una prefactura
        
        Args:
            prefactura: Número de prefactura a consultar
            
        Returns:
            dict: Datos de la prefactura o None si no existe
        """
        try:
            if not self.conectar():
                return None
                
            cursor = self.connection.cursor(dictionary=True)
            
            query = "SELECT * FROM acumuladoprefactura WHERE NOPREFACTURA = %s"
            cursor.execute(query, (prefactura,))
            
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                logger.info(f"📊 Datos de prefactura {prefactura}:")
                for campo, valor in resultado.items():
                    logger.info(f"   {campo}: {valor}")
                    
            return resultado
            
        except Error as e:
            logger.error(f"❌ Error consultando prefactura: {e}")
            return None
    
    def probar_conexion(self):
        """Prueba la conexión y muestra información de la base de datos"""
        logger.info("🧪 Probando conexión a MySQL...")
        
        if self.conectar():
            logger.info("✅ Conexión exitosa")
            
            # Verificar tabla
            if self.verificar_tabla():
                logger.info("✅ Tabla 'acumuladoprefactura' verificada")
                logger.info("💡 Sistema configurado para UPDATE en lugar de INSERT")
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
def registrar_viaje_exitoso(prefactura, fecha_viaje, uuid=None, viajegm=None, placa_tractor=None, placa_remolque=None):
    """Actualiza un viaje existente como exitoso"""
    return mysql_acumulado.registrar_viaje_exitoso(prefactura, fecha_viaje, uuid, viajegm, placa_tractor, placa_remolque)

def registrar_viaje_fallido(prefactura, fecha_viaje, motivo_fallo, placa_tractor=None, placa_remolque=None):
    """Actualiza un viaje existente como fallido"""
    return mysql_acumulado.registrar_viaje_fallido(prefactura, fecha_viaje, motivo_fallo, placa_tractor, placa_remolque)

def actualizar_uuid_viajegm(prefactura, fecha_viaje, uuid, viajegm):
    """Actualiza UUID y VIAJEGM de un registro existente"""
    return mysql_acumulado.actualizar_uuid_viajegm(prefactura, fecha_viaje, uuid, viajegm)

def consultar_prefactura(prefactura):
    """NUEVA FUNCIÓN: Consulta los datos de una prefactura"""
    return mysql_acumulado.consultar_prefactura(prefactura)

def cerrar_conexion():
    """Cierra la conexión MySQL"""
    mysql_acumulado.desconectar()

# Script de prueba
if __name__ == "__main__":
    print("🧪 Probando conexión a MySQL...")
    
    # Probar conexión
    exito_conexion = mysql_acumulado.probar_conexion()
    
    if exito_conexion:
        print("\n🧪 Probando consulta de prefactura...")
        
        # Consultar una prefactura existente
        prefactura_test = "8053003"  # Usar la que sabemos que existe
        datos = consultar_prefactura(prefactura_test)
        
        if datos:
            print(f"✅ Prefactura {prefactura_test} encontrada en base de datos")
            print("\n🧪 Probando actualización...")
            
            # Probar actualización
            exito_update = registrar_viaje_exitoso(
                prefactura=prefactura_test,
                fecha_viaje="10/07/2025", 
                uuid="12345678-1234-1234-1234-123456789012",
                viajegm="COB-12345",
                placa_tractor="TEST123",
                placa_remolque="TEST456"
            )
            print(f"Actualización: {'✅' if exito_update else '❌'}")
        else:
            print(f"❌ Prefactura {prefactura_test} no encontrada")
    
    # Cerrar conexión
    cerrar_conexion()
    print("👋 Prueba completada")