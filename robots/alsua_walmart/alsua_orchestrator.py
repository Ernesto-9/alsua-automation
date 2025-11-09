#!/usr/bin/env python3
"""
Orquestador principal del sistema de automatización Alsua Transport
Versión refactorizada usando arquitectura modular

Mail Reader → Cola JSON → GM Automation
"""

import os
import time
import logging
import sys
from datetime import datetime

# Imports de módulos refactorizados
from core.email.outlook_client import OutlookEmailClient
from core.browser.driver_manager import DriverManager
from robots.alsua_walmart.processors.trip_processor import TripProcessor
from core.queue.queue_processor import QueueProcessor

# Imports de módulos existentes (legacy)
from robots.alsua_walmart.parsers.xls_parser import parse_xls
from shared.crm.gm_transport.login import login_to_gm
from shared.crm.gm_transport.automation import GMTransportAutomation

# Imports de cola (legacy)
from cola_viajes import (
    agregar_viaje_a_cola,
    obtener_siguiente_viaje_cola,
    marcar_viaje_exitoso_cola,
    marcar_viaje_fallido_cola,
    registrar_error_reintentable_cola,
    obtener_estadisticas_cola,
    resetear_viajes_atascados,
    leer_cola,
    limpiar_viajes_zombie
)
from viajes_log import viajes_log

