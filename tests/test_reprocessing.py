"""Tests para sistema de reprocesamiento"""
import unittest
import sys
import os
import shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.reprocessing_manager import ReprocessingManager

class TestReprocessing(unittest.TestCase):
    def setUp(self):
        self.test_dir = "data/test_failed_trips"
        self.manager = ReprocessingManager(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_guarda_viaje_fallido(self):
        datos = {
            'prefactura': '1234567',
            'placa_tractor': 'ABC123',
            'fecha': '01/01/2024'
        }

        result = self.manager.save_failed_trip(datos, 'Error de prueba', 'modulo_test')
        self.assertTrue(result)

        trips = self.manager.get_failed_trips()
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0]['prefactura'], '1234567')

    def test_obtiene_viajes_por_estado(self):
        datos = {'prefactura': '1111111'}
        self.manager.save_failed_trip(datos, 'Error 1')

        trips = self.manager.get_failed_trips('pendiente_reproceso')
        self.assertEqual(len(trips), 1)

        trips = self.manager.get_failed_trips('reprocesado_exitoso')
        self.assertEqual(len(trips), 0)

if __name__ == '__main__':
    unittest.main()
