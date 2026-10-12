"""Pruebas de HU-01 a HU-05 contra la base poli_restaurante real.

Requisitos: MySQL encendido, backend.sql cargado y el archivo .env configurado.
Ejecutar:  python -m pytest -v
Cada prueba cancela los pedidos que crea para dejar las mesas libres.
"""
import pytest

import servicio
from errores import ErrorNegocio, SIN_CAMBIO

MESERO1, MESERO2, COCINA = 2, 3, 4            # ids de los datos semilla
HAMBURGUESA, GASEOSA, BROWNIE = 3, 5, 8       # brownie viene NO disponible


@pytest.fixture
def pedidos():
    ids = []
    yield ids
    for id_pedido in ids:
        try:
            servicio.cancelar_pedido(MESERO1, id_pedido)
        except ErrorNegocio:
            pass


def codigo(excepcion):
    return excepcion.value.codigo


def nuevo(pedidos, mesero=MESERO1):
    mesa = servicio.listar_mesas_libres(MESERO1)[0]
    id_pedido = servicio.crear_pedido(mesero, mesa["id_mesa"])
    pedidos.append(id_pedido)
    return id_pedido


def con_producto(pedidos, producto=HAMBURGUESA, cantidad=2, notas=None):
    id_pedido = nuevo(pedidos)
    r = servicio.agregar_producto(MESERO1, id_pedido, producto, cantidad, notas)
    return id_pedido, r["id_detalle"]


def listo(id_pedido):
    servicio.avanzar_cocina(COCINA, id_pedido)
    servicio.avanzar_cocina(COCINA, id_pedido)


# ------------------------------------------------------------------ general
def test_buscar_usuario():
    assert servicio.buscar_usuario("mesero1")["rol"] == "MESERO"
    assert servicio.buscar_usuario("noexiste") is None


def test_rol_incorrecto():
    with pytest.raises(ErrorNegocio) as e:
        servicio.crear_pedido(COCINA, 1)
    assert codigo(e) == "ACCESO_DENEGADO"


# -------------------------------------------------------------- HU-01 crear
def test_hu01_crear_pedido(pedidos):
    mesa = servicio.listar_mesas_libres(MESERO1)[0]
    id_pedido = servicio.crear_pedido(MESERO1, mesa["id_mesa"])
    pedidos.append(id_pedido)
    p = servicio.obtener_pedido(MESERO1, id_pedido)
    assert p["estado"] == "PENDIENTE"
    assert p["fecha_creacion"] is not None
    assert p["mesas"] == [mesa["numero"]] and p["total"] == 0 and p["productos"] == []
    assert mesa["id_mesa"] not in [m["id_mesa"] for m in servicio.listar_mesas_libres(MESERO1)]
    assert [h["estado"] for h in servicio.obtener_historial(MESERO1, id_pedido)] == ["PENDIENTE"]


def test_hu01_mesa_ocupada(pedidos):
    mesa = servicio.listar_mesas_libres(MESERO1)[0]["id_mesa"]
    pedidos.append(servicio.crear_pedido(MESERO1, mesa))
    with pytest.raises(ErrorNegocio) as e:
        servicio.crear_pedido(MESERO2, mesa)
    assert codigo(e) == "MESA_OCUPADA"


def test_hu01_mesa_inexistente():
    with pytest.raises(ErrorNegocio) as e:
        servicio.crear_pedido(MESERO1, 999)
    assert codigo(e) == "MESA_NO_EXISTE"


# ------------------------------------------------------------ HU-02 agregar
def test_hu02_agregar_y_total(pedidos):
    id_pedido = nuevo(pedidos)
    r = servicio.agregar_producto(MESERO1, id_pedido, HAMBURGUESA, 2, "sin cebolla")
    assert r["total"] == 44000
    r = servicio.agregar_producto(MESERO1, id_pedido, GASEOSA, 1)
    assert r["total"] == 48500
    p = servicio.obtener_pedido(MESERO1, id_pedido)
    assert len(p["productos"]) == 2 and p["total"] == 48500
    assert any(d["notas"] == "sin cebolla" for d in p["productos"])


