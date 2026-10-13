-- =====================================================================
-- Datos de demostración (ejecutar DESPUÉS de backend.sql, una sola vez)
-- Crea 4 pedidos PENDIENTES, uno por cada forma de acceso a la base:
--   Pedido 1 (mesa 1) -> versión con procedimientos almacenados
--   Pedido 2 (mesa 2) -> versión con driver (SQL directo)
--   Pedido 3 (mesa 3) -> versión con ORM (SQLAlchemy)
--   Pedido 4 (mesa 4) -> queda pendiente: sirve para las pruebas de error
-- Usuarios: 1 admin, 2 mesero1, 3 mesero2, 4 cocina1
-- =====================================================================
USE poli_restaurante;

CALL sp_mesero_crear_pedido(2, 1, @p1);
CALL sp_mesero_agregar_producto(2, @p1, 3, 2, 'sin cebolla');
CALL sp_mesero_agregar_producto(2, @p1, 5, 2, NULL);

CALL sp_mesero_crear_pedido(3, 2, @p2);
CALL sp_mesero_agregar_producto(3, @p2, 3, 2, 'sin cebolla');
CALL sp_mesero_agregar_producto(3, @p2, 5, 2, NULL);

CALL sp_mesero_crear_pedido(2, 3, @p3);
CALL sp_mesero_agregar_producto(2, @p3, 3, 2, 'sin cebolla');
CALL sp_mesero_agregar_producto(2, @p3, 5, 2, NULL);

CALL sp_mesero_crear_pedido(3, 4, @p4);
CALL sp_mesero_agregar_producto(3, @p4, 4, 1, 'sin salsa');

-- Debe devolver 1, 2, 3 y 4
SELECT @p1 AS pedido_1, @p2 AS pedido_2, @p3 AS pedido_3, @p4 AS pedido_4;
