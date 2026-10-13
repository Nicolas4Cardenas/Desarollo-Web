# 🍽️ Polirestaurante — CRUD con acceso a tablas mediante driver (MySQL)

CRUD de pedidos del módulo **mesero (HU-01 a HU-05)** en consola. Usa el **driver oficial `mysql-connector-python`**
y escribe el **SQL a mano** (INSERT / SELECT / UPDATE / DELETE) directamente sobre las tablas de `poli_restaurante`.
No usa ORM ni procedimientos almacenados: las reglas de negocio se aplican en Python y cada operación es una
transacción (commit / rollback).

## 📁 Estructura

```text
CRUD_Driver_MySQL/
├── main.py            # inicio de sesión (usuario) y arranque
├── menu.py            # menú de consola (solo pide datos y muestra resultados)
├── servicio.py        # ⭐ el CRUD: SQL con el driver + reglas de negocio
├── errores.py         # ErrorNegocio (códigos como MESA_OCUPADA)
├── validaciones.py    # cantidad > 0, notas <= 255
├── config.py          # lee el .env
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

Entrar con el usuario **mesero1** (o mesero2). El menú:

| Opción | Qué hace |
|---|---|
| 3 | **HU-01** Crear pedido (asocia una mesa libre, estado PENDIENTE, fecha y hora automáticas) |
| 4 | **HU-02** Agregar producto (cantidad y notas; el total se recalcula) |
| 5 / 6 | **HU-03** Editar / quitar producto (solo si el pedido está PENDIENTE) |
| 7 | **HU-04** Marcar como entregado (solo si está LISTO) |
| 8 | **HU-05** Cancelar (si no está entregado; queda quién canceló) |
| 1, 2, 9, 10, 11 | Consultas: menú, mesas libres, mis pedidos, detalle, historial |
| 12 | **[DEMO]** Simula a cocina: PENDIENTE → EN_PREPARACION → LISTO (para poder demostrar HU-04 sin usar Workbench) |

## 🔎 Dónde está cada HU en el código (`servicio.py`)

| HU | Función | SQL principal |
|---|---|---|
| HU-01 | `crear_pedido` | `INSERT INTO pedido`, `INSERT INTO pedido_mesa`, `UPDATE mesa SET estado='ocupada'`, `INSERT INTO historial_estado` |
| HU-02 | `agregar_producto` | `INSERT INTO detalle_pedido` (o `UPDATE ... cantidad = cantidad + x` si el producto ya estaba) |
| HU-03 | `modificar_detalle` / `quitar_producto` | `UPDATE detalle_pedido` / `DELETE FROM detalle_pedido` |
| HU-04 | `marcar_entregado` | `UPDATE pedido SET estado='ENTREGADO'` + historial + liberar mesa |
| HU-05 | `cancelar_pedido` | `UPDATE pedido SET estado='CANCELADO'` + historial + liberar mesa |

## ✅ Pruebas automáticas

```bash
python -m pytest -v
```

Cubren casos felices y de error (mesa ocupada, rol incorrecto, pedido ajeno, edición bloqueada, entregar sin estar
LISTO, cancelar un pedido entregado...). Cada prueba cancela lo que crea, pero **crean pedidos reales en tu base**:
al terminar de probar, vuelve a ejecutar `backend.sql` para dejarla limpia.

## 📝 Reglas aplicadas

- Solo un usuario con rol MESERO activo puede usar el CRUD; solo ve y modifica **sus** pedidos.
- Editar productos solo con el pedido en PENDIENTE (en la base también lo protege un trigger).
- HU-05: se puede cancelar cualquier pedido **no entregado** (PENDIENTE, EN_PREPARACION o LISTO), como dice la historia.
  *(Ojo: el procedimiento `sp_cambiar_estado` del backend.sql no permite cancelar desde LISTO; este CRUD sigue el texto de la HU.)*
- El precio de cada producto se guarda en `precio_unitario` al agregarlo.
- Cada cambio de estado se inserta en `historial_estado` con fecha y usuario.
