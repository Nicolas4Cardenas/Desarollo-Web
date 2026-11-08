-- OPCIONAL: MySQL 8.0.16+. Ejecutar en Workbench como instalador/root.
-- Base NUEVA para el backend driver. No reutiliza ni borra las bases anteriores.
-- Sin triggers, funciones, requisito SUPER ni migraciones Alembic.
CREATE DATABASE IF NOT EXISTS polirestaurante_driver CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE polirestaurante_driver;
CREATE TABLE IF NOT EXISTS sistema (
 id BIGINT PRIMARY KEY, version INT NOT NULL, creado VARCHAR(27) NOT NULL, CHECK(id=1)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS usuario (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(100) NOT NULL,
 login VARCHAR(40) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL,
 rol VARCHAR(20) NOT NULL, activo TINYINT NOT NULL DEFAULT 1,
 fallos INT NOT NULL DEFAULT 0, bloqueado_hasta VARCHAR(27), debe_cambiar TINYINT NOT NULL DEFAULT 0,
 CHECK(rol IN ('ADMINISTRADOR','MESERO','COCINA')), CHECK(activo IN (0,1)), CHECK(debe_cambiar IN (0,1))
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS sesion (
 token_hash CHAR(64) PRIMARY KEY, usuario_id BIGINT NOT NULL, creado VARCHAR(27) NOT NULL, expira VARCHAR(27) NOT NULL,
 FOREIGN KEY(usuario_id) REFERENCES usuario(id), INDEX ix_sesion_usuario(usuario_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS categoria (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS producto (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(100) NOT NULL, descripcion VARCHAR(255) NOT NULL,
 precio_centavos BIGINT NOT NULL, categoria_id BIGINT NOT NULL,
 disponible TINYINT NOT NULL DEFAULT 1, activo TINYINT NOT NULL DEFAULT 1,
 FOREIGN KEY(categoria_id) REFERENCES categoria(id), CHECK(precio_centavos BETWEEN 1 AND 9999999999),
 CHECK(disponible IN (0,1)), CHECK(activo IN (0,1))
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS mesa (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, numero INT NOT NULL UNIQUE, capacidad INT NOT NULL,
 activa TINYINT NOT NULL DEFAULT 1, CHECK(numero BETWEEN 1 AND 9999),
 CHECK(capacidad BETWEEN 1 AND 100), CHECK(activa IN (0,1))
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS pedido (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, responsable_id BIGINT NOT NULL, cocinero_id BIGINT, mesa_id BIGINT,
 tipo VARCHAR(10) NOT NULL, estado VARCHAR(20) NOT NULL, creado VARCHAR(27) NOT NULL,
 actualizado VARCHAR(27) NOT NULL, version INT NOT NULL DEFAULT 1, motivo_cancelacion VARCHAR(255),
 FOREIGN KEY(responsable_id) REFERENCES usuario(id), FOREIGN KEY(cocinero_id) REFERENCES usuario(id),
 FOREIGN KEY(mesa_id) REFERENCES mesa(id), CHECK(tipo IN ('SALON','LLEVAR')),
 CHECK(estado IN ('PENDIENTE','EN_PREPARACION','LISTO','ENTREGADO','CANCELADO')),
 CHECK((tipo='SALON' AND mesa_id IS NOT NULL) OR (tipo='LLEVAR' AND mesa_id IS NULL)),
 INDEX ix_pedido_estado_fecha(estado,creado,id), INDEX ix_pedido_responsable(responsable_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS ocupacion (
 mesa_id BIGINT PRIMARY KEY, pedido_id BIGINT NOT NULL UNIQUE,
 FOREIGN KEY(mesa_id) REFERENCES mesa(id), FOREIGN KEY(pedido_id) REFERENCES pedido(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS detalle (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, pedido_id BIGINT NOT NULL, producto_id BIGINT NOT NULL,
 categoria_id BIGINT NOT NULL, producto_nombre VARCHAR(100) NOT NULL, categoria_nombre VARCHAR(50) NOT NULL,
 precio_centavos BIGINT NOT NULL, cantidad INT NOT NULL, notas VARCHAR(255) NOT NULL,
 FOREIGN KEY(pedido_id) REFERENCES pedido(id), FOREIGN KEY(producto_id) REFERENCES producto(id),
 FOREIGN KEY(categoria_id) REFERENCES categoria(id), CHECK(precio_centavos BETWEEN 1 AND 9999999999),
 CHECK(cantidad BETWEEN 1 AND 99), INDEX ix_detalle_pedido(pedido_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS historial (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, pedido_id BIGINT NOT NULL, estado VARCHAR(20) NOT NULL,
 usuario_id BIGINT NOT NULL, fecha VARCHAR(27) NOT NULL, motivo VARCHAR(255) NOT NULL,
 FOREIGN KEY(pedido_id) REFERENCES pedido(id), FOREIGN KEY(usuario_id) REFERENCES usuario(id),
 CHECK(estado IN ('PENDIENTE','EN_PREPARACION','LISTO','ENTREGADO','CANCELADO')), INDEX ix_historial_pedido(pedido_id,id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS auditoria (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, usuario_id BIGINT NOT NULL, accion VARCHAR(60) NOT NULL,
 entidad VARCHAR(30) NOT NULL, entidad_id BIGINT, fecha VARCHAR(27) NOT NULL, descripcion TEXT NOT NULL,
 FOREIGN KEY(usuario_id) REFERENCES usuario(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS operacion (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, usuario_id BIGINT NOT NULL, clave CHAR(36) NOT NULL,
 huella CHAR(64) NOT NULL, resultado TEXT NOT NULL, fecha VARCHAR(27) NOT NULL,
 FOREIGN KEY(usuario_id) REFERENCES usuario(id), UNIQUE(usuario_id,clave)
) ENGINE=InnoDB;
-- Única semilla: una fila técnica de versión y bloqueo. No hay datos comerciales.
INSERT INTO sistema(id,version,creado) SELECT 1,1,CONCAT(DATE_FORMAT(UTC_TIMESTAMP(6),'%Y-%m-%dT%H:%i:%s.%f'),'Z')
WHERE NOT EXISTS (SELECT 1 FROM sistema WHERE id=1);
SELECT version FROM sistema WHERE id=1;
SHOW TABLES;
