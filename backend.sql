-- =====================================================================
--  PoliRestaurante - Backend en SQL (MySQL 8 / compatible con MariaDB 10.5+)
--  Proyecto Corte 1 - Desarrollo de Software - Politécnico Grancolombiano
--
--  Estructura:
--    1. Esquema (tablas según el diagrama de clases del documento)
--    2. Triggers (historial inmutable, detalle solo editable en PENDIENTE)
--    3. Funciones / procedimientos auxiliares (roles, total, motor de estados)
--    4. MÓDULO MESERO         (sp_mesero_*)
--    5. MÓDULO COCINA         (sp_cocina_*)
--    6. MÓDULO ADMINISTRACIÓN (sp_admin_*)
--    7. Autenticación         (sp_auth_*)
--    8. Datos semilla
--
--  Convención: todo procedimiento público recibe como primer parámetro el
--  id del usuario que ejecuta la acción y valida su rol EN LA BASE DE DATOS
--  (RNF-06: control de acceso en backend, no solo en el frontend).
--  Toda operación crítica corre en una transacción (RNF-10).
--
--  Contraseñas (RNF-05): la base solo guarda el HASH (bcrypt generado por la
--  aplicación). Nunca se almacena ni se recibe texto plano.
-- =====================================================================

DROP DATABASE IF EXISTS poli_restaurante;
CREATE DATABASE poli_restaurante CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE poli_restaurante;

-- =====================================================================
-- 1. ESQUEMA
-- =====================================================================

CREATE TABLE rol (
    id_rol  INT AUTO_INCREMENT PRIMARY KEY,
    nombre  VARCHAR(30) NOT NULL UNIQUE          -- MESERO | COCINA | ADMINISTRADOR
) ENGINE=InnoDB;

CREATE TABLE usuario (
    id_usuario      INT AUTO_INCREMENT PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL,
    usuario_login   VARCHAR(50)  NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,        -- hash bcrypt, nunca texto plano
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    id_rol          INT          NOT NULL,
    CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol) REFERENCES rol(id_rol)
) ENGINE=InnoDB;

CREATE TABLE mesa (
    id_mesa INT AUTO_INCREMENT PRIMARY KEY,
    numero  INT NOT NULL UNIQUE,
    estado  VARCHAR(20) NOT NULL DEFAULT 'libre',
    CONSTRAINT ck_mesa_estado CHECK (estado IN ('libre','ocupada'))
) ENGINE=InnoDB;

