# 🍽️ Polirestaurante — CRUD con ORM de Nicolas (SQLAlchemy)

Misma aplicación de consola y mismas HU que la versión con driver (**HU-06, 07, 08, 13, 14 y 15**), pero con el **ORM SQLAlchemy**:
no hay SQL escrito a mano; cada tabla es una clase (`modelos.py`) y la sesión genera los `INSERT`, `UPDATE` y `DELETE`.

## 📁 Estructura

```text
CRUD_ORM_SQLAlchemy/
├── main.py            # inicio de sesión y arranque (igual que la versión driver)
├── menu.py            # interfaz de consola (igual que la versión driver)
├── servicio.py        # reglas de negocio con objetos del ORM
├── modelos.py         # clases que mapean las tablas: Rol, Usuario, Mesa, Pedido, DetallePedido, HistorialEstado...
├── db.py              # engine + sesión con commit/rollback
├── validaciones.py, errores.py, config.py
├── tests/test_crud.py # las mismas 28 pruebas (la API de servicio.py es idéntica)
└── requirements.txt
```

## ▶️ Cómo ejecutarlo

```bash
pip install -r requirements.txt
copy .env.example .env     # Windows (Linux/Mac: cp); edita usuario y contraseña de MySQL
python main.py
```

Necesita la base `poli_restaurante_nicolas` (script `../sql/backend_nicolas.sql`). Menú, usuarios de prueba, flujo de demostración y errores
son los mismos que en `CRUD_Driver_MySQL` (opción 20 para cambiar de usuario). El administrador puede ejecutar cualquier opción.

## 🔁 Equivalencias CRUD ↔ ORM (HU-15 historial)

| Operación | Driver (SQL) | ORM (SQLAlchemy) |
|---|---|---|
| Create | `INSERT INTO historial_estado ...` | `session.add(HistorialEstado(...))` + `flush()` |
| Read (lista) | `SELECT ... ORDER BY ...` | `session.query(HistorialEstado).filter(...).all()` |
| Read (uno) | `SELECT ... WHERE id_historial = %s` | `session.get(HistorialEstado, id)` |
| Update | `UPDATE historial_estado SET ...` | `h.estado = "LISTO"` (el cambio se detecta solo) |
| Delete | `DELETE FROM historial_estado ...` | `session.delete(h)` |

Otras diferencias:
- **Relaciones:** `pedido.detalles`, `pedido.mesas`, `pedido.historial` evitan los `JOIN` escritos a mano; `Pedido.total` es una propiedad calculada.
- **Cambio de estado:** `pedido.historial.append(HistorialEstado(...))` inserta el registro del historial junto con la actualización del pedido.
- **Cola:** `Pedido.detalles.any()` filtra los pedidos que tienen productos.
- **Reportes:** se arma la consulta con `join()` y `filter()`; los totales por categoría y por producto se agrupan en Python.
- **Bloqueo:** `with_for_update()` equivale a `SELECT ... FOR UPDATE`.
- **No se usa `create_all()`:** el esquema, los datos semilla y los procedimientos vienen de `backend_nicolas.sql`.

## ✅ Pruebas

```bash
python -m pytest -v
```

Son las mismas 28 pruebas de la versión con driver: prueban la misma API de `servicio.py` y confirman que las dos implementaciones se comportan igual.
Para dejar la base limpia después de probar, vuelve a ejecutar `backend_nicolas.sql`.
