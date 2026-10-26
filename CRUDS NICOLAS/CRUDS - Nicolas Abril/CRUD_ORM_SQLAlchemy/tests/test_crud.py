"""Pruebas de HU-06, 07, 08, 13, 14 y 15 contra la base real poli_restaurante_nicolas.

Requisitos: MySQL encendido, backend_nicolas.sql cargado y el archivo .env configurado.
Ejecutar:  python -m pytest -v
Cada prueba deja sus pedidos ENTREGADOS o CANCELADOS (mesas libres), pero crea datos reales:
al terminar conviene volver a ejecutar backend_nicolas.sql para dejar la base limpia.
"""
import pytest

import servicio
from errores import ErrorNegocio, SIN_CAMBIO

ADMIN, MESERO, MESERO2, COCINA = 1, 2, 3, 4      # ids de los datos semilla
HAMBURGUESA, GASEOSA = 3, 5
DESDE, HASTA = "2020-01-01", "2099-12-31"


@pytest.fixture
def pedidos():
    ids = []
    yield ids
    for id_pedido in ids:                          # deja las mesas libres
        for accion in (servicio.cancelar_pedido, servicio.marcar_entregado):
            try:
                accion(MESERO, id_pedido)
                break
            except ErrorNegocio:
                pass


def codigo(excepcion):
    return excepcion.value.codigo


def nuevo(pedidos, productos=((HAMBURGUESA, 2), (GASEOSA, 1))):
    mesa = servicio.listar_mesas_libres(MESERO)[0]
    id_pedido = servicio.crear_pedido(MESERO, mesa["id_mesa"])
    pedidos.append(id_pedido)
    for id_producto, cantidad in productos:
        servicio.agregar_producto(MESERO, id_pedido, id_producto, cantidad)
    return id_pedido


def entregado(pedidos):
    id_pedido = nuevo(pedidos)
    servicio.iniciar_preparacion(COCINA, id_pedido)
    servicio.marcar_listo(COCINA, id_pedido)
    servicio.marcar_entregado(MESERO, id_pedido)
    return id_pedido


def estado_de(id_pedido):
    return servicio.obtener_pedido(ADMIN, id_pedido)["estado"]


# ------------------------------------------------------------------ general
def test_buscar_usuario():
    assert servicio.buscar_usuario("cocina1")["rol"] == "COCINA"
    assert servicio.buscar_usuario("admin")["rol"] == "ADMINISTRADOR"
    assert servicio.buscar_usuario("noexiste") is None


# -------------------------------------------------------------- HU-06 cola
def test_hu06_cola_con_pedido_y_productos(pedidos):
    id_pedido = nuevo(pedidos)
    mio = [p for p in servicio.ver_cola(COCINA) if p["id_pedido"] == id_pedido]
    assert len(mio) == 1 and len(mio[0]["productos"]) == 2 and len(mio[0]["mesas"]) == 1


def test_hu06_pedido_vacio_no_aparece(pedidos):
    id_pedido = nuevo(pedidos, productos=())
    assert id_pedido not in [p["id_pedido"] for p in servicio.ver_cola(COCINA)]


def test_hu06_orden_del_mas_antiguo_al_mas_reciente(pedidos):
    a, b = nuevo(pedidos), nuevo(pedidos)
    ids = [p["id_pedido"] for p in servicio.ver_cola(COCINA) if p["id_pedido"] in (a, b)]
    assert ids == [a, b]


def test_hu06_rol_incorrecto():
    with pytest.raises(ErrorNegocio) as e:
        servicio.ver_cola(MESERO)
    assert codigo(e) == "ACCESO_DENEGADO"


# ------------------------------------------------------ HU-07 preparación
def test_hu07_preparar(pedidos):
    id_pedido = nuevo(pedidos)
    servicio.iniciar_preparacion(COCINA, id_pedido)
    assert estado_de(id_pedido) == "EN_PREPARACION"
    assert id_pedido in [p["id_pedido"] for p in servicio.ver_en_preparacion(COCINA)]
    assert id_pedido not in [p["id_pedido"] for p in servicio.ver_cola(COCINA)]


def test_hu07_registra_historial(pedidos):
    id_pedido = nuevo(pedidos)
    servicio.iniciar_preparacion(COCINA, id_pedido)
    h = servicio.listar_historial(ADMIN, id_pedido)
    assert [x["estado"] for x in h] == ["PENDIENTE", "EN_PREPARACION"]
    assert h[-1]["id_usuario_cambio"] == COCINA


def test_hu07_pedido_vacio(pedidos):
    id_pedido = nuevo(pedidos, productos=())
    with pytest.raises(ErrorNegocio) as e:
        servicio.iniciar_preparacion(COCINA, id_pedido)
    assert codigo(e) == "PEDIDO_VACIO"