CREATE TABLE categoria (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE producto (
    id_producto    INT AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(100)  NOT NULL,
    descripcion    VARCHAR(255),
    precio         DECIMAL(10,2) NOT NULL,
    disponibilidad BOOLEAN       NOT NULL DEFAULT TRUE,
    id_categoria   INT           NOT NULL,
    CONSTRAINT ck_producto_precio CHECK (precio >= 0),          -- HU-07: sin precios negativos
    CONSTRAINT fk_producto_categoria FOREIGN KEY (id_categoria) REFERENCES categoria(id_categoria)
) ENGINE=InnoDB;

CREATE TABLE pedido (
    id_pedido                INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario_mesero        INT         NOT NULL,
    estado                   VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    fecha_creacion           DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_actualizacion DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_pedido_estado CHECK (estado IN
        ('PENDIENTE','EN_PREPARACION','LISTO','ENTREGADO','CANCELADO')),
    CONSTRAINT fk_pedido_mesero FOREIGN KEY (id_usuario_mesero) REFERENCES usuario(id_usuario),
    INDEX idx_pedido_estado_fecha (estado, fecha_creacion)
) ENGINE=InnoDB;

-- Tabla intermedia pedido <-> mesa (según el diagrama)
CREATE TABLE pedido_mesa (
    id_pedido INT NOT NULL,
    id_mesa   INT NOT NULL,
    PRIMARY KEY (id_pedido, id_mesa),
    CONSTRAINT fk_pm_pedido FOREIGN KEY (id_pedido) REFERENCES pedido(id_pedido),
    CONSTRAINT fk_pm_mesa   FOREIGN KEY (id_mesa)   REFERENCES mesa(id_mesa)
) ENGINE=InnoDB;

CREATE TABLE detalle_pedido (
    id_detalle      INT AUTO_INCREMENT PRIMARY KEY,
    id_pedido       INT NOT NULL,
    id_producto     INT NOT NULL,
    cantidad        INT NOT NULL,
    notas           VARCHAR(255),
    -- AJUSTE AL DIAGRAMA: precio del producto al momento de pedir, para que los
    -- reportes de ventas no cambien si luego el administrador modifica el precio.
    precio_unitario DECIMAL(10,2) NOT NULL,
    CONSTRAINT ck_detalle_cantidad CHECK (cantidad > 0),
    -- El diagrama marca id_producto como UNIQUE; se implementa como UNIQUE por
    -- pedido (un producto una sola vez dentro de cada pedido).
    CONSTRAINT uq_detalle_pedido_producto UNIQUE (id_pedido, id_producto),
    CONSTRAINT fk_detalle_pedido   FOREIGN KEY (id_pedido)   REFERENCES pedido(id_pedido),
    CONSTRAINT fk_detalle_producto FOREIGN KEY (id_producto) REFERENCES producto(id_producto)
) ENGINE=InnoDB;

CREATE TABLE historial_estado (
    id_historial      INT AUTO_INCREMENT PRIMARY KEY,
    id_pedido         INT         NOT NULL,
    estado            VARCHAR(20) NOT NULL,
    fecha             DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_usuario_cambio INT         NOT NULL,
    CONSTRAINT fk_hist_pedido  FOREIGN KEY (id_pedido)         REFERENCES pedido(id_pedido),
    CONSTRAINT fk_hist_usuario FOREIGN KEY (id_usuario_cambio) REFERENCES usuario(id_usuario),
    INDEX idx_hist_pedido (id_pedido, fecha)
) ENGINE=InnoDB;

-- =====================================================================
-- 2. TRIGGERS
-- =====================================================================
DELIMITER $$

-- RNF-11: el historial es inmutable (sin UPDATE ni DELETE)
CREATE TRIGGER trg_historial_no_update BEFORE UPDATE ON historial_estado
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'HISTORIAL_INMUTABLE: no se puede editar el historial de estados';
END$$

CREATE TRIGGER trg_historial_no_delete BEFORE DELETE ON historial_estado
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'HISTORIAL_INMUTABLE: no se puede borrar el historial de estados';
END$$

-- HU-03: el detalle solo se puede tocar mientras el pedido está PENDIENTE
-- (defensa adicional: aunque alguien escriba SQL directo, la regla se cumple)
CREATE TRIGGER trg_detalle_bi BEFORE INSERT ON detalle_pedido
FOR EACH ROW
BEGIN
    IF (SELECT estado FROM pedido WHERE id_pedido = NEW.id_pedido) <> 'PENDIENTE' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_BLOQUEADO: solo se puede editar un pedido en estado PENDIENTE';
    END IF;
END$$

CREATE TRIGGER trg_detalle_bu BEFORE UPDATE ON detalle_pedido
FOR EACH ROW
BEGIN
    IF (SELECT estado FROM pedido WHERE id_pedido = OLD.id_pedido) <> 'PENDIENTE' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_BLOQUEADO: solo se puede editar un pedido en estado PENDIENTE';
    END IF;
END$$

CREATE TRIGGER trg_detalle_bd BEFORE DELETE ON detalle_pedido
FOR EACH ROW
BEGIN
    IF (SELECT estado FROM pedido WHERE id_pedido = OLD.id_pedido) <> 'PENDIENTE' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_BLOQUEADO: solo se puede editar un pedido en estado PENDIENTE';
    END IF;
END$$

DELIMITER ;

-- =====================================================================
-- 3. AUXILIARES
-- =====================================================================

-- Total del pedido (HU-02: se recalcula solo, siempre se deriva del detalle)
DELIMITER $$
CREATE FUNCTION fn_total_pedido(p_id_pedido INT)
RETURNS DECIMAL(12,2)
READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(12,2);
    SELECT COALESCE(SUM(cantidad * precio_unitario), 0) INTO v_total
      FROM detalle_pedido WHERE id_pedido = p_id_pedido;
    RETURN v_total;
END$$
DELIMITER ;

CREATE VIEW v_pedido_resumen AS
SELECT p.id_pedido, p.estado, p.fecha_creacion, p.fecha_ultima_actualizacion,
       p.id_usuario_mesero, u.nombre AS mesero,
       (SELECT GROUP_CONCAT(m.numero ORDER BY m.numero SEPARATOR ',')
          FROM pedido_mesa pm JOIN mesa m ON m.id_mesa = pm.id_mesa
         WHERE pm.id_pedido = p.id_pedido) AS mesas,
       fn_total_pedido(p.id_pedido) AS total
  FROM pedido p JOIN usuario u ON u.id_usuario = p.id_usuario_mesero;

DELIMITER $$

-- RF-16 / RNF-06: valida que el usuario exista, esté activo y tenga el rol pedido
CREATE PROCEDURE sp_validar_rol(IN p_id_usuario INT, IN p_rol VARCHAR(30))
BEGIN
    DECLARE v_rol VARCHAR(30);
    SELECT r.nombre INTO v_rol
      FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
     WHERE u.id_usuario = p_id_usuario AND u.activo = TRUE;
    IF v_rol IS NULL OR v_rol <> p_rol THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ACCESO_DENEGADO: el usuario no tiene permiso para esta operación';
    END IF;
END$$

-- Libera las mesas del pedido si ya no tienen otro pedido activo
CREATE PROCEDURE sp_liberar_mesas_pedido(IN p_id_pedido INT)
BEGIN
    UPDATE mesa m
      JOIN pedido_mesa pm ON pm.id_mesa = m.id_mesa AND pm.id_pedido = p_id_pedido
       SET m.estado = 'libre'
     WHERE NOT EXISTS (
            SELECT 1
              FROM pedido_mesa pm2 JOIN pedido p2 ON p2.id_pedido = pm2.id_pedido
             WHERE pm2.id_mesa = m.id_mesa
               AND pm2.id_pedido <> p_id_pedido
               AND p2.estado IN ('PENDIENTE','EN_PREPARACION','LISTO'));
END$$

-- MOTOR DE ESTADOS (uso interno; siempre se llama dentro de una transacción)
-- PENDIENTE -> EN_PREPARACION -> LISTO -> ENTREGADO
-- CANCELADO solo desde PENDIENTE o EN_PREPARACION (HU-05: nunca desde ENTREGADO)
CREATE PROCEDURE sp_cambiar_estado(IN p_id_pedido INT, IN p_nuevo VARCHAR(20), IN p_id_usuario INT)
BEGIN
    DECLARE v_actual VARCHAR(20);
    DECLARE v_valido BOOLEAN DEFAULT FALSE;

    SELECT estado INTO v_actual FROM pedido WHERE id_pedido = p_id_pedido FOR UPDATE;
    IF v_actual IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_NO_EXISTE: el pedido indicado no existe';
    END IF;

    SET v_valido = (v_actual = 'PENDIENTE'      AND p_nuevo = 'EN_PREPARACION')
                OR (v_actual = 'EN_PREPARACION' AND p_nuevo = 'LISTO')
                OR (v_actual = 'LISTO'          AND p_nuevo = 'ENTREGADO')
                OR (v_actual IN ('PENDIENTE','EN_PREPARACION') AND p_nuevo = 'CANCELADO');

    IF NOT v_valido THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'TRANSICION_INVALIDA: el cambio de estado no está permitido';
    END IF;

    UPDATE pedido SET estado = p_nuevo, fecha_ultima_actualizacion = NOW()
     WHERE id_pedido = p_id_pedido;

    -- HU-15 / RF-15: cada cambio queda registrado (fecha, hora y usuario)
    INSERT INTO historial_estado (id_pedido, estado, fecha, id_usuario_cambio)
    VALUES (p_id_pedido, p_nuevo, NOW(), p_id_usuario);

    -- HU-11: la mesa se libera automáticamente al cerrar el pedido
    IF p_nuevo IN ('ENTREGADO','CANCELADO') THEN
        CALL sp_liberar_mesas_pedido(p_id_pedido);
    END IF;
END$$

-- =====================================================================
-- 4. MÓDULO MESERO   (RF-01 .. RF-05)
-- =====================================================================

-- Menú visible para el mesero: solo productos disponibles, agrupados por categoría
CREATE PROCEDURE sp_mesero_listar_menu(IN p_id_usuario INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'MESERO');
    SELECT c.id_categoria, c.nombre AS categoria,
           p.id_producto, p.nombre, p.descripcion, p.precio
      FROM producto p JOIN categoria c ON c.id_categoria = p.id_categoria
     WHERE p.disponibilidad = TRUE
     ORDER BY c.nombre, p.nombre;
END$$

CREATE PROCEDURE sp_mesero_listar_mesas_libres(IN p_id_usuario INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'MESERO');
    SELECT id_mesa, numero FROM mesa WHERE estado = 'libre' ORDER BY numero;
END$$

-- HU-01: crear pedido asociado a una mesa disponible (estado PENDIENTE)
CREATE PROCEDURE sp_mesero_crear_pedido(
    IN  p_id_usuario INT,
    IN  p_id_mesa    INT,
    OUT p_id_pedido  INT)
BEGIN
    DECLARE v_estado_mesa VARCHAR(20);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

    CALL sp_validar_rol(p_id_usuario, 'MESERO');

    START TRANSACTION;
    SELECT estado INTO v_estado_mesa FROM mesa WHERE id_mesa = p_id_mesa FOR UPDATE;
    IF v_estado_mesa IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'MESA_NO_EXISTE: la mesa indicada no existe';
    END IF;
    IF v_estado_mesa <> 'libre' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'MESA_OCUPADA: la mesa no está disponible';
    END IF;

    INSERT INTO pedido (id_usuario_mesero, estado, fecha_creacion, fecha_ultima_actualizacion)
    VALUES (p_id_usuario, 'PENDIENTE', NOW(), NOW());
    SET p_id_pedido = LAST_INSERT_ID();

    INSERT INTO pedido_mesa (id_pedido, id_mesa) VALUES (p_id_pedido, p_id_mesa);
    UPDATE mesa SET estado = 'ocupada' WHERE id_mesa = p_id_mesa;

    INSERT INTO historial_estado (id_pedido, estado, fecha, id_usuario_cambio)
    VALUES (p_id_pedido, 'PENDIENTE', NOW(), p_id_usuario);
    COMMIT;
END$$

-- HU-02: agregar producto (con cantidad y notas). Si el producto ya está en el
-- pedido se suma la cantidad (porque el diagrama exige un renglón por producto).
CREATE PROCEDURE sp_mesero_agregar_producto(
    IN p_id_usuario  INT,
    IN p_id_pedido   INT,
    IN p_id_producto INT,
    IN p_cantidad    INT,
    IN p_notas       VARCHAR(255))
BEGIN
    DECLARE v_estado  VARCHAR(20);
    DECLARE v_mesero  INT;
    DECLARE v_precio  DECIMAL(10,2);
    DECLARE v_disp    BOOLEAN;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

    CALL sp_validar_rol(p_id_usuario, 'MESERO');
    IF p_cantidad IS NULL OR p_cantidad <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CANTIDAD_INVALIDA: la cantidad debe ser mayor que cero';
    END IF;

    START TRANSACTION;
    SELECT estado, id_usuario_mesero INTO v_estado, v_mesero
      FROM pedido WHERE id_pedido = p_id_pedido FOR UPDATE;
    IF v_estado IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_NO_EXISTE: el pedido indicado no existe';
    END IF;
    IF v_mesero <> p_id_usuario THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ACCESO_DENEGADO: el pedido pertenece a otro mesero';
    END IF;
    IF v_estado <> 'PENDIENTE' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_BLOQUEADO: solo se puede editar un pedido en estado PENDIENTE';
    END IF;

    SELECT precio, disponibilidad INTO v_precio, v_disp
      FROM producto WHERE id_producto = p_id_producto;
    IF v_precio IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PRODUCTO_NO_EXISTE: el producto indicado no existe';
    END IF;
    IF v_disp = FALSE THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PRODUCTO_NO_DISPONIBLE: el producto no está disponible';
    END IF;

    INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, notas, precio_unitario)
    VALUES (p_id_pedido, p_id_producto, p_cantidad, p_notas, v_precio)
    ON DUPLICATE KEY UPDATE
        cantidad = cantidad + VALUES(cantidad),
        notas    = COALESCE(VALUES(notas), notas);

    UPDATE pedido SET fecha_ultima_actualizacion = NOW() WHERE id_pedido = p_id_pedido;
    COMMIT;

    SELECT p_id_pedido AS id_pedido, fn_total_pedido(p_id_pedido) AS total;