# Imports de mejora (legacy)
from modules import robot_state_manager
from modules.debug_logger import debug_logger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class AlsuaOrchestrator:
    """
    Orquestador principal del sistema de automatización
    Coordina email, cola, procesamiento y browser
    """

    # Variable de clase para controlar la ejecución desde Flask
    continuar_ejecutando = True

    def __init__(self):
        """Inicializa todos los componentes del sistema"""
        self.carpeta_descarga = os.path.abspath("archivos_descargados")
        self._crear_carpeta_descarga()

        # Componentes refactorizados
        self.email_client = OutlookEmailClient()
        self.driver_manager = DriverManager(login_to_gm)
        self.trip_processor = TripProcessor(
            self.driver_manager,
            viajes_log,
            robot_state_manager,
            debug_logger
        )

        # Funciones de cola
        self.cola_functions = {
            'obtener_siguiente': obtener_siguiente_viaje_cola,
            'marcar_exitoso': marcar_viaje_exitoso_cola,
            'marcar_fallido': marcar_viaje_fallido_cola,
            'registrar_error': registrar_error_reintentable_cola,
            'obtener_estadisticas': obtener_estadisticas_cola
        }

        self.queue_processor = QueueProcessor(
            self.trip_processor,
            self.cola_functions,
            robot_state_manager
        )

    def _crear_carpeta_descarga(self):
        """Crea y valida la carpeta de descarga de archivos"""
        try:
            if not os.path.exists(self.carpeta_descarga):
                os.makedirs(self.carpeta_descarga)

            # Test de permisos
            test_file = os.path.join(self.carpeta_descarga, "test_permisos.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                logger.error(f"Error de permisos en carpeta: {e}")
                self.carpeta_descarga = os.path.join(
                    os.path.expanduser("~"), "Downloads", "alsua_archivos"
                )
                os.makedirs(self.carpeta_descarga, exist_ok=True)
                logger.warning(f"Usando carpeta alternativa: {self.carpeta_descarga}")

        except Exception as e:
            logger.error(f"Error al crear carpeta: {e}")
            self.carpeta_descarga = os.path.join(
                os.path.expanduser("~"), "Downloads", "alsua_archivos"
            )
            os.makedirs(self.carpeta_descarga, exist_ok=True)
            logger.warning(f"Carpeta fallback: {self.carpeta_descarga}")

    def revisar_y_extraer_correos(self, limite_viajes=3):
        """
        Revisa correos y extrae viajes a la cola

        Args:
            limite_viajes: Número máximo de viajes a extraer

        Returns:
            bool: True si extrajo al menos un viaje
        """
        return self.email_client.revisar_y_extraer_correos(
            self.carpeta_descarga,
            parse_xls,
            viajes_log,
            agregar_viaje_a_cola,
            limite_viajes
        )

    def procesar_cola_viajes(self):
        """Procesa todos los viajes en cola (modo simple)"""
        try:
            return self.queue_processor.procesar_cola_simple(GMTransportAutomation)
        finally:
            self.driver_manager.limpiar_driver()
            self.email_client.limpiar_com()

    def mostrar_estadisticas_inicio(self):
        """Muestra estadísticas al inicio del sistema"""
        try:
            stats_cola = obtener_estadisticas_cola()
            logger.info(
                f"Cola: {stats_cola.get('total_viajes', 0)} | "
                f"Pendientes: {stats_cola.get('pendientes', 0)} | "
                f"Procesando: {stats_cola.get('procesando', 0)}"
            )
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de cola: {e}")

    def ejecutar_bucle_continuo(self, mostrar_debug=False):
        """
        Bucle principal continuo: revisa emails → procesa cola → repite

        Args:
            mostrar_debug: Si True, muestra logs de debug cada ciclo
        """
        # Resetear viajes atascados al inicio
        viajes_reseteados = resetear_viajes_atascados()
        if viajes_reseteados > 0:
            logger.warning(f"Se resetearon {viajes_reseteados} viajes atascados")

        robot_state_manager.actualizar_estado_robot("ejecutando")
        debug_logger.info("Iniciando bucle continuo de automatización")

        self.mostrar_estadisticas_inicio()

        try:
            contador_ciclos = 0
            contador_sync_mysql = 0
            ultimo_sync_mysql = time.time()
            ultima_cant_viajes = -1

            while AlsuaOrchestrator.continuar_ejecutando:
                try:
                    contador_ciclos += 1
                    if mostrar_debug:
                        logger.info(f"Ciclo #{contador_ciclos}")

                    # Limpieza de viajes stuck
                    try:
                        robot_state_manager.verificar_y_limpiar_viaje_stuck()
                    except:
                        pass

                    # Actualizar cola en estado_robots.json
                    try:
                        cola_actual = leer_cola()
                        viajes = cola_actual.get('viajes', [])
                        cant_actual = len(viajes)

                        if cant_actual != ultima_cant_viajes:
                            if cant_actual > 0:
                                viajes_pendientes = [
                                    {
                                        'prefactura': v.get('datos_viaje', {}).get('prefactura', 'N/A'),
                                        'fecha': v.get('datos_viaje', {}).get('fecha', 'N/A'),
                                        'placa_tractor': v.get('datos_viaje', {}).get('placa_tractor', 'N/A'),
                                        'placa_remolque': v.get('datos_viaje', {}).get('placa_remolque', 'N/A')
                                    }
                                    for v in viajes
                                    if v.get('estado') in ['pendiente', 'procesando']
                                ]
                                robot_state_manager.actualizar_cola(viajes_pendientes)
                            else:
                                robot_state_manager.actualizar_cola([])

                            ultima_cant_viajes = cant_actual
                    except:
                        pass

                    # Procesar un viaje si hay en cola
                    viaje_registro = obtener_siguiente_viaje_cola()

                    if viaje_registro:
                        resultado, modulo_error, prefactura = self.queue_processor.procesar_un_viaje(
                            GMTransportAutomation
                        )

                        if resultado == 'EXITOSO':
                            contador_sync_mysql += 1
                            time.sleep(60)

                        elif resultado == 'LOGIN_LIMIT':
                            time.sleep(15 * 60)

                        elif resultado == 'DRIVER_CORRUPTO':
                            pass  # Reintenta inmediatamente

                        else:
                            contador_sync_mysql += 1
                            time.sleep(30)

                        # Batch MySQL sync: cada 5 viajes o cada 10 minutos
                        ahora = time.time()
                        if contador_sync_mysql >= 5 or (ahora - ultimo_sync_mysql) > 600:
                            from modules.mysql_simple import sincronizar_csv_a_mysql
                            sincronizar_csv_a_mysql()
                            contador_sync_mysql = 0
                            ultimo_sync_mysql = ahora

                    else:
                        # No hay viajes en cola, revisar emails
                        viajes_encontrados = self.revisar_y_extraer_correos(limite_viajes=3)

                        if viajes_encontrados:
                            logger.info(f"Nuevos viajes agregados a cola")
                        else:
                            time.sleep(10)

                    # Limpieza zombie automática cada 100 ciclos (~1 hora)
                    if contador_ciclos % 100 == 0:
                        try:
                            eliminados = limpiar_viajes_zombie()
                            if eliminados > 0:
                                logger.warning(f"Limpieza zombie: {eliminados} viajes eliminados")
                        except:
                            pass

                    # Estadísticas periódicas
                    if contador_ciclos % 10 == 0:
                        try:
                            stats = obtener_estadisticas_cola()
                            if stats.get('total_viajes', 0) > 0:
                                logger.info(f"Cola actual: {stats.get('pendientes', 0)} pendientes")
                        except:
                            pass

                except KeyboardInterrupt:
                    logger.info("Interrupción manual detectada")
                    break

                except Exception as e:
                    logger.error(f"Error en ciclo continuo: {e}")
                    logger.info("Continuando con siguiente ciclo en 30 segundos...")
                    time.sleep(30)

        except KeyboardInterrupt:
            logger.info("Sistema detenido por usuario")

        finally:
            # Sync final de MySQL antes de cerrar
            try:
                from modules.mysql_simple import sincronizar_csv_a_mysql
                sincronizar_csv_a_mysql()
            except:
                pass

            robot_state_manager.limpiar_viaje_actual()
            robot_state_manager.actualizar_estado_robot("detenido")
            debug_logger.info("Bucle continuo finalizado")

            self.driver_manager.limpiar_driver()
            self.email_client.limpiar_com()

            logger.info("Sistema de automatización finalizado")

    def ejecutar_revision_unica(self):
        """Ejecuta una revisión única de emails y procesa viajes (modo test)"""
        logger.info("Ejecutando revisión única...")
        logger.info("MODO TEST: Solo algunos ciclos para inspección")

        self.mostrar_estadisticas_inicio()

        try:
            ciclos_max = 5
            logger.info(f"Ejecutando máximo {ciclos_max} ciclos de prueba...")

            for ciclo in range(ciclos_max):
                logger.info(f"Ciclo de prueba {ciclo + 1}/{ciclos_max}")

                viajes_encontrados = self.revisar_y_extraer_correos()

                if viajes_encontrados:
                    logger.info("Nuevos viajes encontrados en modo test")

                viaje_registro = obtener_siguiente_viaje_cola()

                if viaje_registro:
                    prefactura = viaje_registro.get('datos_viaje', {}).get('prefactura', 'DESCONOCIDA')
                    logger.info(f"MODO TEST: Procesando viaje {prefactura}")

                    resultado, modulo_error, _ = self.queue_processor.procesar_un_viaje(
                        GMTransportAutomation
                    )
                    logger.info(f"Resultado test: {resultado} en {modulo_error}")

                    if resultado in ['EXITOSO', 'VIAJE_FALLIDO']:
                        break
                else:
                    logger.info("No hay viajes en cola para test")

                if ciclo < ciclos_max - 1:
                    logger.info("Pausa entre ciclos de test...")
                    time.sleep(10)

            try:
                stats = obtener_estadisticas_cola()
                logger.info("Estadísticas finales del test:")
                logger.info(f"   Total viajes: {stats.get('total_viajes', 0)}")
                logger.info(f"   Pendientes: {stats.get('pendientes', 0)}")
                logger.info(f"   Procesando: {stats.get('procesando', 0)}")
            except Exception as e:
                logger.warning(f"Error obteniendo estadísticas finales: {e}")

            logger.info("Revisión única de test completada")
            return True

        except Exception as e:
            logger.error(f"Error en revisión única: {e}")
            return False
        finally:
            self.driver_manager.limpiar_driver()
            self.email_client.limpiar_com()

    def mostrar_estadisticas(self):
        """Muestra estadísticas generales del sistema"""
        try:
            stats = viajes_log.obtener_estadisticas()
            logger.info(
                f"Total: {stats['total_viajes']} | "
                f"Exitosos: {stats['exitosos']} | "
                f"Fallidos: {stats['fallidos']}"
            )
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas CSV: {e}")

        try:
            stats_cola = obtener_estadisticas_cola()
            logger.info(
                f"Cola: {stats_cola.get('total_viajes', 0)} viajes | "
                f"Pendientes: {stats_cola.get('pendientes', 0)} | "
                f"Procesando: {stats_cola.get('procesando', 0)}"
            )
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de cola: {e}")


def main():
    """Punto de entrada principal"""
    sistema = AlsuaOrchestrator()

    sistema.mostrar_estadisticas()

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logger.info("MODO PRUEBA: Ejecutando revisión de test...")
        sistema.ejecutar_revision_unica()
    else:
        sistema.ejecutar_bucle_continuo(mostrar_debug=False)


if __name__ == "__main__":
    main()
