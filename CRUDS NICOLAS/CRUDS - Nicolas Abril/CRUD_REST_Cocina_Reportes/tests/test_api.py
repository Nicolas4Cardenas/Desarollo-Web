"""Pruebas automáticas del servicio REST contra la base REAL (poli_restaurante_nicolas).

Requisitos: MySQL encendido, backend_nicolas.sql cargado y el archivo .env configurado.
Ejecutar:  pytest -v
Cada prueba deja los pedidos que crea ENTREGADOS o CANCELADOS (las mesas quedan libres).
Los pedidos se acumulan en la base: para dejarla limpia, vuelve a ejecutar backend_nicolas.sql.
"""
import pytest

from api import crear_app
from api.dao import comun

ADMIN, MESERO, MESERO2, COCINA = 1, 2, 3, 4      # ids de los datos semilla
HAMBURGUESA, GASEOSA = 3, 5
DESDE, HASTA = "2020-01-01", "2099-12-31"
URL = "/api/v1"


def h(usuario):
    return {"X-Usuario-Id": str(usuario)}


@pytest.fixture
def client():
    return crear_app().test_client()


@pytest.fixture
def pedidos(client):
    """Lista de pedidos creados por la prueba; al terminar se cierran para liberar las mesas."""
    ids = []
    yield ids
    for id_pedido in ids:
        estado = comun.estado_pedido(id_pedido)
        if estado in ("PENDIENTE", "EN_PREPARACION"):
            client.delete(f"{URL}/pedidos/{id_pedido}", headers=h(MESERO))
        elif estado == "LISTO":
            client.put(f"{URL}/pedidos/{id_pedido}/entregar", headers=h(MESERO))


# ------------------------------------------------------------------ ayudas
def nuevo_pedido(client, pedidos, productos=((HAMBURGUESA, 2), (GASEOSA, 1))):
    mesas = client.get(f"{URL}/mesas/libres", headers=h(MESERO)).get_json()
    r = client.post(f"{URL}/pedidos", json={"id_mesa": mesas[0]["id_mesa"]}, headers=h(MESERO))
    assert r.status_code == 201
    id_pedido = r.get_json()["id_pedido"]
    pedidos.append(id_pedido)
    for id_producto, cantidad in productos:
        r = client.post(f"{URL}/pedidos/{id_pedido}/productos",
                        json={"id_producto": id_producto, "cantidad": cantidad}, headers=h(MESERO))
        assert r.status_code == 201
    return id_pedido


def preparar(client, id_pedido):
    return client.put(f"{URL}/cocina/pedidos/{id_pedido}/preparar", headers=h(COCINA))


def listo(client, id_pedido):
    return client.put(f"{URL}/cocina/pedidos/{id_pedido}/listo", headers=h(COCINA))


def entregar(client, id_pedido):
    return client.put(f"{URL}/pedidos/{id_pedido}/entregar", headers=h(MESERO))