END$$

-- HU-03: modificar cantidad / notas de un renglón (solo PENDIENTE)
CREATE PROCEDURE sp_mesero_modificar_detalle(
    IN p_id_usuario INT,
    IN p_id_detalle INT,
    IN p_cantidad   INT,
    IN p_notas      VARCHAR(255))
BEGIN
    DECLARE v_pedido INT;
    DECLARE v_estado VARCHAR(20);
    DECLARE v_mesero INT;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

    CALL sp_validar_rol(p_id_usuario, 'MESERO');
    IF p_cantidad IS NULL OR p_cantidad <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CANTIDAD_INVALIDA: la cantidad debe ser mayor que cero';
    END IF;

    START TRANSACTION;
    SELECT d.id_pedido INTO v_pedido FROM detalle_pedido d WHERE d.id_detalle = p_id_detalle;
    IF v_pedido IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'DETALLE_NO_EXISTE: el renglón indicado no existe';
    END IF;
    SELECT estado, id_usuario_mesero INTO v_estado, v_mesero
      FROM pedido WHERE id_pedido = v_pedido FOR UPDATE;
    IF v_mesero <> p_id_usuario THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ACCESO_DENEGADO: el pedido pertenece a otro mesero';
    END IF;
    IF v_estado <> 'PENDIENTE' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_BLOQUEADO: solo se puede editar un pedido en estado PENDIENTE';
    END IF;

    UPDATE detalle_pedido SET cantidad = p_cantidad, notas = p_notas WHERE id_detalle = p_id_detalle;
    UPDATE pedido SET fecha_ultima_actualizacion = NOW() WHERE id_pedido = v_pedido;
    COMMIT;

    SELECT v_pedido AS id_pedido, fn_total_pedido(v_pedido) AS total;
END$$

