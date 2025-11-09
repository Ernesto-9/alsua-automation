"""Tests para circuit breaker"""
import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.circuit_breaker import CircuitBreaker

class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.cb = CircuitBreaker()
        self.cb.reset()

    def test_inicia_cerrado(self):
        self.assertFalse(self.cb.is_open)
        self.assertTrue(self.cb.should_process())

    def test_abre_con_mismo_error_repetido(self):
        for i in range(15):
            self.cb.record_result(False, 'MISMO_ERROR')

        self.assertTrue(self.cb.is_open)
        self.assertFalse(self.cb.should_process())

    def test_no_abre_con_errores_diferentes(self):
        for i in range(15):
            self.cb.record_result(False, f'ERROR_{i}')

        self.assertFalse(self.cb.is_open)

    def test_reset_funciona(self):
        for i in range(15):
            self.cb.record_result(False, 'ERROR')

        self.assertTrue(self.cb.is_open)

        self.cb.reset()

        self.assertFalse(self.cb.is_open)
        self.assertTrue(self.cb.should_process())

if __name__ == '__main__':
    unittest.main()
