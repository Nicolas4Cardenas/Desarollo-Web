"""Pruebas del CRUD REST (HU-01 a HU-05) contra la base poli_restaurante real.

Requisitos: MySQL levantado con backend.sql cargado y el .env configurado.
Ejecutar:   pytest -v
Cada prueba cierra los pedidos que crea para dejar las mesas libres.
"""
import pytest

from api import crear_app
from api.dao import pedido_dao
from api.db import conexion

ADMIN, MESERO1, MESERO2, COCINA = 1, 2, 3, 4   # ids de los datos semilla
HAMBURGUESA, GASEOSA = 3, 5                      # ids de productos semilla
API = "/api/v1"


def h(id_usuario):
    return {"X-Usuario-Id": str(id_usuario)}


@pytest.fixture
def client():
    app = crear_app()
    app.testing = True
    return app.test_client()


@pytest.fixture
def pedidos_creados():
    """Registra los ids de pedidos de la prueba y los cierra al terminar."""
    ids = []
    yield ids
    for id_pedido in ids:
        for accion in (pedido_dao.cancelar_pedido, pedido_dao.marcar_entregado):
            try:
                accion(MESERO1, id_pedido)
                break
            except Exception:
                continue


def mesa_libre(client):
    return client.get(f"{API}/mesas/libres", headers=h(MESERO1)).get_json()[0]["id_mesa"]


def nuevo_pedido(client, ids, mesero=MESERO1):
    r = client.post(f"{API}/pedidos", json={"id_mesa": mesa_libre(client)}, headers=h(mesero))
    assert r.status_code == 201, r.get_json()
    id_pedido = r.get_json()["pedido"]["id_pedido"]
    ids.append(id_pedido)
    return id_pedido


def con_producto(client, ids, producto=HAMBURGUESA, cantidad=2, notas=None):
    id_pedido = nuevo_pedido(client, ids)
    body = {"id_producto": producto, "cantidad": cantidad}
    if notas:
        body["notas"] = notas
    r = client.post(f"{API}/pedidos/{id_pedido}/productos", json=body, headers=h(MESERO1))
    assert r.status_code == 201, r.get_json()
    return id_pedido, r.get_json()["id_detalle"]


def cocina_deja_listo(id_pedido):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_cocina_iniciar_preparacion(%s, %s)", (COCINA, id_pedido))
        while cur.nextset():
            pass
        cur.execute("CALL sp_cocina_marcar_listo(%s, %s)", (COCINA, id_pedido))
        while cur.nextset():
            pass


# ------------------------------------------------------------------ general
def test_salud(client):
    assert client.get(f"{API}/salud").status_code == 200


def test_sin_cabecera_usuario_401(client):
    r = client.get(f"{API}/pedidos")
    assert r.status_code == 401 and r.get_json()["codigo"] == "NO_AUTENTICADO"


def test_rol_incorrecto_403(client):
    r = client.post(f"{API}/pedidos", json={"id_mesa": 1}, headers=h(COCINA))
    assert r.status_code == 403 and r.get_json()["codigo"] == "ACCESO_DENEGADO"


def test_ruta_inexistente_404(client):
    assert client.get(f"{API}/nada").status_code == 404


# -------------------------------------------------------------- HU-01 crear
def test_hu01_crear_pedido(client, pedidos_creados):
    id_mesa = mesa_libre(client)
    r = client.post(f"{API}/pedidos", json={"id_mesa": id_mesa}, headers=h(MESERO1))
    assert r.status_code == 201
    pedido = r.get_json()["pedido"]
    pedidos_creados.append(pedido["id_pedido"])
    assert pedido["estado"] == "PENDIENTE"
    assert pedido["fecha_creacion"]                      # fecha y hora automáticas
    assert r.headers["Location"].endswith(f"/pedidos/{pedido['id_pedido']}")
    # la mesa queda ocupada automáticamente
    libres = [m["id_mesa"] for m in client.get(f"{API}/mesas/libres", headers=h(MESERO1)).get_json()]
    assert id_mesa not in libres


def test_hu01_mesa_ocupada_409(client, pedidos_creados):
    id_mesa = mesa_libre(client)
    r1 = client.post(f"{API}/pedidos", json={"id_mesa": id_mesa}, headers=h(MESERO1))
    pedidos_creados.append(r1.get_json()["pedido"]["id_pedido"])
    r2 = client.post(f"{API}/pedidos", json={"id_mesa": id_mesa}, headers=h(MESERO2))
    assert r2.status_code == 409 and r2.get_json()["codigo"] == "MESA_OCUPADA"


