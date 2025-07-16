#!/usr/bin/env python3
"""
Sistema de Cola de Viajes Persistente para Alsua Transport
Maneja una cola JSON de viajes pendientes de procesamiento
Garantiza que no se pierdan viajes por errores de login o driver corrupto
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ColaViajesManager:
    def __init__(self, archivo_cola="cola_viajes.json"):
        """
        Inicializa el manejador de cola de viajes
        
        Args:
            archivo_cola: Nombre del archivo JSON donde se guardan los viajes pendientes
        """
        self.archivo_cola = os.path.abspath(archivo_cola)
        self._verificar_archivo()
    
    def _verificar_archivo(self):
        """Verifica que el archivo JSON existe"""
        try:
            if not os.path.exists(self.archivo_cola):
                logger.info(f"📄 Creando nuevo archivo de cola: {self.archivo_cola}")
                self._crear_archivo_vacio()
            else:
                logger.info(f"📄 Archivo de cola encontrado: {self.archivo_cola}")
                # Verificar que es JSON válido
                self._leer_cola()
        except Exception as e:
            logger.error(f"❌ Error verificando archivo de cola: {e}")
            self._crear_archivo_vacio()
    
    def _crear_archivo_vacio(self):
        """Crea un archivo JSON vacío"""
        try:
            cola_vacia = []
            with open(self.archivo_cola, 'w', encoding='utf-8') as f:
                json.dump(cola_vacia, f, indent=2, ensure_ascii=False)
            logger.info("✅ Archivo de cola creado")
        except Exception as e:
            logger.error(f"❌ Error creando archivo de cola: {e}")
    
    def _leer_cola(self):
        """Lee la cola completa del archivo JSON"""
        try:
            with open(self.archivo_cola, 'r', encoding='utf-8') as f:
                cola = json.load(f)
            return cola if isinstance(cola, list) else []
        except Exception as e:
            logger.error(f"❌ Error leyendo cola: {e}")
            return []
    
    def _escribir_cola(self, cola):
        """Escribe la cola completa al archivo JSON"""
        try:
            with open(self.archivo_cola, 'w', encoding='utf-8') as f:
                json.dump(cola, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"❌ Error escribiendo cola: {e}")
            return False
    
    def agregar_viaje(self, datos_viaje):
        """
        Agrega un nuevo viaje a la cola
        
        Args:
            datos_viaje: Dict con todos los datos del viaje extraídos del correo
            
        Returns:
            bool: True si se agregó correctamente
        """
        try:
            # Preparar el registro del viaje
            viaje_registro = {
                'id': self._generar_id_viaje(datos_viaje),
                'timestamp_agregado': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'estado': 'PENDIENTE',
                'intentos_login': 0,
                'intentos_driver': 0,
                'ultimo_intento': None,
                'ultimo_error': None,
                'modulo_fallo': None,
                'datos_viaje': datos_viaje
            }
            
            # Leer cola actual
            cola = self._leer_cola()
            
            # Verificar si ya existe (anti-duplicados)
            prefactura = datos_viaje.get('prefactura')
            for viaje_existente in cola:
                if viaje_existente.get('datos_viaje', {}).get('prefactura') == prefactura:
                    logger.warning(f"⚠️ Viaje {prefactura} ya existe en cola - no agregando duplicado")
                    return False
            
            # Agregar nuevo viaje
            cola.append(viaje_registro)
            
            # Guardar cola
            if self._escribir_cola(cola):
                logger.info(f"✅ Viaje agregado a cola: {prefactura}")
                logger.info(f"   📊 Total viajes en cola: {len(cola)}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Error agregando viaje a cola: {e}")
            return False
    
    def obtener_siguiente_viaje(self):
        """
        Obtiene el siguiente viaje pendiente de la cola
        
        Returns:
            Dict: Datos del viaje o None si no hay viajes pendientes
        """
        try:
            cola = self._leer_cola()
            
            # Buscar primer viaje pendiente
            for viaje in cola:
                if viaje.get('estado') == 'PENDIENTE':
                    # Marcar como procesando
                    viaje['estado'] = 'PROCESANDO'
                    viaje['ultimo_intento'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Guardar cambios
                    if self._escribir_cola(cola):
                        prefactura = viaje.get('datos_viaje', {}).get('prefactura', 'DESCONOCIDA')
                        logger.info(f"🚀 Procesando viaje: {prefactura}")
                        return viaje
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo siguiente viaje: {e}")
            return None
    
    def marcar_viaje_exitoso(self, viaje_id):
        """
        Marca un viaje como exitoso y lo remove de la cola
        
        Args:
            viaje_id: ID del viaje
            
        Returns:
            bool: True si se marcó correctamente
        """
        return self._remover_viaje_completado(viaje_id, 'EXITOSO')
    
    def marcar_viaje_fallido(self, viaje_id, modulo_fallo, detalle_error):
        """
        Marca un viaje como fallido y lo remove de la cola
        
        Args:
            viaje_id: ID del viaje
            modulo_fallo: Módulo donde falló (gm_salida, gm_llegada, etc.)
            detalle_error: Detalle del error
            
        Returns:
            bool: True si se marcó correctamente
        """
        try:
            cola = self._leer_cola()
            
            # Buscar el viaje
            for viaje in cola:
                if viaje.get('id') == viaje_id:
                    prefactura = viaje.get('datos_viaje', {}).get('prefactura', 'DESCONOCIDA')
                    
                    logger.error(f"❌ PROCESO FALLÓ EN: {modulo_fallo}")
                    logger.error(f"   📋 Prefactura: {prefactura}")
                    logger.error(f"   🔍 Error: {detalle_error}")
                    logger.error(f"   📍 Módulo: {modulo_fallo}")
                    logger.error("   🔧 REQUIERE ATENCIÓN MANUAL")
                    
                    # Remover de cola
                    cola.remove(viaje)
                    
                    if self._escribir_cola(cola):
                        logger.info(f"🗑️ Viaje fallido removido de cola: {prefactura}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error marcando viaje fallido: {e}")
            return False
    
    def registrar_error_reintentable(self, viaje_id, tipo_error, detalle_error):
        """
        Registra un error que requiere reintento (login/driver corrupto)
        
        Args:
            viaje_id: ID del viaje
            tipo_error: 'LOGIN_LIMIT' o 'DRIVER_CORRUPTO'
            detalle_error: Detalle del error
            
        Returns:
            bool: True si se registró correctamente
        """
        try:
            cola = self._leer_cola()
            
            # Buscar el viaje
            for viaje in cola:
                if viaje.get('id') == viaje_id:
                    # Actualizar estado y contadores
                    viaje['estado'] = 'PENDIENTE'
                    viaje['ultimo_error'] = detalle_error
                    viaje['ultimo_intento'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    if tipo_error == 'LOGIN_LIMIT':
                        viaje['intentos_login'] = viaje.get('intentos_login', 0) + 1
                    elif tipo_error == 'DRIVER_CORRUPTO':
                        viaje['intentos_driver'] = viaje.get('intentos_driver', 0) + 1
                    
                    prefactura = viaje.get('datos_viaje', {}).get('prefactura', 'DESCONOCIDA')
                    intentos_login = viaje.get('intentos_login', 0)
                    intentos_driver = viaje.get('intentos_driver', 0)
                    
                    if tipo_error == 'LOGIN_LIMIT':
                        logger.warning(f"🚨 Error de login - límite de usuarios: {prefactura}")
                        logger.warning(f"   🔄 Intento #{intentos_login} - Reintentará en 15 minutos")
                    else:
                        logger.warning(f"🔧 Driver corrupto detectado: {prefactura}")
                        logger.warning(f"   🔄 Intento #{intentos_driver} - Reintentará inmediatamente")
                    
                    if self._escribir_cola(cola):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error registrando error reintentable: {e}")
            return False
    
    def _remover_viaje_completado(self, viaje_id, estado_final):
        """Remueve un viaje completado de la cola"""
        try:
            cola = self._leer_cola()
            
            # Buscar y remover el viaje
            for viaje in cola:
                if viaje.get('id') == viaje_id:
                    prefactura = viaje.get('datos_viaje', {}).get('prefactura', 'DESCONOCIDA')
                    cola.remove(viaje)
                    
                    if self._escribir_cola(cola):
                        logger.info(f"✅ Viaje {estado_final} removido de cola: {prefactura}")
                        logger.info(f"   📊 Viajes restantes en cola: {len(cola)}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error removiendo viaje completado: {e}")
            return False
    
    def _generar_id_viaje(self, datos_viaje):
        """Genera un ID único para el viaje"""
        prefactura = datos_viaje.get('prefactura', 'UNKNOWN')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefactura}_{timestamp}"
    
    def obtener_estadisticas_cola(self):
        """
        Obtiene estadísticas de la cola
        
        Returns:
            Dict: Estadísticas de la cola
        """
        try:
            cola = self._leer_cola()
            
            estadisticas = {
                'total_viajes': len(cola),
                'pendientes': 0,
                'procesando': 0,
                'total_intentos_login': 0,
                'total_intentos_driver': 0,
                'viajes_con_errores': 0
            }
            
            for viaje in cola:
                estado = viaje.get('estado', '')
                if estado == 'PENDIENTE':
                    estadisticas['pendientes'] += 1
                elif estado == 'PROCESANDO':
                    estadisticas['procesando'] += 1
                
                estadisticas['total_intentos_login'] += viaje.get('intentos_login', 0)
                estadisticas['total_intentos_driver'] += viaje.get('intentos_driver', 0)
                
                if viaje.get('ultimo_error'):
                    estadisticas['viajes_con_errores'] += 1
            
            return estadisticas
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {'error': str(e)}
    
    def limpiar_cola_vacia(self):
        """Limpia la cola si está vacía (mantiene archivo pero vacío)"""
        try:
            cola = self._leer_cola()
            if len(cola) == 0:
                logger.info("🧹 Cola vacía - archivo mantenido")
                return True
            else:
                logger.info(f"📊 Cola tiene {len(cola)} viajes pendientes")
                return False
        except Exception as e:
            logger.error(f"❌ Error limpiando cola: {e}")
            return False

# Instancia global para uso en toda la aplicación
cola_viajes = ColaViajesManager()

# Funciones de conveniencia
def agregar_viaje_a_cola(datos_viaje):
    """Función de conveniencia para agregar viaje a cola"""
    return cola_viajes.agregar_viaje(datos_viaje)

def obtener_siguiente_viaje_cola():
    """Función de conveniencia para obtener siguiente viaje"""
    return cola_viajes.obtener_siguiente_viaje()

def marcar_viaje_exitoso_cola(viaje_id):
    """Función de conveniencia para marcar viaje como exitoso"""
    return cola_viajes.marcar_viaje_exitoso(viaje_id)

def marcar_viaje_fallido_cola(viaje_id, modulo_fallo, detalle_error):
    """Función de conveniencia para marcar viaje como fallido"""
    return cola_viajes.marcar_viaje_fallido(viaje_id, modulo_fallo, detalle_error)

def registrar_error_reintentable_cola(viaje_id, tipo_error, detalle_error):
    """Función de conveniencia para registrar error reintentable"""
    return cola_viajes.registrar_error_reintentable(viaje_id, tipo_error, detalle_error)

def obtener_estadisticas_cola():
    """Función de conveniencia para obtener estadísticas"""
    return cola_viajes.obtener_estadisticas_cola()

# Script de prueba
if __name__ == "__main__":
    print("🧪 Probando ColaViajesManager...")
    
    # Datos de prueba
    datos_prueba = {
        'prefactura': 'TEST123',
        'fecha': '15/07/2025',
        'placa_tractor': 'TEST01',
        'placa_remolque': 'TEST02',
        'clave_determinante': '1234',
        'importe': 100.00
    }
    
    # Agregar viaje de prueba
    print("➕ Agregando viaje de prueba...")
    resultado = agregar_viaje_a_cola(datos_prueba)
    print(f"   Resultado: {resultado}")
    
    # Obtener estadísticas
    print("\n📊 Estadísticas de cola:")
    stats = obtener_estadisticas_cola()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Prueba completada")