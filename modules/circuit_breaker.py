"""
Circuit Breaker - Detección de patrones de error
Pausa sistema cuando detecta errores recurrentes
"""
import logging
from collections import deque, Counter
from datetime import datetime, timedelta
from modules.config import CIRCUIT_BREAKER_ENABLED, CIRCUIT_BREAKER_MAX_SAME_ERROR, CIRCUIT_BREAKER_MAX_ERROR_RATE

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self):
        self.enabled = CIRCUIT_BREAKER_ENABLED
        self.max_same_error = CIRCUIT_BREAKER_MAX_SAME_ERROR
        self.max_error_rate = CIRCUIT_BREAKER_MAX_ERROR_RATE
        self.recent_errors = deque(maxlen=50)
        self.recent_results = deque(maxlen=20)
        self.is_open = False
        self.opened_at = None

    def record_result(self, success, error_type=None):
        """Registra resultado de procesamiento"""
        if not self.enabled:
            return

        self.recent_results.append('success' if success else 'failed')

        if not success and error_type:
            self.recent_errors.append({
                'type': error_type,
                'timestamp': datetime.now()
            })

        self._check_circuit()

    def _check_circuit(self):
        """Verifica si debe abrir el circuit breaker"""
        if len(self.recent_errors) < self.max_same_error:
            return

        error_counts = Counter([e['type'] for e in self.recent_errors])
        most_common_error, count = error_counts.most_common(1)[0]

        if count >= self.max_same_error:
            self._open_circuit(f"Mismo error {count} veces: {most_common_error}")
            return

        if len(self.recent_results) >= 10:
            failed_count = self.recent_results.count('failed')
            error_rate = failed_count / len(self.recent_results)

            if error_rate > self.max_error_rate:
                self._open_circuit(f"Tasa de error {error_rate*100:.1f}% > {self.max_error_rate*100:.1f}%")

    def _open_circuit(self, reason):
        """Abre el circuito (pausa sistema)"""
        if not self.is_open:
            self.is_open = True
            self.opened_at = datetime.now()
            logger.error(f"⚠️  CIRCUIT BREAKER ABIERTO: {reason}")
            logger.error("Sistema pausado. Revisar errores antes de continuar.")

    def should_process(self):
        """Verifica si debe continuar procesando"""
        return not self.is_open

    def reset(self):
        """Resetea el circuit breaker"""
        self.is_open = False
        self.opened_at = None
        self.recent_errors.clear()
        self.recent_results.clear()
        logger.info("Circuit breaker reseteado")

    def get_status(self):
        """Obtiene estado del circuit breaker"""
        return {
            'enabled': self.enabled,
            'is_open': self.is_open,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'recent_errors_count': len(self.recent_errors),
            'recent_results': list(self.recent_results)
        }

circuit_breaker = CircuitBreaker()
