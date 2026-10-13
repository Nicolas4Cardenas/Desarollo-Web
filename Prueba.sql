-- =====================================================================
--  Pruebas del backend de PoliRestaurante
--  Ejecutar DESPUÉS de poli_restaurante_backend.sql
--  Usuarios semilla: 1 = admin, 2 = mesero1, 3 = mesero2, 4 = cocina1
-- =====================================================================
USE poli_restaurante;

SELECT '--- 1. FLUJO FELIZ: mesero crea pedido (mesa 1) y agrega productos ---' AS prueba;
CALL sp_mesero_crear_pedido(2, 1, @p1);
SELECT @p1 AS id_pedido_creado;
CALL sp_mesero_agregar_producto(2, @p1, 3, 2, 'sin cebolla');   -- 2 hamburguesas
CALL sp_mesero_agregar_producto(2, @p1, 5, 2, NULL);            -- 2 gaseosas
CALL sp_mesero_agregar_producto(2, @p1, 2, 1, 'sin sal');       -- 1 papas
SELECT id_mesa, numero, estado FROM mesa WHERE numero = 1;      -- debe estar ocupada

SELECT '--- 2. Editar / quitar producto mientras está PENDIENTE ---' AS prueba;
CALL sp_mesero_modificar_detalle(2, (SELECT id_detalle FROM detalle_pedido WHERE id_pedido=@p1 AND id_producto=5), 1, NULL);
CALL sp_mesero_quitar_producto(2, (SELECT id_detalle FROM detalle_pedido WHERE id_pedido=@p1 AND id_producto=2));

SELECT '--- 3. Cocina ve la cola (2 result sets) ---' AS prueba;
CALL sp_cocina_ver_cola(4);

SELECT '--- 4. Cocina: PENDIENTE -> EN_PREPARACION -> LISTO ---' AS prueba;
CALL sp_cocina_iniciar_preparacion(4, @p1);
SELECT SLEEP(1);
CALL sp_cocina_marcar_listo(4, @p1);

SELECT '--- 5. Mesero ve pedidos listos y entrega ---' AS prueba;
CALL sp_mesero_pedidos_listos(2);
CALL sp_mesero_marcar_entregado(2, @p1);
SELECT numero, estado FROM mesa WHERE numero = 1;               -- debe volver a libre

SELECT '--- 6. Segundo pedido cancelado (mesa 2) ---' AS prueba;
CALL sp_mesero_crear_pedido(3, 2, @p2);
CALL sp_mesero_agregar_producto(3, @p2, 4, 3, NULL);
CALL sp_mesero_cancelar_pedido(3, @p2);
SELECT numero, estado FROM mesa WHERE numero = 2;               -- libre otra vez

SELECT '--- 7. Historial del pedido 1 (auditoría admin) ---' AS prueba;
CALL sp_admin_ver_historial_pedido(1, @p1);

SELECT '--- 8. Reportes ---' AS prueba;
CALL sp_admin_reporte_ventas(1, CURDATE(), CURDATE(), NULL, NULL);
CALL sp_admin_reporte_tiempos(1, CURDATE(), CURDATE());

-- =====================================================================
-- CASOS DE ERROR (cada uno DEBE fallar con el mensaje indicado).
-- Se ejecutan con --force para que el script continúe tras cada error.
-- =====================================================================
SELECT '--- E1: mesero intenta usar función de cocina (ACCESO_DENEGADO) ---' AS prueba;
CALL sp_cocina_ver_cola(2);
SELECT '--- E2: cocina intenta gestionar menú (ACCESO_DENEGADO) ---' AS prueba;
CALL sp_admin_crear_categoria(4, 'Combos');
SELECT '--- E3: entregar pedido que no está LISTO (TRANSICION_INVALIDA) ---' AS prueba;
CALL sp_mesero_crear_pedido(2, 3, @p3);
CALL sp_mesero_agregar_producto(2, @p3, 1, 1, NULL);
CALL sp_mesero_marcar_entregado(2, @p3);
SELECT '--- E4: editar pedido EN_PREPARACION (PEDIDO_BLOQUEADO) ---' AS prueba;
CALL sp_cocina_iniciar_preparacion(4, @p3);
CALL sp_mesero_agregar_producto(2, @p3, 2, 1, NULL);
SELECT '--- E5: cancelar pedido ENTREGADO (CANCELACION_NO_PERMITIDA) ---' AS prueba;
CALL sp_mesero_cancelar_pedido(2, @p1);
SELECT '--- E6: crear pedido en mesa ocupada (MESA_OCUPADA) ---' AS prueba;
CALL sp_mesero_crear_pedido(3, 3, @p4);
SELECT '--- E7: producto no disponible (PRODUCTO_NO_DISPONIBLE) ---' AS prueba;
CALL sp_mesero_crear_pedido(3, 4, @p5);
CALL sp_mesero_agregar_producto(3, @p5, 8, 1, NULL);
SELECT '--- E8: precio negativo (PRECIO_INVALIDO) ---' AS prueba;
CALL sp_admin_crear_producto(1, 'Prueba', 'x', -5, 1, TRUE);
SELECT '--- E9: borrar categoría con productos (CATEGORIA_CON_PRODUCTOS) ---' AS prueba;
CALL sp_admin_eliminar_categoria(1, 1);
SELECT '--- E10: editar/borrar historial (HISTORIAL_INMUTABLE) ---' AS prueba;
UPDATE historial_estado SET estado = 'LISTO' WHERE id_historial = 1;
DELETE FROM historial_estado WHERE id_historial = 1;
SELECT '--- E11: contraseña en texto plano (HASH_INVALIDO) ---' AS prueba;
CALL sp_admin_crear_usuario(1, 'Nuevo', 'nuevo1', 'clave123', 'MESERO');
SELECT '--- E12: mesero modifica pedido de otro mesero (ACCESO_DENEGADO) ---' AS prueba;
CALL sp_mesero_agregar_producto(3, @p5, 1, 1, NULL);
CALL sp_mesero_agregar_producto(2, @p5, 1, 1, NULL);
SELECT '--- E13: usuario desactivado pierde el acceso ---' AS prueba;
CALL sp_admin_activar_usuario(1, 3, FALSE);
CALL sp_mesero_listar_menu(3);
CALL sp_admin_activar_usuario(1, 3, TRUE);