-- HU-03: quitar un producto del pedido (solo PENDIENTE)
CREATE PROCEDURE sp_mesero_quitar_producto(IN p_id_usuario INT, IN p_id_detalle INT)
BEGIN
    DECLARE v_pedido INT;
    DECLARE v_estado VARCHAR(20);
    DECLARE v_mesero INT;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

    CALL sp_validar_rol(p_id_usuario, 'MESERO');

    START TRANSACTION;
    SELECT d.id_pedido INTO v_pedido FROM detalle_pedido d WHERE d.id_detalle = p_id_detalle;
    IF v_pedido IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'DETALLE_NO_EXISTE: el renglón indicado no existe';
    END IF;
    SELECT estado, id_usuario_mesero INTO v_estado, v_mesero
      FROM pedido WHERE id_pedido = v_pedido FOR UPDATE;
    IF v_mesero <> p_id_usuario THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ACCESO_DENEGADO: el pedido pertenece a otro mesero';
    END IF;
    IF v_estado <> 'PENDIENTE' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_BLOQUEADO: solo se puede editar un pedido en estado PENDIENTE';
    END IF;

    DELETE FROM detalle_pedido WHERE id_detalle = p_id_detalle;
    UPDATE pedido SET fecha_ultima_actualizacion = NOW() WHERE id_pedido = v_pedido;
    COMMIT;

    SELECT v_pedido AS id_pedido, fn_total_pedido(v_pedido) AS total;
END$$

-- HU-04: marcar como ENTREGADO (solo si está LISTO)
CREATE PROCEDURE sp_mesero_marcar_entregado(IN p_id_usuario INT, IN p_id_pedido INT)
BEGIN
    DECLARE v_mesero INT;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

    CALL sp_validar_rol(p_id_usuario, 'MESERO');

    START TRANSACTION;
    SELECT id_usuario_mesero INTO v_mesero FROM pedido WHERE id_pedido = p_id_pedido FOR UPDATE;
    IF v_mesero IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_NO_EXISTE: el pedido indicado no existe';
    END IF;
    IF v_mesero <> p_id_usuario THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ACCESO_DENEGADO: el pedido pertenece a otro mesero';
    END IF;
    CALL sp_cambiar_estado(p_id_pedido, 'ENTREGADO', p_id_usuario);
    COMMIT;
END$$

-- HU-05: cancelar (solo si no está ENTREGADO; queda el usuario en el historial)
CREATE PROCEDURE sp_mesero_cancelar_pedido(IN p_id_usuario INT, IN p_id_pedido INT)
BEGIN
    DECLARE v_mesero INT;
    DECLARE v_estado VARCHAR(20);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

    CALL sp_validar_rol(p_id_usuario, 'MESERO');

    START TRANSACTION;
    SELECT id_usuario_mesero, estado INTO v_mesero, v_estado
      FROM pedido WHERE id_pedido = p_id_pedido FOR UPDATE;
    IF v_mesero IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_NO_EXISTE: el pedido indicado no existe';
    END IF;
    IF v_mesero <> p_id_usuario THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ACCESO_DENEGADO: el pedido pertenece a otro mesero';
    END IF;
    IF v_estado = 'ENTREGADO' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CANCELACION_NO_PERMITIDA: el pedido ya fue entregado';
    END IF;
    CALL sp_cambiar_estado(p_id_pedido, 'CANCELADO', p_id_usuario);
    COMMIT;
END$$

-- Pedidos del mesero (todos, o filtrados por estado si se envía p_estado)
CREATE PROCEDURE sp_mesero_mis_pedidos(IN p_id_usuario INT, IN p_estado VARCHAR(20))
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'MESERO');
    SELECT * FROM v_pedido_resumen
     WHERE id_usuario_mesero = p_id_usuario
       AND (p_estado IS NULL OR estado = p_estado)
     ORDER BY fecha_creacion DESC;
END$$

-- Pedidos LISTOS para recoger (aviso al mesero, HU-08)
CREATE PROCEDURE sp_mesero_pedidos_listos(IN p_id_usuario INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'MESERO');
    SELECT * FROM v_pedido_resumen
     WHERE id_usuario_mesero = p_id_usuario AND estado = 'LISTO'
     ORDER BY fecha_ultima_actualizacion;
END$$

-- Detalle completo de un pedido propio
CREATE PROCEDURE sp_mesero_ver_pedido(IN p_id_usuario INT, IN p_id_pedido INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'MESERO');
    SELECT * FROM v_pedido_resumen
     WHERE id_pedido = p_id_pedido AND id_usuario_mesero = p_id_usuario;
    SELECT d.id_detalle, pr.nombre AS producto, d.cantidad, d.precio_unitario,
           d.cantidad * d.precio_unitario AS subtotal, d.notas
      FROM detalle_pedido d
      JOIN producto pr ON pr.id_producto = d.id_producto
      JOIN pedido p    ON p.id_pedido = d.id_pedido
     WHERE d.id_pedido = p_id_pedido AND p.id_usuario_mesero = p_id_usuario;
END$$

-- =====================================================================
-- 5. MÓDULO COCINA   (RF-06 .. RF-08)
-- =====================================================================

-- HU-06: cola de pendientes ordenada por fecha de creación (más antiguo primero).
-- Solo aparecen pedidos que ya tienen al menos un producto.
-- Resultado 1: pedidos | Resultado 2: detalle de cada producto
CREATE PROCEDURE sp_cocina_ver_cola(IN p_id_usuario INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'COCINA');
    SELECT p.id_pedido, p.fecha_creacion,
           (SELECT GROUP_CONCAT(m.numero ORDER BY m.numero SEPARATOR ',')
              FROM pedido_mesa pm JOIN mesa m ON m.id_mesa = pm.id_mesa
             WHERE pm.id_pedido = p.id_pedido) AS mesas
      FROM pedido p
     WHERE p.estado = 'PENDIENTE'
       AND EXISTS (SELECT 1 FROM detalle_pedido d WHERE d.id_pedido = p.id_pedido)
     ORDER BY p.fecha_creacion, p.id_pedido;

    SELECT d.id_pedido, pr.nombre AS producto, d.cantidad, d.notas
      FROM detalle_pedido d
      JOIN pedido p    ON p.id_pedido = d.id_pedido
      JOIN producto pr ON pr.id_producto = d.id_producto
     WHERE p.estado = 'PENDIENTE'
     ORDER BY p.fecha_creacion, p.id_pedido, d.id_detalle;
END$$