def test_hu07_transicion_invalida(pedidos):
    id_pedido = nuevo(pedidos)
    servicio.iniciar_preparacion(COCINA, id_pedido)
    with pytest.raises(ErrorNegocio) as e:
        servicio.iniciar_preparacion(COCINA, id_pedido)
    assert codigo(e) == "TRANSICION_INVALIDA"


def test_hu07_pedido_inexistente():
    with pytest.raises(ErrorNegocio) as e:
        servicio.iniciar_preparacion(COCINA, 999999)
    assert codigo(e) == "PEDIDO_NO_EXISTE"


def test_hu07_rol_incorrecto(pedidos):
    id_pedido = nuevo(pedidos)
    with pytest.raises(ErrorNegocio) as e:
        servicio.iniciar_preparacion(MESERO, id_pedido)
    assert codigo(e) == "ACCESO_DENEGADO"


def test_admin_puede_operar_cocina_y_mesero(pedidos):
    """El administrador puede hacer todo, incluso sobre pedidos de otro mesero."""
    id_pedido = nuevo(pedidos, productos=())
    servicio.agregar_producto(ADMIN, id_pedido, HAMBURGUESA, 1)
    servicio.iniciar_preparacion(ADMIN, id_pedido)
    servicio.marcar_listo(ADMIN, id_pedido)
    servicio.marcar_entregado(ADMIN, id_pedido)
    assert estado_de(id_pedido) == "ENTREGADO"
    assert servicio.ver_cola(ADMIN) is not None


def test_mesero_no_opera_pedido_de_otro_mesero(pedidos):
    id_pedido = nuevo(pedidos)
    with pytest.raises(ErrorNegocio) as e:
        servicio.cancelar_pedido(MESERO2, id_pedido)
    assert codigo(e) == "ACCESO_DENEGADO"


# ---------------------------------------------------------------- HU-08 listo
def test_hu08_listo(pedidos):
    id_pedido = nuevo(pedidos)
    servicio.iniciar_preparacion(COCINA, id_pedido)
    servicio.marcar_listo(COCINA, id_pedido)
    assert estado_de(id_pedido) == "LISTO"


def test_hu08_sin_preparar(pedidos):
    id_pedido = nuevo(pedidos)
    with pytest.raises(ErrorNegocio) as e:
        servicio.marcar_listo(COCINA, id_pedido)
    assert codigo(e) == "TRANSICION_INVALIDA"


def test_hu08_listo_dos_veces(pedidos):
    id_pedido = nuevo(pedidos)
    servicio.iniciar_preparacion(COCINA, id_pedido)
    servicio.marcar_listo(COCINA, id_pedido)
    with pytest.raises(ErrorNegocio) as e:
        servicio.marcar_listo(COCINA, id_pedido)
    assert codigo(e) == "TRANSICION_INVALIDA"


# ------------------------------------------------------------ HU-13 ventas
def test_hu13_ventas_suma_pedido_entregado(pedidos):
    antes = servicio.reporte_ventas(ADMIN, DESDE, HASTA)["resumen"]
    entregado(pedidos)                                # 2 x 22000 + 1 x 4500 = 48500
    despues = servicio.reporte_ventas(ADMIN, DESDE, HASTA)["resumen"]
    assert despues["pedidos_entregados"] == antes["pedidos_entregados"] + 1
    assert despues["productos_vendidos"] == antes["productos_vendidos"] + 3
    assert despues["total_ventas"] - antes["total_ventas"] == 48500


def test_hu13_filtros(pedidos):
    entregado(pedidos)
    por_producto = servicio.reporte_ventas(ADMIN, DESDE, HASTA, id_producto=GASEOSA)["por_producto"]
    assert por_producto and all(p["producto"] == "Gaseosa" for p in por_producto)
    por_categoria = servicio.reporte_ventas(ADMIN, DESDE, HASTA, id_categoria=2)["por_categoria"]
    assert por_categoria and all(c["categoria"] == "Platos fuertes" for c in por_categoria)


def test_hu13_pedido_cancelado_no_cuenta(pedidos):
    antes = servicio.reporte_ventas(ADMIN, DESDE, HASTA)["resumen"]["pedidos_entregados"]
    id_pedido = nuevo(pedidos)
    servicio.cancelar_pedido(MESERO, id_pedido)
    assert servicio.reporte_ventas(ADMIN, DESDE, HASTA)["resumen"]["pedidos_entregados"] == antes


def test_hu13_rango_y_fechas_invalidas():
    with pytest.raises(ErrorNegocio) as e:
        servicio.reporte_ventas(ADMIN, "2026-12-31", "2026-01-01")
    assert codigo(e) == "RANGO_INVALIDO"
    with pytest.raises(ErrorNegocio) as e:
        servicio.reporte_ventas(ADMIN, "hoy", HASTA)
    assert codigo(e) == "FECHA_INVALIDA"