def test_hu01_validaciones(client):
    assert client.post(f"{API}/pedidos", json={"id_mesa": 999}, headers=h(MESERO1)).status_code == 404
    assert client.post(f"{API}/pedidos", json={}, headers=h(MESERO1)).status_code == 400
    assert client.post(f"{API}/pedidos", json={"id_mesa": "uno"}, headers=h(MESERO1)).status_code == 400
    assert client.post(f"{API}/pedidos", data="no es json", headers=h(MESERO1)).status_code == 400


# ------------------------------------------------------- HU-02 agregar
def test_hu02_agregar_productos_y_total(client, pedidos_creados):
    id_pedido = nuevo_pedido(client, pedidos_creados)
    r = client.post(f"{API}/pedidos/{id_pedido}/productos",
                    json={"id_producto": HAMBURGUESA, "cantidad": 2, "notas": "sin cebolla"},
                    headers=h(MESERO1))
    assert r.status_code == 201 and r.get_json()["total"] == 44000
    r = client.post(f"{API}/pedidos/{id_pedido}/productos",
                    json={"id_producto": GASEOSA, "cantidad": 1}, headers=h(MESERO1))
    assert r.get_json()["total"] == 48500
    detalle = client.get(f"{API}/pedidos/{id_pedido}", headers=h(MESERO1)).get_json()
    assert len(detalle["productos"]) == 2
    assert any(p["notas"] == "sin cebolla" for p in detalle["productos"])
    assert detalle["total"] == 48500


def test_hu02_producto_repetido_suma_cantidad(client, pedidos_creados):
    id_pedido, _ = con_producto(client, pedidos_creados, cantidad=1)
    r = client.post(f"{API}/pedidos/{id_pedido}/productos",
                    json={"id_producto": HAMBURGUESA, "cantidad": 2}, headers=h(MESERO1))
    assert r.get_json()["total"] == 66000                 # 3 x 22.000


def test_hu02_errores(client, pedidos_creados):
    id_pedido = nuevo_pedido(client, pedidos_creados)
    url = f"{API}/pedidos/{id_pedido}/productos"
    assert client.post(url, json={"id_producto": HAMBURGUESA, "cantidad": 0}, headers=h(MESERO1)).status_code == 400
    assert client.post(url, json={"id_producto": HAMBURGUESA}, headers=h(MESERO1)).status_code == 400
    assert client.post(url, json={"id_producto": 999, "cantidad": 1}, headers=h(MESERO1)).status_code == 404
    r = client.post(url, json={"id_producto": HAMBURGUESA, "cantidad": 1}, headers=h(MESERO2))
    assert r.status_code == 403                           # pedido de otro mesero
    assert client.post(f"{API}/pedidos/99999/productos", json={"id_producto": 1, "cantidad": 1},
                       headers=h(MESERO1)).status_code == 404


# ------------------------------------------------------ HU-03 editar / quitar
def test_hu03_editar_cantidad_y_conservar_notas(client, pedidos_creados):
    id_pedido, id_detalle = con_producto(client, pedidos_creados, notas="sin cebolla")
    url = f"{API}/pedidos/{id_pedido}/productos/{id_detalle}"
    r = client.put(url, json={"cantidad": 3}, headers=h(MESERO1))
    assert r.status_code == 200 and r.get_json()["total"] == 66000
    prod = client.get(f"{API}/pedidos/{id_pedido}", headers=h(MESERO1)).get_json()["productos"][0]
    assert prod["cantidad"] == 3 and prod["notas"] == "sin cebolla"
    r = client.put(url, json={"cantidad": 1, "notas": "bien cocida"}, headers=h(MESERO1))
    assert r.status_code == 200
    prod = client.get(f"{API}/pedidos/{id_pedido}", headers=h(MESERO1)).get_json()["productos"][0]
    assert prod["notas"] == "bien cocida"


def test_hu03_quitar_producto(client, pedidos_creados):
    id_pedido, id_detalle = con_producto(client, pedidos_creados)
    r = client.delete(f"{API}/pedidos/{id_pedido}/productos/{id_detalle}", headers=h(MESERO1))
    assert r.status_code == 200 and r.get_json()["total"] == 0
    assert client.get(f"{API}/pedidos/{id_pedido}", headers=h(MESERO1)).get_json()["productos"] == []


def test_hu03_bloqueado_si_ya_esta_en_preparacion(client, pedidos_creados):
    id_pedido, id_detalle = con_producto(client, pedidos_creados)
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_cocina_iniciar_preparacion(%s, %s)", (COCINA, id_pedido))
    url = f"{API}/pedidos/{id_pedido}/productos/{id_detalle}"
    r = client.put(url, json={"cantidad": 5}, headers=h(MESERO1))
    assert r.status_code == 409 and r.get_json()["codigo"] == "PEDIDO_BLOQUEADO"
    r = client.delete(url, headers=h(MESERO1))
    assert r.status_code == 409 and r.get_json()["codigo"] == "PEDIDO_BLOQUEADO"