-- Pedidos que cocina ya tiene en preparación
CREATE PROCEDURE sp_cocina_ver_en_preparacion(IN p_id_usuario INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'COCINA');
    SELECT p.id_pedido, p.fecha_creacion, p.fecha_ultima_actualizacion,
           (SELECT GROUP_CONCAT(m.numero ORDER BY m.numero SEPARATOR ',')
              FROM pedido_mesa pm JOIN mesa m ON m.id_mesa = pm.id_mesa
             WHERE pm.id_pedido = p.id_pedido) AS mesas
      FROM pedido p WHERE p.estado = 'EN_PREPARACION'
     ORDER BY p.fecha_ultima_actualizacion;

    SELECT d.id_pedido, pr.nombre AS producto, d.cantidad, d.notas
      FROM detalle_pedido d
      JOIN pedido p    ON p.id_pedido = d.id_pedido
      JOIN producto pr ON pr.id_producto = d.id_producto
     WHERE p.estado = 'EN_PREPARACION'
     ORDER BY p.fecha_ultima_actualizacion, d.id_pedido, d.id_detalle;
END$$

-- HU-07: PENDIENTE -> EN_PREPARACION
CREATE PROCEDURE sp_cocina_iniciar_preparacion(IN p_id_usuario INT, IN p_id_pedido INT)
BEGIN
    DECLARE v_items INT;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

    CALL sp_validar_rol(p_id_usuario, 'COCINA');

    START TRANSACTION;
    SELECT COUNT(*) INTO v_items FROM detalle_pedido WHERE id_pedido = p_id_pedido;
    IF v_items = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PEDIDO_VACIO: el pedido no tiene productos';
    END IF;
    CALL sp_cambiar_estado(p_id_pedido, 'EN_PREPARACION', p_id_usuario);
    COMMIT;
END$$