def test_hu13_rol_incorrecto():
    with pytest.raises(ErrorNegocio) as e:
        servicio.reporte_ventas(COCINA, DESDE, HASTA)
    assert codigo(e) == "ACCESO_DENEGADO"


# ----------------------------------------------------------- HU-14 tiempos
def test_hu14_tiempos_incluye_pedido(pedidos):
    id_pedido = entregado(pedidos)
    r = servicio.reporte_tiempos(ADMIN, DESDE, HASTA)
    fila = [f for f in r["detalle"] if f["id_pedido"] == id_pedido]
    assert len(fila) == 1 and fila[0]["min_total"] is not None and fila[0]["min_total"] >= 0
    assert r["promedios"]["pedidos_preparados"] >= 1


def test_hu14_rango_invalido_y_rol():
    with pytest.raises(ErrorNegocio) as e:
        servicio.reporte_tiempos(ADMIN, "2026-12-31", "2026-01-01")
    assert codigo(e) == "RANGO_INVALIDO"
    with pytest.raises(ErrorNegocio) as e:
        servicio.reporte_tiempos(MESERO, DESDE, HASTA)
    assert codigo(e) == "ACCESO_DENEGADO"


# ---------------------------------------------------------- HU-15 historial
def test_hu15_listar_por_pedido(pedidos):
    id_pedido = entregado(pedidos)
    assert [h["estado"] for h in servicio.listar_historial(ADMIN, id_pedido)] == [
        "PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO"]


def test_hu15_crud_completo(pedidos):
    id_pedido = nuevo(pedidos)
    # CREATE
    id_hist = servicio.crear_historial(ADMIN, id_pedido, "listo", "2026-01-01 08:00:00")
    # READ
    h = servicio.obtener_historial(ADMIN, id_hist)
    assert h["estado"] == "LISTO" and h["id_usuario_cambio"] == ADMIN and h["rol"] == "ADMINISTRADOR"
    # UPDATE (solo estado: lo demás se conserva)
    servicio.editar_historial(ADMIN, id_hist, estado="CANCELADO")
    h = servicio.obtener_historial(ADMIN, id_hist)
    assert h["estado"] == "CANCELADO" and h["fecha"].strftime("%Y-%m-%d %H:%M:%S") == "2026-01-01 08:00:00"
    # UPDATE (fecha y usuario)
    servicio.editar_historial(ADMIN, id_hist, fecha="2026-01-02 09:30:00", id_usuario_cambio=COCINA)
    h = servicio.obtener_historial(ADMIN, id_hist)
    assert h["fecha"].strftime("%Y-%m-%d %H:%M:%S") == "2026-01-02 09:30:00" and h["id_usuario_cambio"] == COCINA
    # DELETE
    servicio.eliminar_historial(ADMIN, id_hist)
    with pytest.raises(ErrorNegocio) as e:
        servicio.obtener_historial(ADMIN, id_hist)
    assert codigo(e) == "HISTORIAL_NO_EXISTE"


def test_hu15_errores_al_crear(pedidos):
    id_pedido = nuevo(pedidos)
    with pytest.raises(ErrorNegocio) as e:
        servicio.crear_historial(ADMIN, id_pedido, "XYZ")
    assert codigo(e) == "ESTADO_INVALIDO"
    with pytest.raises(ErrorNegocio) as e:
        servicio.crear_historial(ADMIN, 999999, "LISTO")
    assert codigo(e) == "PEDIDO_NO_EXISTE"
    with pytest.raises(ErrorNegocio) as e:
        servicio.crear_historial(ADMIN, id_pedido, "LISTO", "ayer")
    assert codigo(e) == "FECHA_INVALIDA"
    with pytest.raises(ErrorNegocio) as e:
        servicio.crear_historial(ADMIN, id_pedido, "LISTO", id_usuario_cambio=999999)
    assert codigo(e) == "USUARIO_NO_EXISTE"


def test_hu15_editar_y_eliminar_inexistentes():
    with pytest.raises(ErrorNegocio) as e:
        servicio.editar_historial(ADMIN, 999999, estado="LISTO")
    assert codigo(e) == "HISTORIAL_NO_EXISTE"
    with pytest.raises(ErrorNegocio) as e:
        servicio.eliminar_historial(ADMIN, 999999)
    assert codigo(e) == "HISTORIAL_NO_EXISTE"
    with pytest.raises(ErrorNegocio) as e:
        servicio.editar_historial(ADMIN, 1)             # sin ningún campo
    assert codigo(e) == "CAMPO_REQUERIDO"


def test_hu15_rol_incorrecto():
    with pytest.raises(ErrorNegocio) as e:
        servicio.listar_historial(COCINA)
    assert codigo(e) == "ACCESO_DENEGADO"
