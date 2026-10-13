# 🍽️ Polirestaurante — CRUD con acceso a través de ORM (SQLAlchemy)

CRUD de pedidos del módulo **mesero (HU-01 a HU-05)** en consola, usando **SQLAlchemy** (guía de la Sesión 8).
No hay SQL escrito a mano: las tablas se mapean a clases (`Pedido`, `DetallePedido`, `Mesa`...) y la sesión
genera los INSERT / UPDATE / DELETE. Hace las mismas operaciones y aplica las mismas reglas que la versión con driver.

## 📁 Estructura

```text
CRUD_ORM_SQLAlchemy/
├── main.py            # inicio de sesión (usuario) y arranque
├── menu.py            # menú de consola
├── modelos.py         # ⭐ entidades ORM: Tabla = Clase, Columna = Atributo, FK = relationship()
├── db.py              # engine + SessionLocal + transacción explícita (commit / rollback)
├── servicio.py        # ⭐ el CRUD con la sesión de SQLAlchemy
├── errores.py / validaciones.py / config.py
├── tests/test_crud.py # 21 pruebas automáticas (pytest)
├── requirements.txt
└── .env.example
```

## ▶️ Cómo ejecutarlo (Windows)

Requisitos: Python 3.10+, MySQL 8 con `backend.sql` ya ejecutado.

```bash
python -m pip install -r requirements.txt
copy .env.example .env      # y editar usuario/contraseña de MySQL dentro del .env
python main.py
```

El menú es el mismo de la versión con driver (opciones 1 a 12; la 12 es la simulación de cocina para la demo).
Si aparece un error que menciona `cryptography`, ejecute `python -m pip install cryptography`.

## 🔗 Relación con la guía (Sesión 8)

| Guía | En este proyecto |
|---|---|
| `Base = declarative_base()` y clases con `Column(...)` | `modelos.py` |
| `create_engine(...)` | `db.py` (con `URL.create`, que escapa caracteres raros de la contraseña) |
| CREATE: `session.add(obj); session.commit()` | `crear_pedido`, `agregar_producto` |
| READ: `session.query(Modelo).filter(...)` | `listar_pedidos`, `obtener_pedido`, `listar_menu` |
| UPDATE: modificar el atributo y `commit()` | `modificar_detalle`, `_cambiar_estado` (HU-04, HU-05) |
| DELETE: `session.delete(obj)` | `quitar_producto` (`pedido.detalles.remove(d)` + `delete-orphan`) |
| Relaciones 1:N y N:N | `Pedido.detalles` (1:N), `Pedido.mesas` (N:N con la tabla `pedido_mesa`) |
| Mejores prácticas: transacciones explícitas, evitar N+1, auditoría | `db.sesion()`, `selectinload(...)`, historial de estados |

> En SQLAlchemy 2.x `session.query(...).get(id)` quedó obsoleto: se usa `session.get(Modelo, id)`.

## ✅ Pruebas automáticas

```bash
python -m pytest -v
```

Mismas 21 pruebas que la versión con driver. Crean pedidos reales (y los cancelan al terminar), así que
al final de las pruebas conviene volver a ejecutar `backend.sql` para dejar la base limpia.

## 📝 Reglas aplicadas

Idénticas a la versión con driver: solo MESERO activo, solo sus pedidos, edición únicamente en PENDIENTE,
entregar solo desde LISTO, cancelar cualquier pedido no entregado (HU-05), precio guardado en `precio_unitario`
y cada cambio de estado registrado en `historial_estado`.