-- HU-08: EN_PREPARACION -> LISTO
CREATE PROCEDURE sp_cocina_marcar_listo(IN p_id_usuario INT, IN p_id_pedido INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

    CALL sp_validar_rol(p_id_usuario, 'COCINA');

    START TRANSACTION;
    CALL sp_cambiar_estado(p_id_pedido, 'LISTO', p_id_usuario);
    COMMIT;
END$$

-- =====================================================================
-- 6. MÓDULO ADMINISTRACIÓN   (RF-09 .. RF-14)
-- =====================================================================

-- ---------- Categorías (HU-10) ----------
CREATE PROCEDURE sp_admin_crear_categoria(IN p_id_usuario INT, IN p_nombre VARCHAR(50))
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF p_nombre IS NULL OR TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'DATOS_INVALIDOS: el nombre es obligatorio';
    END IF;
    INSERT INTO categoria (nombre) VALUES (TRIM(p_nombre));
    SELECT LAST_INSERT_ID() AS id_categoria;
END$$

CREATE PROCEDURE sp_admin_editar_categoria(IN p_id_usuario INT, IN p_id_categoria INT, IN p_nombre VARCHAR(50))
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF p_nombre IS NULL OR TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'DATOS_INVALIDOS: el nombre es obligatorio';
    END IF;
    UPDATE categoria SET nombre = TRIM(p_nombre) WHERE id_categoria = p_id_categoria;
    IF ROW_COUNT() = 0 AND NOT EXISTS (SELECT 1 FROM categoria WHERE id_categoria = p_id_categoria) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CATEGORIA_NO_EXISTE: la categoría indicada no existe';
    END IF;
END$$

-- No se puede eliminar una categoría con productos asociados
CREATE PROCEDURE sp_admin_eliminar_categoria(IN p_id_usuario INT, IN p_id_categoria INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF NOT EXISTS (SELECT 1 FROM categoria WHERE id_categoria = p_id_categoria) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CATEGORIA_NO_EXISTE: la categoría indicada no existe';
    END IF;
    IF EXISTS (SELECT 1 FROM producto WHERE id_categoria = p_id_categoria) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CATEGORIA_CON_PRODUCTOS: la categoría tiene productos asociados';
    END IF;
    DELETE FROM categoria WHERE id_categoria = p_id_categoria;
END$$

CREATE PROCEDURE sp_admin_listar_categorias(IN p_id_usuario INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    SELECT c.id_categoria, c.nombre, COUNT(p.id_producto) AS productos
      FROM categoria c LEFT JOIN producto p ON p.id_categoria = c.id_categoria
     GROUP BY c.id_categoria, c.nombre ORDER BY c.nombre;
END$$

-- ---------- Productos (HU-09) ----------
CREATE PROCEDURE sp_admin_crear_producto(
    IN p_id_usuario  INT,
    IN p_nombre      VARCHAR(100),
    IN p_descripcion VARCHAR(255),
    IN p_precio      DECIMAL(10,2),
    IN p_id_categoria INT,
    IN p_disponible  BOOLEAN)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF p_nombre IS NULL OR TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'DATOS_INVALIDOS: el nombre es obligatorio';
    END IF;
    IF p_precio IS NULL OR p_precio < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PRECIO_INVALIDO: el precio no puede ser negativo';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM categoria WHERE id_categoria = p_id_categoria) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CATEGORIA_NO_EXISTE: la categoría indicada no existe';
    END IF;
    INSERT INTO producto (nombre, descripcion, precio, disponibilidad, id_categoria)
    VALUES (TRIM(p_nombre), p_descripcion, p_precio, COALESCE(p_disponible, TRUE), p_id_categoria);
    SELECT LAST_INSERT_ID() AS id_producto;
END$$

CREATE PROCEDURE sp_admin_editar_producto(
    IN p_id_usuario   INT,
    IN p_id_producto  INT,
    IN p_nombre       VARCHAR(100),
    IN p_descripcion  VARCHAR(255),
    IN p_precio       DECIMAL(10,2),
    IN p_id_categoria INT,
    IN p_disponible   BOOLEAN)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF NOT EXISTS (SELECT 1 FROM producto WHERE id_producto = p_id_producto) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PRODUCTO_NO_EXISTE: el producto indicado no existe';
    END IF;
    IF p_nombre IS NULL OR TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'DATOS_INVALIDOS: el nombre es obligatorio';
    END IF;
    IF p_precio IS NULL OR p_precio < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PRECIO_INVALIDO: el precio no puede ser negativo';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM categoria WHERE id_categoria = p_id_categoria) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CATEGORIA_NO_EXISTE: la categoría indicada no existe';
    END IF;
    UPDATE producto
       SET nombre = TRIM(p_nombre), descripcion = p_descripcion, precio = p_precio,
           id_categoria = p_id_categoria, disponibilidad = COALESCE(p_disponible, disponibilidad)
     WHERE id_producto = p_id_producto;
END$$

CREATE PROCEDURE sp_admin_activar_producto(IN p_id_usuario INT, IN p_id_producto INT, IN p_disponible BOOLEAN)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF NOT EXISTS (SELECT 1 FROM producto WHERE id_producto = p_id_producto) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PRODUCTO_NO_EXISTE: el producto indicado no existe';
    END IF;
    UPDATE producto SET disponibilidad = p_disponible WHERE id_producto = p_id_producto;
END$$

-- Eliminar: si el producto ya fue usado en pedidos no se borra (protege el
-- historial de ventas); en ese caso se recomienda desactivarlo.
CREATE PROCEDURE sp_admin_eliminar_producto(IN p_id_usuario INT, IN p_id_producto INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF NOT EXISTS (SELECT 1 FROM producto WHERE id_producto = p_id_producto) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PRODUCTO_NO_EXISTE: el producto indicado no existe';
    END IF;
    IF EXISTS (SELECT 1 FROM detalle_pedido WHERE id_producto = p_id_producto) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PRODUCTO_CON_HISTORIAL: el producto ya fue pedido; desactívelo en lugar de eliminarlo';
    END IF;
    DELETE FROM producto WHERE id_producto = p_id_producto;
END$$

CREATE PROCEDURE sp_admin_listar_productos(IN p_id_usuario INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    SELECT p.id_producto, p.nombre, p.descripcion, p.precio, p.disponibilidad,
           c.id_categoria, c.nombre AS categoria
      FROM producto p JOIN categoria c ON c.id_categoria = p.id_categoria
     ORDER BY c.nombre, p.nombre;
END$$

-- ---------- Mesas (HU-11) ----------
CREATE PROCEDURE sp_admin_crear_mesa(IN p_id_usuario INT, IN p_numero INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF p_numero IS NULL OR p_numero <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'DATOS_INVALIDOS: el número de mesa debe ser positivo';
    END IF;
    IF EXISTS (SELECT 1 FROM mesa WHERE numero = p_numero) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'MESA_DUPLICADA: ya existe una mesa con ese número';
    END IF;
    INSERT INTO mesa (numero, estado) VALUES (p_numero, 'libre');
    SELECT LAST_INSERT_ID() AS id_mesa;
END$$

CREATE PROCEDURE sp_admin_editar_mesa(IN p_id_usuario INT, IN p_id_mesa INT, IN p_numero INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF NOT EXISTS (SELECT 1 FROM mesa WHERE id_mesa = p_id_mesa) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'MESA_NO_EXISTE: la mesa indicada no existe';
    END IF;
    IF p_numero IS NULL OR p_numero <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'DATOS_INVALIDOS: el número de mesa debe ser positivo';
    END IF;
    IF EXISTS (SELECT 1 FROM mesa WHERE numero = p_numero AND id_mesa <> p_id_mesa) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'MESA_DUPLICADA: ya existe una mesa con ese número';
    END IF;
    UPDATE mesa SET numero = p_numero WHERE id_mesa = p_id_mesa;
END$$

-- Cambio manual de estado (p. ej. corregir una mesa). No permite liberar una
-- mesa que todavía tiene un pedido activo.
CREATE PROCEDURE sp_admin_cambiar_estado_mesa(IN p_id_usuario INT, IN p_id_mesa INT, IN p_estado VARCHAR(20))
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    IF NOT EXISTS (SELECT 1 FROM mesa WHERE id_mesa = p_id_mesa) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'MESA_NO_EXISTE: la mesa indicada no existe';
    END IF;
    IF p_estado NOT IN ('libre','ocupada') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ESTADO_INVALIDO: use libre u ocupada';
    END IF;
    IF p_estado = 'libre' AND EXISTS (
        SELECT 1 FROM pedido_mesa pm JOIN pedido p ON p.id_pedido = pm.id_pedido
         WHERE pm.id_mesa = p_id_mesa AND p.estado IN ('PENDIENTE','EN_PREPARACION','LISTO')) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'MESA_CON_PEDIDO_ACTIVO: la mesa tiene un pedido en curso';
    END IF;
    UPDATE mesa SET estado = p_estado WHERE id_mesa = p_id_mesa;
END$$

CREATE PROCEDURE sp_admin_listar_mesas(IN p_id_usuario INT)
BEGIN
    CALL sp_validar_rol(p_id_usuario, 'ADMINISTRADOR');
    SELECT id_mesa, numero, estado FROM mesa ORDER BY numero;
END$$

-- ---------- Usuarios y roles (HU-12) ----------
-- La aplicación calcula el hash bcrypt y lo envía aquí (RNF-05).
CREATE PROCEDURE sp_admin_crear_usuario(
    IN p_id_admin   INT,
    IN p_nombre     VARCHAR(100),
    IN p_login      VARCHAR(50),
    IN p_hash       VARCHAR(255),
    IN p_rol        VARCHAR(30))
BEGIN
    DECLARE v_rol INT;
    CALL sp_validar_rol(p_id_admin, 'ADMINISTRADOR');
    IF p_nombre IS NULL OR TRIM(p_nombre) = '' OR p_login IS NULL OR TRIM(p_login) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'DATOS_INVALIDOS: nombre y usuario son obligatorios';
    END IF;
    -- rechaza texto plano evidente: exige formato bcrypt ($2a$/$2b$/$2y$ + 60 caracteres)
    IF p_hash IS NULL OR p_hash NOT REGEXP '^\\$2[aby]\\$[0-9]{2}\\$.{53}$' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'HASH_INVALIDO: la contraseña debe llegar cifrada (bcrypt)';
    END IF;
    IF EXISTS (SELECT 1 FROM usuario WHERE usuario_login = p_login) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'USUARIO_DUPLICADO: ya existe ese nombre de usuario';
    END IF;
    SELECT id_rol INTO v_rol FROM rol WHERE nombre = UPPER(p_rol);
    IF v_rol IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ROL_NO_EXISTE: use MESERO, COCINA o ADMINISTRADOR';
    END IF;
    INSERT INTO usuario (nombre, usuario_login, contrasena_hash, activo, id_rol)
    VALUES (TRIM(p_nombre), TRIM(p_login), p_hash, TRUE, v_rol);
    SELECT LAST_INSERT_ID() AS id_usuario;
END$$

CREATE PROCEDURE sp_admin_editar_usuario(
    IN p_id_admin   INT,
    IN p_id_usuario INT,
    IN p_nombre     VARCHAR(100),
    IN p_rol        VARCHAR(30))
BEGIN
    DECLARE v_rol INT;
    CALL sp_validar_rol(p_id_admin, 'ADMINISTRADOR');
    IF NOT EXISTS (SELECT 1 FROM usuario WHERE id_usuario = p_id_usuario) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'USUARIO_NO_EXISTE: el usuario indicado no existe';
    END IF;
    SELECT id_rol INTO v_rol FROM rol WHERE nombre = UPPER(p_rol);
    IF v_rol IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ROL_NO_EXISTE: use MESERO, COCINA o ADMINISTRADOR';
    END IF;
    IF p_id_admin = p_id_usuario AND UPPER(p_rol) <> 'ADMINISTRADOR' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'OPERACION_NO_PERMITIDA: un administrador no puede quitarse su propio rol';
    END IF;
    UPDATE usuario SET nombre = TRIM(p_nombre), id_rol = v_rol WHERE id_usuario = p_id_usuario;
END$$

CREATE PROCEDURE sp_admin_cambiar_contrasena(IN p_id_admin INT, IN p_id_usuario INT, IN p_hash VARCHAR(255))
BEGIN
    CALL sp_validar_rol(p_id_admin, 'ADMINISTRADOR');
    IF NOT EXISTS (SELECT 1 FROM usuario WHERE id_usuario = p_id_usuario) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'USUARIO_NO_EXISTE: el usuario indicado no existe';
    END IF;
    IF p_hash IS NULL OR p_hash NOT REGEXP '^\\$2[aby]\\$[0-9]{2}\\$.{53}$' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'HASH_INVALIDO: la contraseña debe llegar cifrada (bcrypt)';
    END IF;
    UPDATE usuario SET contrasena_hash = p_hash WHERE id_usuario = p_id_usuario;
END$$

CREATE PROCEDURE sp_admin_activar_usuario(IN p_id_admin INT, IN p_id_usuario INT, IN p_activo BOOLEAN)
BEGIN
    CALL sp_validar_rol(p_id_admin, 'ADMINISTRADOR');
    IF NOT EXISTS (SELECT 1 FROM usuario WHERE id_usuario = p_id_usuario) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'USUARIO_NO_EXISTE: el usuario indicado no existe';
    END IF;
    IF p_id_admin = p_id_usuario AND p_activo = FALSE THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'OPERACION_NO_PERMITIDA: un administrador no puede desactivarse a sí mismo';
    END IF;
    UPDATE usuario SET activo = p_activo WHERE id_usuario = p_id_usuario;
END$$

CREATE PROCEDURE sp_admin_listar_usuarios(IN p_id_admin INT)
BEGIN
    CALL sp_validar_rol(p_id_admin, 'ADMINISTRADOR');
    SELECT u.id_usuario, u.nombre, u.usuario_login, u.activo, r.nombre AS rol
      FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
     ORDER BY r.nombre, u.nombre;
END$$

-- ---------- Reportes (HU-13, HU-14) ----------
-- Ventas: solo cuentan pedidos ENTREGADOS cuya fecha de entrega cae en el rango.
-- Filtros opcionales por categoría y producto (NULL = todos).
-- Resultado 1: totales | 2: por categoría | 3: por producto
CREATE PROCEDURE sp_admin_reporte_ventas(
    IN p_id_admin     INT,
    IN p_fecha_ini    DATE,
    IN p_fecha_fin    DATE,
    IN p_id_categoria INT,
    IN p_id_producto  INT)
BEGIN
    CALL sp_validar_rol(p_id_admin, 'ADMINISTRADOR');
    IF p_fecha_ini IS NULL OR p_fecha_fin IS NULL OR p_fecha_fin < p_fecha_ini THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'RANGO_INVALIDO: revise las fechas del reporte';
    END IF;

    DROP TEMPORARY TABLE IF EXISTS tmp_ventas;
    CREATE TEMPORARY TABLE tmp_ventas AS
    SELECT p.id_pedido, pr.id_producto, pr.nombre AS producto,
           c.id_categoria, c.nombre AS categoria,
           d.cantidad, d.cantidad * d.precio_unitario AS subtotal
      FROM pedido p
      JOIN historial_estado h ON h.id_pedido = p.id_pedido AND h.estado = 'ENTREGADO'
      JOIN detalle_pedido d   ON d.id_pedido = p.id_pedido
      JOIN producto pr        ON pr.id_producto = d.id_producto
      JOIN categoria c        ON c.id_categoria = pr.id_categoria
     WHERE p.estado = 'ENTREGADO'
       AND h.fecha >= p_fecha_ini AND h.fecha < DATE_ADD(p_fecha_fin, INTERVAL 1 DAY)
       AND (p_id_categoria IS NULL OR c.id_categoria = p_id_categoria)
       AND (p_id_producto  IS NULL OR pr.id_producto = p_id_producto);

    SELECT COUNT(DISTINCT id_pedido)  AS pedidos_entregados,
           COALESCE(SUM(cantidad), 0) AS productos_vendidos,
           COALESCE(SUM(subtotal), 0) AS total_ventas
      FROM tmp_ventas;

    SELECT categoria, SUM(cantidad) AS productos_vendidos, SUM(subtotal) AS total_ventas
      FROM tmp_ventas GROUP BY id_categoria, categoria ORDER BY total_ventas DESC;

    SELECT producto, categoria, SUM(cantidad) AS unidades_vendidas, SUM(subtotal) AS total_ventas
      FROM tmp_ventas GROUP BY id_producto, producto, categoria ORDER BY total_ventas DESC;

    DROP TEMPORARY TABLE tmp_ventas;
END$$

-- Tiempos de preparación calculados a partir de historial_estado (HU-14).
-- Resultado 1: detalle por pedido | 2: promedio del periodo (en minutos)
CREATE PROCEDURE sp_admin_reporte_tiempos(
    IN p_id_admin  INT,
    IN p_fecha_ini DATE,
    IN p_fecha_fin DATE)
BEGIN
    CALL sp_validar_rol(p_id_admin, 'ADMINISTRADOR');
    IF p_fecha_ini IS NULL OR p_fecha_fin IS NULL OR p_fecha_fin < p_fecha_ini THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'RANGO_INVALIDO: revise las fechas del reporte';
    END IF;

    DROP TEMPORARY TABLE IF EXISTS tmp_tiempos;
    CREATE TEMPORARY TABLE tmp_tiempos AS
    SELECT p.id_pedido,
           MIN(CASE WHEN h.estado = 'PENDIENTE'      THEN h.fecha END) AS t_creado,
           MIN(CASE WHEN h.estado = 'EN_PREPARACION' THEN h.fecha END) AS t_prep,
           MIN(CASE WHEN h.estado = 'LISTO'          THEN h.fecha END) AS t_listo,
           MIN(CASE WHEN h.estado = 'ENTREGADO'      THEN h.fecha END) AS t_entregado
      FROM pedido p JOIN historial_estado h ON h.id_pedido = p.id_pedido
     WHERE p.estado <> 'CANCELADO'
       AND p.fecha_creacion >= p_fecha_ini
       AND p.fecha_creacion <  DATE_ADD(p_fecha_fin, INTERVAL 1 DAY)
     GROUP BY p.id_pedido;

    SELECT id_pedido, t_creado, t_prep, t_listo, t_entregado,
           TIMESTAMPDIFF(SECOND, t_creado, t_prep)  / 60 AS min_espera_en_cola,
           TIMESTAMPDIFF(SECOND, t_prep,  t_listo)  / 60 AS min_preparacion,
           TIMESTAMPDIFF(SECOND, t_listo, t_entregado) / 60 AS min_espera_entrega,
           TIMESTAMPDIFF(SECOND, t_creado, t_entregado) / 60 AS min_total
      FROM tmp_tiempos ORDER BY t_creado;

    SELECT COUNT(t_listo) AS pedidos_preparados,
           ROUND(AVG(TIMESTAMPDIFF(SECOND, t_creado, t_prep)) / 60, 2)      AS prom_min_espera_en_cola,
           ROUND(AVG(TIMESTAMPDIFF(SECOND, t_prep,  t_listo)) / 60, 2)      AS prom_min_preparacion,
           ROUND(AVG(TIMESTAMPDIFF(SECOND, t_listo, t_entregado)) / 60, 2)  AS prom_min_espera_entrega,
           ROUND(AVG(TIMESTAMPDIFF(SECOND, t_creado, t_entregado)) / 60, 2) AS prom_min_total
      FROM tmp_tiempos;

    DROP TEMPORARY TABLE tmp_tiempos;
END$$

-- Consulta de auditoría: historial completo de un pedido
CREATE PROCEDURE sp_admin_ver_historial_pedido(IN p_id_admin INT, IN p_id_pedido INT)
BEGIN
    CALL sp_validar_rol(p_id_admin, 'ADMINISTRADOR');
    SELECT h.id_historial, h.estado, h.fecha, u.nombre AS usuario, r.nombre AS rol
      FROM historial_estado h
      JOIN usuario u ON u.id_usuario = h.id_usuario_cambio
      JOIN rol r     ON r.id_rol = u.id_rol
     WHERE h.id_pedido = p_id_pedido
     ORDER BY h.fecha, h.id_historial;
END$$

-- =====================================================================
-- 7. AUTENTICACIÓN   (RF-16)
-- =====================================================================
-- El backend de la app llama a este procedimiento con el usuario_login, obtiene
-- el hash y lo compara con bcrypt en la aplicación; si coincide emite el JWT
-- con id_usuario y rol. Usuarios inactivos no devuelven filas.
CREATE PROCEDURE sp_auth_obtener_credenciales(IN p_login VARCHAR(50))
BEGIN
    SELECT u.id_usuario, u.nombre, u.contrasena_hash, r.nombre AS rol
      FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
     WHERE u.usuario_login = p_login AND u.activo = TRUE;
END$$

DELIMITER ;

-- =====================================================================
-- 8. DATOS SEMILLA (demo)
--    Contraseñas de prueba: Admin2026* / Mesero2026* / Cocina2026*
--    (guardadas como hash bcrypt)
-- =====================================================================
INSERT INTO rol (nombre) VALUES ('MESERO'), ('COCINA'), ('ADMINISTRADOR');

INSERT INTO usuario (nombre, usuario_login, contrasena_hash, activo, id_rol) VALUES
('Administrador General', 'admin',   '$2b$10$Nbbq0HK9kUZHK2Vlu7ViLennIDCO3J3bD662hMtdIJ1xGXkWONvgO', TRUE, (SELECT id_rol FROM rol WHERE nombre='ADMINISTRADOR')),
('Mesero Uno',            'mesero1', '$2b$10$D.DmWHIDeYQcCqa7xIQ/beyholsBjZPoD1QVlCN70yrd7D4eTF.Hm', TRUE, (SELECT id_rol FROM rol WHERE nombre='MESERO')),
('Mesero Dos',            'mesero2', '$2b$10$D.DmWHIDeYQcCqa7xIQ/beyholsBjZPoD1QVlCN70yrd7D4eTF.Hm', TRUE, (SELECT id_rol FROM rol WHERE nombre='MESERO')),
('Cocinero Uno',          'cocina1', '$2b$10$59zlePZPYCR1h3x2orM/Sub64R11yXWCeWa1/ADH8cfZ8gg7VU3Gq', TRUE, (SELECT id_rol FROM rol WHERE nombre='COCINA'));

INSERT INTO mesa (numero, estado) VALUES (1,'libre'),(2,'libre'),(3,'libre'),(4,'libre'),(5,'libre');

INSERT INTO categoria (nombre) VALUES ('Entradas'), ('Platos fuertes'), ('Bebidas'), ('Postres');

INSERT INTO producto (nombre, descripcion, precio, disponibilidad, id_categoria) VALUES
('Nuggets de pollo',   '8 unidades con salsa',            12000, TRUE, (SELECT id_categoria FROM categoria WHERE nombre='Entradas')),
('Papas fritas',       'Porción grande',                   8000, TRUE, (SELECT id_categoria FROM categoria WHERE nombre='Entradas')),
('Hamburguesa clásica','Carne, queso, lechuga y tomate',  22000, TRUE, (SELECT id_categoria FROM categoria WHERE nombre='Platos fuertes')),
('Perro caliente',     'Salchicha, papitas y salsas',     15000, TRUE, (SELECT id_categoria FROM categoria WHERE nombre='Platos fuertes')),
('Gaseosa',            '400 ml',                           4500, TRUE, (SELECT id_categoria FROM categoria WHERE nombre='Bebidas')),
('Limonada natural',   '450 ml',                           6000, TRUE, (SELECT id_categoria FROM categoria WHERE nombre='Bebidas')),
('Helado de vainilla', 'Copa con topping',                 7000, TRUE, (SELECT id_categoria FROM categoria WHERE nombre='Postres')),
('Brownie',            'Con salsa de chocolate',           9000, FALSE,(SELECT id_categoria FROM categoria WHERE nombre='Postres'));