def entregado(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    assert preparar(client, id_pedido).status_code == 200
    assert listo(client, id_pedido).status_code == 200
    assert entregar(client, id_pedido).status_code == 200
    return id_pedido


def codigo(r):
    return r.get_json()["codigo"]


# ----------------------------------------------------------------- general
def test_salud(client):
    r = client.get(f"{URL}/salud")
    assert r.status_code == 200 and r.get_json()["estado"] == "ok"


def test_sin_cabecera_401(client):
    r = client.get(f"{URL}/cocina/cola")
    assert r.status_code == 401 and codigo(r) == "NO_AUTENTICADO"


# ------------------------------------------------------------- HU-06 cola
def test_hu06_cola_con_pedido_y_productos(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    r = client.get(f"{URL}/cocina/cola", headers=h(COCINA))
    assert r.status_code == 200
    mio = [p for p in r.get_json()["pedidos"] if p["id_pedido"] == id_pedido]
    assert len(mio) == 1 and len(mio[0]["productos"]) == 2 and len(mio[0]["mesas"]) == 1


def test_hu06_pedido_vacio_no_aparece(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos, productos=())
    ids = [p["id_pedido"] for p in client.get(f"{URL}/cocina/cola", headers=h(COCINA)).get_json()["pedidos"]]
    assert id_pedido not in ids


def test_hu06_rol_incorrecto(client):
    r = client.get(f"{URL}/cocina/cola", headers=h(MESERO))
    assert r.status_code == 403 and codigo(r) == "ACCESO_DENEGADO"


# -------------------------------------------------------- HU-07 preparación
def test_hu07_preparar(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    r = preparar(client, id_pedido)
    assert r.status_code == 200 and r.get_json()["estado"] == "EN_PREPARACION"
    ids = [p["id_pedido"] for p in client.get(f"{URL}/cocina/en-preparacion", headers=h(COCINA)).get_json()["pedidos"]]
    assert id_pedido in ids


def test_hu07_sale_de_la_cola(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    preparar(client, id_pedido)
    ids = [p["id_pedido"] for p in client.get(f"{URL}/cocina/cola", headers=h(COCINA)).get_json()["pedidos"]]
    assert id_pedido not in ids


def test_hu07_pedido_vacio(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos, productos=())
    r = preparar(client, id_pedido)
    assert r.status_code == 409 and codigo(r) == "PEDIDO_VACIO"


def test_hu07_transicion_invalida(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    preparar(client, id_pedido)
    r = preparar(client, id_pedido)
    assert r.status_code == 409 and codigo(r) == "TRANSICION_INVALIDA"


def test_hu07_pedido_inexistente(client):
    r = preparar(client, 999999)
    assert r.status_code == 404 and codigo(r) == "PEDIDO_NO_EXISTE"


def test_hu07_rol_incorrecto(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    r = client.put(f"{URL}/cocina/pedidos/{id_pedido}/preparar", headers=h(MESERO))
    assert r.status_code == 403 and codigo(r) == "ACCESO_DENEGADO"


def test_admin_puede_operar_cocina_y_mesero(client, pedidos):
    """El administrador puede hacer todo, incluso sobre pedidos de otro mesero."""
    id_pedido = nuevo_pedido(client, pedidos, productos=())
    r = client.post(f"{URL}/pedidos/{id_pedido}/productos", headers=h(ADMIN),
                    json={"id_producto": HAMBURGUESA, "cantidad": 1})
    assert r.status_code == 201
    assert client.put(f"{URL}/cocina/pedidos/{id_pedido}/preparar", headers=h(ADMIN)).status_code == 200
    assert client.put(f"{URL}/cocina/pedidos/{id_pedido}/listo", headers=h(ADMIN)).status_code == 200
    assert client.put(f"{URL}/pedidos/{id_pedido}/entregar", headers=h(ADMIN)).status_code == 200
    assert client.get(f"{URL}/cocina/cola", headers=h(ADMIN)).status_code == 200


def test_mesero_no_opera_pedido_de_otro_mesero(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    r = client.delete(f"{URL}/pedidos/{id_pedido}", headers=h(MESERO2))
    assert r.status_code == 403 and codigo(r) == "ACCESO_DENEGADO"


# --------------------------------------------------------------- HU-08 listo
def test_hu08_listo(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    preparar(client, id_pedido)
    r = listo(client, id_pedido)
    assert r.status_code == 200 and r.get_json()["estado"] == "LISTO"


def test_hu08_sin_preparar(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    r = listo(client, id_pedido)
    assert r.status_code == 409 and codigo(r) == "TRANSICION_INVALIDA"


def test_hu08_listo_dos_veces(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    preparar(client, id_pedido)
    listo(client, id_pedido)
    r = listo(client, id_pedido)
    assert r.status_code == 409 and codigo(r) == "TRANSICION_INVALIDA"


# ------------------------------------------------------- HU-13 ventas
def _ventas(client, extra=""):
    r = client.get(f"{URL}/reportes/ventas?desde={DESDE}&hasta={HASTA}{extra}", headers=h(ADMIN))
    assert r.status_code == 200
    return r.get_json()


def test_hu13_ventas_suma_pedido_entregado(client, pedidos):
    antes = _ventas(client)["resumen"]
    entregado(client, pedidos)                       # 2 x 22000 + 1 x 4500 = 48500
    despues = _ventas(client)["resumen"]
    assert despues["pedidos_entregados"] == antes["pedidos_entregados"] + 1
    assert despues["productos_vendidos"] == antes["productos_vendidos"] + 3
    assert round(despues["total_ventas"] - antes["total_ventas"], 2) == 48500


def test_hu13_filtro_por_producto(client, pedidos):
    entregado(client, pedidos)
    r = _ventas(client, f"&id_producto={GASEOSA}")
    assert r["por_producto"] and all(p["producto"] == "Gaseosa" for p in r["por_producto"])


def test_hu13_rango_invalido(client):
    r = client.get(f"{URL}/reportes/ventas?desde=2026-12-31&hasta=2026-01-01", headers=h(ADMIN))
    assert r.status_code == 400 and codigo(r) == "RANGO_INVALIDO"


def test_hu13_fecha_invalida_y_faltante(client):
    r = client.get(f"{URL}/reportes/ventas?desde=hoy&hasta={HASTA}", headers=h(ADMIN))
    assert r.status_code == 400 and codigo(r) == "FECHA_INVALIDA"
    r = client.get(f"{URL}/reportes/ventas?desde={DESDE}", headers=h(ADMIN))
    assert r.status_code == 400 and codigo(r) == "CAMPO_REQUERIDO"


def test_hu13_rol_incorrecto(client):
    r = client.get(f"{URL}/reportes/ventas?desde={DESDE}&hasta={HASTA}", headers=h(COCINA))
    assert r.status_code == 403 and codigo(r) == "ACCESO_DENEGADO"


# ------------------------------------------------------- HU-14 tiempos
def test_hu14_tiempos_incluye_pedido(client, pedidos):
    id_pedido = entregado(client, pedidos)
    r = client.get(f"{URL}/reportes/tiempos?desde={DESDE}&hasta={HASTA}", headers=h(ADMIN))
    assert r.status_code == 200
    datos = r.get_json()
    fila = [d for d in datos["detalle"] if d["id_pedido"] == id_pedido]
    assert len(fila) == 1 and fila[0]["min_total"] is not None
    assert datos["promedios"]["pedidos_preparados"] >= 1


def test_hu14_rango_invalido(client):
    r = client.get(f"{URL}/reportes/tiempos?desde=2026-12-31&hasta=2026-01-01", headers=h(ADMIN))
    assert r.status_code == 400 and codigo(r) == "RANGO_INVALIDO"


# ------------------------------------------------------- HU-15 historial
def test_hu15_listar_por_pedido(client, pedidos):
    id_pedido = entregado(client, pedidos)
    r = client.get(f"{URL}/historial?id_pedido={id_pedido}", headers=h(ADMIN))
    assert r.status_code == 200
    assert [x["estado"] for x in r.get_json()["historial"]] == [
        "PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO"]


def test_hu15_crud_completo(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    # CREATE
    r = client.post(f"{URL}/historial", headers=h(ADMIN),
                    json={"id_pedido": id_pedido, "estado": "LISTO", "fecha": "2026-01-01 08:00:00"})
    assert r.status_code == 201 and "Location" in r.headers
    id_hist = r.get_json()["registro"]["id_historial"]
    # READ
    r = client.get(f"{URL}/historial/{id_hist}", headers=h(ADMIN))
    assert r.status_code == 200 and r.get_json()["estado"] == "LISTO"
    # UPDATE
    r = client.put(f"{URL}/historial/{id_hist}", headers=h(ADMIN), json={"estado": "CANCELADO"})
    assert r.status_code == 200 and r.get_json()["registro"]["estado"] == "CANCELADO"
    assert r.get_json()["registro"]["fecha"] == "2026-01-01 08:00:00"      # lo no enviado se conserva
    # DELETE
    r = client.delete(f"{URL}/historial/{id_hist}", headers=h(ADMIN))
    assert r.status_code == 200
    r = client.get(f"{URL}/historial/{id_hist}", headers=h(ADMIN))
    assert r.status_code == 404 and codigo(r) == "HISTORIAL_NO_EXISTE"


def test_hu15_errores_de_entrada(client, pedidos):
    id_pedido = nuevo_pedido(client, pedidos)
    r = client.post(f"{URL}/historial", headers=h(ADMIN), json={"id_pedido": id_pedido, "estado": "XYZ"})
    assert r.status_code == 400 and codigo(r) == "ESTADO_INVALIDO"
    r = client.post(f"{URL}/historial", headers=h(ADMIN), json={"id_pedido": id_pedido})
    assert r.status_code == 400 and codigo(r) == "CAMPO_REQUERIDO"
    r = client.post(f"{URL}/historial", headers=h(ADMIN), json={"id_pedido": 999999, "estado": "LISTO"})
    assert r.status_code == 404 and codigo(r) == "PEDIDO_NO_EXISTE"
    r = client.post(f"{URL}/historial", headers=h(ADMIN),
                    json={"id_pedido": id_pedido, "estado": "LISTO", "fecha": "ayer"})
    assert r.status_code == 400 and codigo(r) == "FECHA_INVALIDA"


def test_hu15_editar_sin_campos_y_inexistente(client):
    r = client.put(f"{URL}/historial/1", headers=h(ADMIN), json={})
    assert r.status_code == 400 and codigo(r) == "CAMPO_REQUERIDO"
    r = client.put(f"{URL}/historial/999999", headers=h(ADMIN), json={"estado": "LISTO"})
    assert r.status_code == 404 and codigo(r) == "HISTORIAL_NO_EXISTE"
    r = client.delete(f"{URL}/historial/999999", headers=h(ADMIN))
    assert r.status_code == 404 and codigo(r) == "HISTORIAL_NO_EXISTE"


def test_hu15_rol_incorrecto(client):
    r = client.get(f"{URL}/historial", headers=h(COCINA))
    assert r.status_code == 403 and codigo(r) == "ACCESO_DENEGADO"