def test_hu02_producto_repetido_suma(pedidos):
    id_pedido, _ = con_producto(pedidos, cantidad=1)
    assert servicio.agregar_producto(MESERO1, id_pedido, HAMBURGUESA, 2)["total"] == 66000


def test_hu02_errores(pedidos):
    id_pedido = nuevo(pedidos)
    casos = [
        ((MESERO1, id_pedido, HAMBURGUESA, 0), "CANTIDAD_INVALIDA"),
        ((MESERO1, id_pedido, 999, 1), "PRODUCTO_NO_EXISTE"),
        ((MESERO1, id_pedido, BROWNIE, 1), "PRODUCTO_NO_DISPONIBLE"),
        ((MESERO2, id_pedido, HAMBURGUESA, 1), "ACCESO_DENEGADO"),
        ((MESERO1, 99999, HAMBURGUESA, 1), "PEDIDO_NO_EXISTE"),
    ]
    for args, esperado in casos:
        with pytest.raises(ErrorNegocio) as e:
            servicio.agregar_producto(*args)
        assert codigo(e) == esperado


# ------------------------------------------------- HU-03 editar / quitar
def test_hu03_editar_y_conservar_notas(pedidos):
    id_pedido, id_detalle = con_producto(pedidos, notas="sin cebolla")
    r = servicio.modificar_detalle(MESERO1, id_pedido, id_detalle, 3)
    assert r["total"] == 66000
    d = servicio.obtener_pedido(MESERO1, id_pedido)["productos"][0]
    assert d["cantidad"] == 3 and d["notas"] == "sin cebolla"
    servicio.modificar_detalle(MESERO1, id_pedido, id_detalle, 1, "bien cocida")
    assert servicio.obtener_pedido(MESERO1, id_pedido)["productos"][0]["notas"] == "bien cocida"
    servicio.modificar_detalle(MESERO1, id_pedido, id_detalle, 1, None)       # None = borrar notas
    assert servicio.obtener_pedido(MESERO1, id_pedido)["productos"][0]["notas"] is None
    servicio.modificar_detalle(MESERO1, id_pedido, id_detalle, 2, SIN_CAMBIO)


def test_hu03_quitar(pedidos):
    id_pedido, id_detalle = con_producto(pedidos)
    assert servicio.quitar_producto(MESERO1, id_pedido, id_detalle)["total"] == 0
    assert servicio.obtener_pedido(MESERO1, id_pedido)["productos"] == []


def test_hu03_bloqueado_fuera_de_pendiente(pedidos):
    id_pedido, id_detalle = con_producto(pedidos)
    servicio.avanzar_cocina(COCINA, id_pedido)                                # EN_PREPARACION
    with pytest.raises(ErrorNegocio) as e:
        servicio.modificar_detalle(MESERO1, id_pedido, id_detalle, 5)
    assert codigo(e) == "PEDIDO_BLOQUEADO"
    with pytest.raises(ErrorNegocio) as e:
        servicio.quitar_producto(MESERO1, id_pedido, id_detalle)
    assert codigo(e) == "PEDIDO_BLOQUEADO"
    with pytest.raises(ErrorNegocio) as e:
        servicio.agregar_producto(MESERO1, id_pedido, GASEOSA, 1)
    assert codigo(e) == "PEDIDO_BLOQUEADO"


def test_hu03_detalle_de_otro_pedido(pedidos):
    id_a, _ = con_producto(pedidos)
    _, detalle_b = con_producto(pedidos)
    with pytest.raises(ErrorNegocio) as e:
        servicio.modificar_detalle(MESERO1, id_a, detalle_b, 1)
    assert codigo(e) == "DETALLE_NO_EXISTE"


# ------------------------------------------------------------ HU-04 entregar
def test_hu04_solo_si_esta_listo(pedidos):
    id_pedido, _ = con_producto(pedidos)
    with pytest.raises(ErrorNegocio) as e:
        servicio.marcar_entregado(MESERO1, id_pedido)
    assert codigo(e) == "TRANSICION_INVALIDA"
    listo(id_pedido)
    servicio.marcar_entregado(MESERO1, id_pedido)
    assert servicio.obtener_pedido(MESERO1, id_pedido)["estado"] == "ENTREGADO"


