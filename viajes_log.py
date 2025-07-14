#!/usr/bin/env python3
"""
Sistema de Log Unificado para Automatización Alsua Transport
Maneja un archivo CSV único con todos los viajes procesados (exitosos y fallidos)
"""

import csv
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ViajesLogManager:
    def __init__(self, archivo_csv="viajes_log.csv"):
        """
        Inicializa el manejador de log de viajes
        
        Args:
            archivo_csv: Nombre del archivo CSV donde se guardarán los registros
        """
        self.archivo_csv = os.path.abspath(archivo_csv)
        self.campos = [
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
        self._verificar_archivo()
    
    def _verificar_archivo(self):
        """Verifica que el archivo CSV existe y tiene los headers correctos"""
        try:
            if not os.path.exists(self.archivo_csv):
                logger.info(f"📄 Creando nuevo archivo de log: {self.archivo_csv}")
                self._crear_archivo_con_headers()
            else:
                logger.info(f"📄 Archivo de log encontrado: {self.archivo_csv}")
                self._verificar_headers()
                
        except Exception as e:
            logger.error(f"❌ Error verificando archivo de log: {e}")
    
    def _crear_archivo_con_headers(self):
        """Crea el archivo CSV con los headers correctos"""
        try:
            with open(self.archivo_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos)
                writer.writeheader()
            logger.info("✅ Archivo de log creado con headers")
        except Exception as e:
            logger.error(f"❌ Error creando archivo de log: {e}")
    
    def _verificar_headers(self):
        """Verifica que el archivo existente tiene los headers correctos"""
        try:
            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers_existentes = reader.fieldnames or []
                
            # Verificar si faltan campos
            campos_faltantes = set(self.campos) - set(headers_existentes)
            if campos_faltantes:
                logger.warning(f"⚠️ Campos faltantes en CSV: {campos_faltantes}")
                # En producción, podrías agregar los campos faltantes aquí
                
        except Exception as e:
            logger.warning(f"⚠️ Error verificando headers: {e}")
    
    def registrar_viaje_exitoso(self, prefactura, determinante=None, fecha_viaje=None, 
                               placa_tractor=None, placa_remolque=None, uuid=None, 
                               viajegm=None, importe=None, cliente_codigo=None):
        """
        Registra un viaje exitoso en el log
        
        Args:
            prefactura: Número de prefactura
            determinante: Clave determinante
            fecha_viaje: Fecha del viaje
            placa_tractor: Placa del tractor
            placa_remolque: Placa del remolque
            uuid: UUID extraído del PDF
            viajegm: Código del viaje en GM
            importe: Monto del viaje
            cliente_codigo: Código del cliente
            
        Returns:
            bool: True si se registró correctamente
        """
        return self._escribir_registro(
            prefactura=prefactura,
            determinante=determinante,
            fecha_viaje=fecha_viaje,
            placa_tractor=placa_tractor,
            placa_remolque=placa_remolque,
            estatus="EXITOSO",
            motivo_fallo="",
            uuid=uuid,
            viajegm=viajegm,
            importe=importe,
            cliente_codigo=cliente_codigo
        )
    
    def registrar_viaje_fallido(self, prefactura, motivo_fallo, determinante=None, 
                               fecha_viaje=None, placa_tractor=None, placa_remolque=None,
                               importe=None, cliente_codigo=None):
        """
        Registra un viaje fallido en el log
        
        Args:
            prefactura: Número de prefactura
            motivo_fallo: Razón del fallo
            determinante: Clave determinante
            fecha_viaje: Fecha del viaje
            placa_tractor: Placa del tractor
            placa_remolque: Placa del remolque
            importe: Monto del viaje
            cliente_codigo: Código del cliente
            
        Returns:
            bool: True si se registró correctamente
        """
        return self._escribir_registro(
            prefactura=prefactura,
            determinante=determinante,
            fecha_viaje=fecha_viaje,
            placa_tractor=placa_tractor,
            placa_remolque=placa_remolque,
            estatus="FALLIDO",
            motivo_fallo=motivo_fallo,
            uuid="",
            viajegm="",
            importe=importe,
            cliente_codigo=cliente_codigo
        )
    
    def _escribir_registro(self, **kwargs):
        """
        Escribe un registro en el archivo CSV
        
        Args:
            **kwargs: Todos los campos del registro
            
        Returns:
            bool: True si se escribió correctamente
        """
        try:
            # Preparar el registro con timestamp
            registro = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'prefactura': kwargs.get('prefactura', ''),
                'determinante': kwargs.get('determinante', ''),
                'fecha_viaje': kwargs.get('fecha_viaje', ''),
                'placa_tractor': kwargs.get('placa_tractor', ''),
                'placa_remolque': kwargs.get('placa_remolque', ''),
                'estatus': kwargs.get('estatus', ''),
                'motivo_fallo': kwargs.get('motivo_fallo', ''),
                'uuid': kwargs.get('uuid', ''),
                'viajegm': kwargs.get('viajegm', ''),
                'importe': kwargs.get('importe', ''),
                'cliente_codigo': kwargs.get('cliente_codigo', '')
            }
            
            # Escribir al archivo
            with open(self.archivo_csv, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos)
                writer.writerow(registro)
            
            # Log del registro
            estatus = registro['estatus']
            prefactura = registro['prefactura']
            if estatus == "EXITOSO":
                logger.info(f"✅ Viaje EXITOSO registrado: {prefactura}")
                logger.info(f"   🆔 UUID: {registro['uuid']}")
                logger.info(f"   🚛 ViajeGM: {registro['viajegm']}")
            else:
                logger.info(f"❌ Viaje FALLIDO registrado: {prefactura}")
                logger.info(f"   🔍 Motivo: {registro['motivo_fallo']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error escribiendo registro al log: {e}")
            return False
    
    def verificar_viaje_existe(self, prefactura, determinante=None):
        """
        Verifica si un viaje ya fue procesado (anti-duplicados)
        
        Args:
            prefactura: Número de prefactura
            determinante: Clave determinante (opcional para mayor precisión)
            
        Returns:
            dict: Información del viaje si existe, None si no existe
        """
        try:
            if not os.path.exists(self.archivo_csv):
                return None
                
            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Buscar por prefactura
                    if row['prefactura'] == str(prefactura):
                        # Si se proporciona determinante, verificar que coincida también
                        if determinante and row['determinante'] != str(determinante):
                            continue
                            
                        logger.info(f"🔍 Viaje encontrado en log: {prefactura}")
                        logger.info(f"   📊 Estatus: {row['estatus']}")
                        logger.info(f"   📅 Timestamp: {row['timestamp']}")
                        return dict(row)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error verificando viaje en log: {e}")
            return None
    
    def leer_viajes_por_estatus(self, estatus):
        """
        Lee todos los viajes con un estatus específico
        
        Args:
            estatus: "EXITOSO" o "FALLIDO"
            
        Returns:
            List[Dict]: Lista de viajes con ese estatus
        """
        viajes = []
        try:
            if not os.path.exists(self.archivo_csv):
                return viajes
                
            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    if row['estatus'] == estatus:
                        viajes.append(dict(row))
            
            logger.info(f"📊 Encontrados {len(viajes)} viajes con estatus: {estatus}")
            return viajes
            
        except Exception as e:
            logger.error(f"❌ Error leyendo viajes por estatus: {e}")
            return viajes
    
    def obtener_estadisticas(self):
        """
        Obtiene estadísticas del log de viajes
        
        Returns:
            Dict: Estadísticas del log
        """
        estadisticas = {
            'total_viajes': 0,
            'exitosos': 0,
            'fallidos': 0,
            'motivos_fallo': {},
            'ultimo_viaje': None
        }
        
        try:
            if not os.path.exists(self.archivo_csv):
                return estadisticas
                
            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    estadisticas['total_viajes'] += 1
                    
                    if row['estatus'] == 'EXITOSO':
                        estadisticas['exitosos'] += 1
                    elif row['estatus'] == 'FALLIDO':
                        estadisticas['fallidos'] += 1
                        motivo = row['motivo_fallo']
                        estadisticas['motivos_fallo'][motivo] = estadisticas['motivos_fallo'].get(motivo, 0) + 1
                    
                    estadisticas['ultimo_viaje'] = row['timestamp']
            
            return estadisticas
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return estadisticas
    
    def limpiar_registros_antiguos(self, dias=30):
        """
        Limpia registros más antiguos que X días
        
        Args:
            dias: Número de días a mantener
            
        Returns:
            int: Número de registros eliminados
        """
        try:
            if not os.path.exists(self.archivo_csv):
                return 0
            
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=dias)
            
            # Leer todos los registros
            registros_actuales = []
            with open(self.archivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        fecha_registro = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                        if fecha_registro >= cutoff_date:
                            registros_actuales.append(row)
                    except:
                        # Mantener registros con fecha inválida
                        registros_actuales.append(row)
            
            # Reescribir archivo con solo registros recientes
            registros_eliminados = 0
            with open(self.archivo_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.campos)
                writer.writeheader()
                
                total_original = 0
                with open(self.archivo_csv, 'r', encoding='utf-8') as f_temp:
                    total_original = sum(1 for line in f_temp) - 1  # -1 por header
                
                writer.writerows(registros_actuales)
                registros_eliminados = total_original - len(registros_actuales)
            
            if registros_eliminados > 0:
                logger.info(f"🧹 Limpieza completada: {registros_eliminados} registros eliminados")
            
            return registros_eliminados
            
        except Exception as e:
            logger.error(f"❌ Error limpiando registros antiguos: {e}")
            return 0


# Instancia global para uso en toda la aplicación
viajes_log = ViajesLogManager()

# Funciones de conveniencia para importar fácilmente
def registrar_viaje_exitoso(prefactura, determinante=None, fecha_viaje=None, 
                           placa_tractor=None, placa_remolque=None, uuid=None, 
                           viajegm=None, importe=None, cliente_codigo=None):
    """Función de conveniencia para registrar viaje exitoso"""
    return viajes_log.registrar_viaje_exitoso(
        prefactura=prefactura,
        determinante=determinante,
        fecha_viaje=fecha_viaje,
        placa_tractor=placa_tractor,
        placa_remolque=placa_remolque,
        uuid=uuid,
        viajegm=viajegm,
        importe=importe,
        cliente_codigo=cliente_codigo
    )

def registrar_viaje_fallido(prefactura, motivo_fallo, determinante=None, 
                           fecha_viaje=None, placa_tractor=None, placa_remolque=None,
                           importe=None, cliente_codigo=None):
    """Función de conveniencia para registrar viaje fallido"""
    return viajes_log.registrar_viaje_fallido(
        prefactura=prefactura,
        motivo_fallo=motivo_fallo,
        determinante=determinante,
        fecha_viaje=fecha_viaje,
        placa_tractor=placa_tractor,
        placa_remolque=placa_remolque,
        importe=importe,
        cliente_codigo=cliente_codigo
    )

def verificar_viaje_existe(prefactura, determinante=None):
    """Función de conveniencia para verificar si viaje existe"""
    return viajes_log.verificar_viaje_existe(prefactura, determinante)

def obtener_estadisticas():
    """Función de conveniencia para obtener estadísticas"""
    return viajes_log.obtener_estadisticas()

# Script de prueba
if __name__ == "__main__":
    print("🧪 Probando sistema de log unificado...")
    
    # Probar registro exitoso
    print("\n1. Probando registro exitoso...")
    exito1 = registrar_viaje_exitoso(
        prefactura="7996845",
        determinante="2899", 
        fecha_viaje="15/01/2025",
        placa_tractor="94BB1F",
        placa_remolque="852YH6",
        uuid="12345678-1234-1234-1234-123456789012",
        viajegm="COB-12345",
        importe="310.75",
        cliente_codigo="040512"
    )
    print(f"Resultado: {'✅' if exito1 else '❌'}")
    
    # Probar registro fallido
    print("\n2. Probando registro fallido...")
    exito2 = registrar_viaje_fallido(
        prefactura="7996846",
        motivo_fallo="Placa 94BB1G no tiene operador asignado",
        determinante="4792",
        fecha_viaje="15/01/2025",
        placa_tractor="94BB1G",
        placa_remolque="852YH7",
        importe="285.50",
        cliente_codigo="040512"
    )
    print(f"Resultado: {'✅' if exito2 else '❌'}")
    
    # Probar verificación de duplicados
    print("\n3. Probando verificación de duplicados...")
    existe = verificar_viaje_existe("7996845")
    print(f"Viaje 7996845 existe: {'✅ Sí' if existe else '❌ No'}")
    
    # Mostrar estadísticas
    print("\n4. Estadísticas del log:")
    stats = obtener_estadisticas()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print(f"\n✅ Archivo de log creado: {viajes_log.archivo_csv}")
    print("📄 Puedes abrirlo con Excel para ver los registros")