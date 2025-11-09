"""Tests para validador de viajes"""
import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.trip_validator import TripValidator

class TestTripValidator(unittest.TestCase):
    def setUp(self):
        self.validator = TripValidator()

    def test_prefactura_valida(self):
        datos = {
            'prefactura': '1234567',
            'placa_tractor': 'ABC123',
            'placa_remolque': 'DEF456',
            'importe': '1000.50',
            'clave_determinante': '1234',
            'fecha': '01/01/2024',
            'cliente_codigo': 'CLI001'
        }
        is_valid, errors = self.validator.validate_trip(datos)
        self.assertTrue(len(errors) == 0 or 'Determinante' in str(errors))

    def test_prefactura_invalida(self):
        datos = {
            'prefactura': '123',
            'placa_tractor': 'ABC123',
            'placa_remolque': 'DEF456',
            'importe': '1000',
            'clave_determinante': '1234',
            'fecha': '01/01/2024',
            'cliente_codigo': 'CLI001'
        }
        is_valid, errors = self.validator.validate_trip(datos)
        self.assertFalse(is_valid)
        self.assertTrue(any('Prefactura' in e for e in errors))

    def test_importe_invalido(self):
        datos = {
            'prefactura': '1234567',
            'placa_tractor': 'ABC123',
            'placa_remolque': 'DEF456',
            'importe': 'ABC',
            'clave_determinante': '1234',
            'fecha': '01/01/2024',
            'cliente_codigo': 'CLI001'
        }
        is_valid, errors = self.validator.validate_trip(datos)
        self.assertFalse(is_valid)
        self.assertTrue(any('Importe' in e for e in errors))

if __name__ == '__main__':
    unittest.main()