def test_hu04_libera_la_mesa_e_historial(pedidos):
    id_pedido, _ = con_producto(pedidos)
    numero = servicio.obtener_pedido(MESERO1, id_pedido)["mesas"][0]
    listo(id_pedido)
    servicio.marcar_entregado(MESERO1, id_pedido)
    assert numero in [m["numero"] for m in servicio.listar_mesas_libres(MESERO1)]
    estados = [h["estado"] for h in servicio.obtener_historial(MESERO1, id_pedido)]
    assert estados == ["PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO"]


def test_hu04_ajeno_o_inexistente(pedidos):
    id_pedido, _ = con_producto(pedidos)
    for mesero, pid, esperado in [(MESERO2, id_pedido, "ACCESO_DENEGADO"), (MESERO1, 99999, "PEDIDO_NO_EXISTE")]:
        with pytest.raises(ErrorNegocio) as e:
            servicio.marcar_entregado(mesero, pid)
        assert codigo(e) == esperado


# ------------------------------------------------------------ HU-05 cancelar
def test_hu05_cancelar_pendiente_registra_quien(pedidos):
    id_pedido, _ = con_producto(pedidos)
    numero = servicio.obtener_pedido(MESERO1, id_pedido)["mesas"][0]
    servicio.cancelar_pedido(MESERO1, id_pedido)
    assert servicio.obtener_pedido(MESERO1, id_pedido)["estado"] == "CANCELADO"
    ultimo = servicio.obtener_historial(MESERO1, id_pedido)[-1]
    assert ultimo["estado"] == "CANCELADO" and ultimo["usuario"] == "Mesero Uno"
    assert numero in [m["numero"] for m in servicio.listar_mesas_libres(MESERO1)]


@pytest.mark.parametrize("avances", [1, 2])
def test_hu05_cancelar_en_preparacion_o_listo(pedidos, avances):
    id_pedido, _ = con_producto(pedidos)
    for _ in range(avances):
        servicio.avanzar_cocina(COCINA, id_pedido)
    servicio.cancelar_pedido(MESERO1, id_pedido)                              # HU-05: todo lo no entregado
    assert servicio.obtener_pedido(MESERO1, id_pedido)["estado"] == "CANCELADO"


def test_hu05_no_se_cancela_entregado(pedidos):
    id_pedido, _ = con_producto(pedidos)
    listo(id_pedido)
    servicio.marcar_entregado(MESERO1, id_pedido)
    with pytest.raises(ErrorNegocio) as e:
        servicio.cancelar_pedido(MESERO1, id_pedido)
    assert codigo(e) == "CANCELACION_NO_PERMITIDA"


def test_hu05_doble_cancelacion_ajeno_inexistente(pedidos):
    id_pedido, _ = con_producto(pedidos)
    with pytest.raises(ErrorNegocio) as e:
        servicio.cancelar_pedido(MESERO2, id_pedido)
    assert codigo(e) == "ACCESO_DENEGADO"
    servicio.cancelar_pedido(MESERO1, id_pedido)
    with pytest.raises(ErrorNegocio) as e:
        servicio.cancelar_pedido(MESERO1, id_pedido)
    assert codigo(e) == "TRANSICION_INVALIDA"
    with pytest.raises(ErrorNegocio) as e:
        servicio.cancelar_pedido(MESERO1, 99999)
    assert codigo(e) == "PEDIDO_NO_EXISTE"


# ------------------------------------------------------------------ consultas
def test_listar_filtrar_y_menu(pedidos):
    id_pedido, _ = con_producto(pedidos)
    assert id_pedido in [p["id_pedido"] for p in servicio.listar_pedidos(MESERO1)]
    assert all(p["estado"] == "PENDIENTE" for p in servicio.listar_pedidos(MESERO1, "PENDIENTE"))
    assert all(p["id_pedido"] != id_pedido for p in servicio.listar_pedidos(MESERO2))
    menu = servicio.listar_menu(MESERO1)
    assert menu and all(m["nombre"] != "Brownie" for m in menu)               # no disponible
