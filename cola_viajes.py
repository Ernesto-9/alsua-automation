import json
import os
import uuid
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ARCHIVO_COLA = "cola_viajes.json"

class ColaViajes:
    def __init__(self):
        self.archivo = os.path.abspath(ARCHIVO_COLA)
        self._verificar_archivo()
        
    def _verificar_archivo(self):
        if not os.path.exists(self.archivo):
            self._crear_archivo_vacio()
            logger.info(f"Archivo de cola creado: {self.archivo}")
        else:
            logger.info(f"Archivo de cola encontrado: {self.archivo}")
    
    def _crear_archivo_vacio(self):
        datos_iniciales = {"viajes": []}
        with open(self.archivo, 'w', encoding='utf-8') as f:
            json.dump(datos_iniciales, f, indent=2, ensure_ascii=False)
    
    def _leer_cola(self):
        try:
            with open(self.archivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error leyendo cola: {e}")
            return {"viajes": []}
    
    def _guardar_cola(self, datos):
        try:
            with open(self.archivo, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error guardando cola: {e}")
            return False
    
    def resetear_viajes_atascados(self):
        try:
            datos = self._leer_cola()
            viajes_reseteados = 0

            for viaje in datos.get("viajes", []):
                if viaje.get("estado") == "procesando":
                    viaje["estado"] = "pendiente"
                    if "intentos" not in viaje:
                        viaje["intentos"] = 0
                    viajes_reseteados += 1

                    prefactura = viaje.get("datos_viaje", {}).get("prefactura", "DESCONOCIDA")
                    logger.warning(f"Viaje atascado reseteado: {prefactura}")

            if viajes_reseteados > 0:
                self._guardar_cola(datos)
                logger.info(f"Total viajes reseteados: {viajes_reseteados}")
            else:
                logger.info("No hay viajes atascados para resetear")

            return viajes_reseteados

        except Exception as e:
            logger.error(f"Error reseteando viajes atascados: {e}")
            return 0

    def limpiar_viajes_zombie(self):
        """
        Elimina SILENCIOSAMENTE de la cola los viajes que ya fueron procesados (zombie)
        Un viaje zombie es aquel que está en cola_viajes.json pero ya existe en viajes_log.csv

        Returns:
            int: Número de viajes zombie eliminados
        """
        try:
            from viajes_log import verificar_viaje_existe

            datos = self._leer_cola()
            viajes_originales = datos.get("viajes", [])
            viajes_limpios = []
            eliminados = 0

            for viaje in viajes_originales:
                prefactura = viaje.get("datos_viaje", {}).get("prefactura", "DESCONOCIDA")

                # Verificar si el viaje ya existe en el log
                if verificar_viaje_existe(prefactura):
                    # Es un viaje zombie - eliminar silenciosamente
                    eliminados += 1
                else:
                    # Viaje válido - mantener en cola
                    viajes_limpios.append(viaje)

            # Guardar cola limpia si hubo cambios
            if eliminados > 0:
                datos["viajes"] = viajes_limpios
                self._guardar_cola(datos)

            return eliminados

        except Exception as e:
            logger.error(f"Error limpiando viajes zombie: {e}")
            return 0
    
    def agregar_viaje(self, datos_viaje):
        try:
            prefactura = datos_viaje.get('prefactura')
            if not prefactura:
                logger.error("No se puede agregar viaje sin prefactura")
                return False
            
            datos = self._leer_cola()
            
            for viaje in datos.get("viajes", []):
                if viaje.get("datos_viaje", {}).get("prefactura") == prefactura:
                    logger.warning(f"Viaje {prefactura} ya existe en cola")
                    return False
            
            nuevo_viaje = {
                "id": str(uuid.uuid4()),
                "datos_viaje": datos_viaje,
                "estado": "pendiente",
                "fecha_agregado": datetime.now().isoformat(),
                "intentos": 0,
                "errores": []
            }
            
            datos["viajes"].append(nuevo_viaje)
            
            if self._guardar_cola(datos):
                logger.info(f"Viaje agregado a cola: {prefactura}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error agregando viaje a cola: {e}")
            return False
    
    def obtener_siguiente_viaje(self, max_intentos=5):
        try:
            datos = self._leer_cola()
            viajes_actualizados = False

            for viaje in datos.get("viajes", []):
                if viaje.get("estado") == "pendiente":
                    intentos = viaje.get("intentos", 0)
                    prefactura = viaje.get('datos_viaje', {}).get('prefactura', 'DESCONOCIDA')

                    if intentos >= max_intentos:
                        logger.warning(f"Viaje {prefactura} superó límite de {max_intentos} intentos")
                        self.marcar_viaje_fallido(
                            viaje.get("id"),
                            "MAX_INTENTOS_EXCEDIDOS",
                            f"Superó el límite de {max_intentos} intentos. Último error: {viaje.get('errores', [{}])[-1].get('tipo', 'DESCONOCIDO')}"
                        )
                        viajes_actualizados = True
                        continue

                    viaje["estado"] = "procesando"
                    viaje["fecha_inicio_procesamiento"] = datetime.now().isoformat()

                    if self._guardar_cola(datos):
                        return viaje
                    else:
                        return None

            if viajes_actualizados:
                return self.obtener_siguiente_viaje(max_intentos)

            return None

        except Exception as e:
            logger.error(f"Error obteniendo siguiente viaje: {e}")
            return None
    
    def marcar_viaje_exitoso(self, viaje_id):
        try:
            datos = self._leer_cola()
            
            viajes_actualizados = []
            viaje_encontrado = False
            
            for viaje in datos.get("viajes", []):
                if viaje.get("id") == viaje_id:
                    viaje_encontrado = True
                    logger.info(f"Viaje exitoso removido de cola: {viaje.get('datos_viaje', {}).get('prefactura')}")
                else:
                    viajes_actualizados.append(viaje)
            
            if viaje_encontrado:
                datos["viajes"] = viajes_actualizados
                return self._guardar_cola(datos)
            else:
                logger.warning(f"Viaje {viaje_id} no encontrado para marcar como exitoso")
                return False
                
        except Exception as e:
            logger.error(f"Error marcando viaje exitoso: {e}")
            return False
    
    def marcar_viaje_fallido(self, viaje_id, modulo_error, motivo):
        try:
            datos = self._leer_cola()
            
            viajes_actualizados = []
            viaje_encontrado = False
            
            for viaje in datos.get("viajes", []):
                if viaje.get("id") == viaje_id:
                    viaje_encontrado = True
                    prefactura = viaje.get('datos_viaje', {}).get('prefactura')
                    logger.error(f"Viaje fallido removido de cola: {prefactura} - {modulo_error}")
                else:
                    viajes_actualizados.append(viaje)
            
            if viaje_encontrado:
                datos["viajes"] = viajes_actualizados
                return self._guardar_cola(datos)
            else:
                logger.warning(f"Viaje {viaje_id} no encontrado para marcar como fallido")
                return False
                
        except Exception as e:
            logger.error(f"Error marcando viaje fallido: {e}")
            return False
    
    def registrar_error_reintentable(self, viaje_id, tipo_error, detalle):
        try:
            datos = self._leer_cola()

            for viaje in datos.get("viajes", []):
                if viaje.get("id") == viaje_id:
                    viaje["estado"] = "pendiente"
                    viaje["intentos"] = viaje.get("intentos", 0) + 1
                    viaje["fecha_inicio_procesamiento"] = None

                    error_info = {
                        "tipo": tipo_error,
                        "detalle": detalle,
                        "timestamp": datetime.now().isoformat()
                    }

                    if "errores" not in viaje:
                        viaje["errores"] = []
                    viaje["errores"].append(error_info)

                    prefactura = viaje.get('datos_viaje', {}).get('prefactura')
                    logger.warning(f"Error reintentable registrado para {prefactura}: {tipo_error} (intento {viaje['intentos']})")

                    return self._guardar_cola(datos)

            logger.warning(f"Viaje {viaje_id} no encontrado para registrar error")
            return False

        except Exception as e:
            logger.error(f"Error registrando error reintentable: {e}")
            return False
    
    def obtener_estadisticas(self):
        try:
            datos = self._leer_cola()
            viajes = datos.get("viajes", [])
            
            total = len(viajes)
            pendientes = sum(1 for v in viajes if v.get("estado") == "pendiente")
            procesando = sum(1 for v in viajes if v.get("estado") == "procesando")
            con_errores = sum(1 for v in viajes if len(v.get("errores", [])) > 0)
            
            return {
                "total_viajes": total,
                "pendientes": pendientes,
                "procesando": procesando,
                "viajes_con_errores": con_errores
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                "total_viajes": 0,
                "pendientes": 0,
                "procesando": 0,
                "viajes_con_errores": 0
            }

cola_viajes = ColaViajes()

def resetear_viajes_atascados():
    return cola_viajes.resetear_viajes_atascados()

def limpiar_viajes_zombie():
    return cola_viajes.limpiar_viajes_zombie()

def agregar_viaje_a_cola(datos_viaje):
    return cola_viajes.agregar_viaje(datos_viaje)

def obtener_siguiente_viaje_cola():
    return cola_viajes.obtener_siguiente_viaje()

def marcar_viaje_exitoso_cola(viaje_id):
    return cola_viajes.marcar_viaje_exitoso(viaje_id)

def marcar_viaje_fallido_cola(viaje_id, modulo_error, motivo):
    return cola_viajes.marcar_viaje_fallido(viaje_id, modulo_error, motivo)

def registrar_error_reintentable_cola(viaje_id, tipo_error, detalle):
    return cola_viajes.registrar_error_reintentable(viaje_id, tipo_error, detalle)

def obtener_estadisticas_cola():
    return cola_viajes.obtener_estadisticas()

def leer_cola():
    return cola_viajes._leer_cola()

if __name__ == "__main__":
    print("Probando sistema de cola...")
    
    print("\nEstadísticas actuales:")
    stats = obtener_estadisticas_cola()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\nProbando reseteo de viajes atascados...")
    reseteados = resetear_viajes_atascados()
    print(f"Viajes reseteados: {reseteados}")
    
    print("\nPrueba completada")