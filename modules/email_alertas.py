"""
Sistema de Alertas por Email para Robot de Automatización
Envía emails cuando el robot lleva mucho tiempo sin trabajar
"""

import win32com.client
import pythoncom
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EmailAlertas:
    def __init__(self, email_destino="ernestouribe48@gmail.com"):
        self.email_destino = email_destino
        self.ultima_alerta_enviada = None
        self.com_inicializado = False

    def inicializar_com(self):
        """Inicializa COM para Outlook"""
        try:
            if not self.com_inicializado:
                pythoncom.CoInitialize()
                self.com_inicializado = True
                return True
        except Exception as e:
            logger.error(f"Error inicializando COM para email: {e}")
            return False

    def limpiar_com(self):
        """Limpia COM después de enviar"""
        try:
            if self.com_inicializado:
                pythoncom.CoUninitialize()
                self.com_inicializado = False
        except Exception as e:
            logger.warning(f"Error limpiando COM: {e}")

    def enviar_alerta_robot_trabado(self, horas_sin_trabajar, ultimo_viaje_exitoso=None):
        """
        Envía email de alerta cuando el robot lleva mucho tiempo sin trabajar

        Args:
            horas_sin_trabajar: Horas transcurridas sin procesar viajes
            ultimo_viaje_exitoso: Prefactura del último viaje exitoso (opcional)

        Returns:
            bool: True si se envió correctamente
        """
        # Prevenir spam: no enviar más de 1 alerta cada 6 horas
        ahora = datetime.now()
        if self.ultima_alerta_enviada:
            tiempo_desde_ultima = (ahora - self.ultima_alerta_enviada).total_seconds() / 3600
            if tiempo_desde_ultima < 6:
                logger.info(f"Alerta no enviada: última alerta hace {tiempo_desde_ultima:.1f}h")
                return False

        try:
            if not self.inicializar_com():
                logger.error("No se pudo inicializar COM para enviar email")
                return False

            # Crear email usando Outlook
            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)

            # Configurar destinatario
            mail.To = self.email_destino

            # Asunto
            mail.Subject = f"🔴 ALERTA: Robot ALSUA sin trabajar ({int(horas_sin_trabajar)}h)"

            # Cuerpo del mensaje
            cuerpo = f"""
ALERTA AUTOMÁTICA - Robot de Automatización ALSUA

⚠️ El robot lleva {int(horas_sin_trabajar)} horas sin procesar ningún viaje.

DETALLES:
• Fecha/Hora: {ahora.strftime('%d/%m/%Y %H:%M:%S')}
• Tiempo sin trabajar: {int(horas_sin_trabajar)} horas
• Último viaje exitoso: {ultimo_viaje_exitoso or 'Desconocido'}

ACCIONES RECOMENDADAS:
1. Revisar el archivo debug.log para ver errores
2. Verificar que el proceso Python esté corriendo
3. Revisar la cola de viajes (cola_viajes.json)
4. Verificar que haya correos pendientes en Outlook

---
Este es un mensaje automático del sistema de monitoreo del robot.
"""

            mail.Body = cuerpo

            # Enviar
            mail.Send()

            # Registrar envío exitoso
            self.ultima_alerta_enviada = ahora
            logger.info(f"✅ Alerta enviada a {self.email_destino}")

            return True

        except Exception as e:
            logger.error(f"Error enviando alerta por email: {e}")
            return False
        finally:
            self.limpiar_com()

    def enviar_alerta_loop_infinito(self, prefactura, intentos):
        """
        Envía email cuando se detecta un loop infinito

        Args:
            prefactura: Número de prefactura en loop
            intentos: Cantidad de intentos detectados
        """
        # Prevenir spam
        ahora = datetime.now()
        if self.ultima_alerta_enviada:
            tiempo_desde_ultima = (ahora - self.ultima_alerta_enviada).total_seconds() / 3600
            if tiempo_desde_ultima < 1:  # No enviar más de 1 por hora para loops
                return False

        try:
            if not self.inicializar_com():
                return False

            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)

            mail.To = self.email_destino
            mail.Subject = f"🔴 CRÍTICO: Loop infinito detectado - Viaje {prefactura}"

            cuerpo = f"""
ALERTA CRÍTICA - Loop Infinito Detectado

🔴 El robot detectó un loop infinito en el viaje {prefactura}

DETALLES:
• Fecha/Hora: {ahora.strftime('%d/%m/%Y %H:%M:%S')}
• Prefactura: {prefactura}
• Intentos detectados: {intentos} en 5 minutos
• Estado: Viaje marcado como FALLIDO automáticamente

El sistema abortó el viaje automáticamente para prevenir que se trabe.

ACCIÓN REQUERIDA:
Revisar el archivo debug.log para identificar qué causó el problema.

---
Este es un mensaje automático del sistema de monitoreo del robot.
"""

            mail.Body = cuerpo
            mail.Send()

            self.ultima_alerta_enviada = ahora
            logger.info(f"✅ Alerta de loop infinito enviada")

            return True

        except Exception as e:
            logger.error(f"Error enviando alerta de loop: {e}")
            return False
        finally:
            self.limpiar_com()


# Instancia global
email_alertas = EmailAlertas()


def enviar_alerta_robot_trabado(horas_sin_trabajar, ultimo_viaje_exitoso=None):
    """Wrapper para enviar alerta de robot trabado"""
    return email_alertas.enviar_alerta_robot_trabado(horas_sin_trabajar, ultimo_viaje_exitoso)


def enviar_alerta_loop_infinito(prefactura, intentos):
    """Wrapper para enviar alerta de loop infinito"""
    return email_alertas.enviar_alerta_loop_infinito(prefactura, intentos)


if __name__ == "__main__":
    print("Sistema de Alertas por Email")
    print("=" * 60)
    print(f"Email destino: ernestouribe48@gmail.com")
    print("Alertas configuradas:")
    print("  - Robot sin trabajar >15 horas")
    print("  - Loop infinito detectado")
    print("=" * 60)