def test_hu03_detalle_de_otro_pedido_404(client, pedidos_creados):
    id_a, _ = con_producto(client, pedidos_creados)
    id_b, detalle_b = con_producto(client, pedidos_creados)
    r = client.put(f"{API}/pedidos/{id_a}/productos/{detalle_b}", json={"cantidad": 1}, headers=h(MESERO1))
    assert r.status_code == 404 and r.get_json()["codigo"] == "DETALLE_NO_EXISTE"


# ------------------------------------------------------ HU-04 entregado
def test_hu04_entregar_solo_si_esta_listo(client, pedidos_creados):
    id_pedido, _ = con_producto(client, pedidos_creados)
    r = client.put(f"{API}/pedidos/{id_pedido}/entregar", headers=h(MESERO1))
    assert r.status_code == 409 and r.get_json()["codigo"] == "TRANSICION_INVALIDA"
    cocina_deja_listo(id_pedido)
    r = client.put(f"{API}/pedidos/{id_pedido}/entregar", headers=h(MESERO1))
    assert r.status_code == 200 and r.get_json()["pedido"]["estado"] == "ENTREGADO"


def test_hu04_libera_la_mesa(client, pedidos_creados):
    id_pedido, _ = con_producto(client, pedidos_creados)
    mesas = client.get(f"{API}/pedidos/{id_pedido}", headers=h(MESERO1)).get_json()["mesas"]
    cocina_deja_listo(id_pedido)
    client.put(f"{API}/pedidos/{id_pedido}/entregar", headers=h(MESERO1))
    libres = [m["numero"] for m in client.get(f"{API}/mesas/libres", headers=h(MESERO1)).get_json()]
    assert all(m in libres for m in mesas)


def test_hu04_pedido_ajeno_o_inexistente(client, pedidos_creados):
    id_pedido, _ = con_producto(client, pedidos_creados)
    assert client.put(f"{API}/pedidos/{id_pedido}/entregar", headers=h(MESERO2)).status_code == 403
    assert client.put(f"{API}/pedidos/99999/entregar", headers=h(MESERO1)).status_code == 404


# ------------------------------------------------------ HU-05 cancelar
def test_hu05_cancelar_pendiente(client, pedidos_creados):
    id_pedido, _ = con_producto(client, pedidos_creados)
    r = client.delete(f"{API}/pedidos/{id_pedido}", headers=h(MESERO1))
    assert r.status_code == 200 and r.get_json()["pedido"]["estado"] == "CANCELADO"
    with conexion() as con, con.cursor() as cur:         # queda quién canceló (HU-05)
        cur.execute("SELECT id_usuario_cambio FROM historial_estado "
                    "WHERE id_pedido=%s AND estado='CANCELADO'", (id_pedido,))
        assert cur.fetchone()["id_usuario_cambio"] == MESERO1


def test_hu05_no_se_cancela_entregado(client, pedidos_creados):
    id_pedido, _ = con_producto(client, pedidos_creados)
    cocina_deja_listo(id_pedido)
    client.put(f"{API}/pedidos/{id_pedido}/entregar", headers=h(MESERO1))
    r = client.delete(f"{API}/pedidos/{id_pedido}", headers=h(MESERO1))
    assert r.status_code == 409 and r.get_json()["codigo"] == "CANCELACION_NO_PERMITIDA"


def test_hu05_pedido_ajeno_o_inexistente(client, pedidos_creados):
    id_pedido, _ = con_producto(client, pedidos_creados)
    assert client.delete(f"{API}/pedidos/{id_pedido}", headers=h(MESERO2)).status_code == 403
    assert client.delete(f"{API}/pedidos/99999", headers=h(MESERO1)).status_code == 404


# ------------------------------------------------------------ consultas
def test_listar_y_filtrar_por_estado(client, pedidos_creados):
    id_pedido, _ = con_producto(client, pedidos_creados)
    todos = client.get(f"{API}/pedidos", headers=h(MESERO1)).get_json()
    assert id_pedido in [p["id_pedido"] for p in todos]
    pend = client.get(f"{API}/pedidos?estado=pendiente", headers=h(MESERO1)).get_json()
    assert all(p["estado"] == "PENDIENTE" for p in pend)
    assert client.get(f"{API}/pedidos?estado=XYZ", headers=h(MESERO1)).status_code == 400
    assert client.get(f"{API}/menu", headers=h(MESERO1)).status_code == 200
