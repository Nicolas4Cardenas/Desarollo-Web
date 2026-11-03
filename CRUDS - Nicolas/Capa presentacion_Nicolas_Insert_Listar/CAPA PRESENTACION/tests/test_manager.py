import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from manager import PedidoManager

class FakePedidoDAO:
    def __init__(self): self.calls = 0
    def listar_pendientes(self, db):
        self.calls += 1
        return [{'id_pedido': 7, 'estado': 'PENDIENTE'}]

class FakeDetalleDAO:
    def __init__(self): self.calls = 0; self.ids = None
    def listar_de_pedidos(self, db, ids):
        self.calls += 1; self.ids = ids
        return [{'id_pedido': 7, 'producto': 'Agua', 'cantidad': 2}]

class ManagerTests(unittest.TestCase):
    def test_consulta_dos_daos(self):
        p, d = FakePedidoDAO(), FakeDetalleDAO()
        result = PedidoManager(p, d).consultar_cola(object())
        self.assertEqual(p.calls, 1)
        self.assertEqual(d.calls, 1)
        self.assertEqual(d.ids, [7])
        self.assertEqual(result[0]['productos'][0]['producto'], 'Agua')
    def test_cola_vacia(self):
        class Vacios:
            def listar_pendientes(self, db): return []
        class SinDetalles:
            def listar_de_pedidos(self, db, ids):
                assert ids == []
                return []
        self.assertEqual(PedidoManager(Vacios(), SinDetalles()).consultar_cola(None), [])

if __name__ == '__main__': unittest.main()
