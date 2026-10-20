-- Esquema vacío, versión 1. No contiene usuarios, mesas, productos ni pedidos ficticios.
CREATE TABLE IF NOT EXISTS sistema (
 id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, creado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usuario (
 id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
 login TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL,
 rol TEXT NOT NULL CHECK(rol IN ('ADMINISTRADOR','MESERO','COCINA')),
 activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1)),
 fallos INTEGER NOT NULL DEFAULT 0, bloqueado_hasta TEXT,
 debe_cambiar INTEGER NOT NULL DEFAULT 0 CHECK(debe_cambiar IN (0,1))
);
CREATE TABLE IF NOT EXISTS sesion (
 token_hash TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuario(id),
 creado TEXT NOT NULL, expira TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS categoria (
 id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
);
CREATE TABLE IF NOT EXISTS producto (
 id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, descripcion TEXT NOT NULL,
 precio_centavos INTEGER NOT NULL CHECK(precio_centavos BETWEEN 1 AND 9999999999),
 categoria_id INTEGER NOT NULL REFERENCES categoria(id),
 disponible INTEGER NOT NULL DEFAULT 1 CHECK(disponible IN (0,1)),
 activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1))
);
CREATE TABLE IF NOT EXISTS mesa (
 id INTEGER PRIMARY KEY AUTOINCREMENT, numero INTEGER NOT NULL UNIQUE CHECK(numero BETWEEN 1 AND 9999),
 capacidad INTEGER NOT NULL CHECK(capacidad BETWEEN 1 AND 100),
 activa INTEGER NOT NULL DEFAULT 1 CHECK(activa IN (0,1))
);
CREATE TABLE IF NOT EXISTS pedido (
 id INTEGER PRIMARY KEY AUTOINCREMENT, responsable_id INTEGER NOT NULL REFERENCES usuario(id),
 cocinero_id INTEGER REFERENCES usuario(id), mesa_id INTEGER REFERENCES mesa(id),
 tipo TEXT NOT NULL CHECK(tipo IN ('SALON','LLEVAR')),
 estado TEXT NOT NULL CHECK(estado IN ('PENDIENTE','EN_PREPARACION','LISTO','ENTREGADO','CANCELADO')),
 creado TEXT NOT NULL, actualizado TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
 motivo_cancelacion TEXT,
 CHECK((tipo='SALON' AND mesa_id IS NOT NULL) OR (tipo='LLEVAR' AND mesa_id IS NULL))
);
CREATE TABLE IF NOT EXISTS ocupacion (
 mesa_id INTEGER PRIMARY KEY REFERENCES mesa(id),
 pedido_id INTEGER NOT NULL UNIQUE REFERENCES pedido(id)
);
CREATE TABLE IF NOT EXISTS detalle (
 id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER NOT NULL REFERENCES pedido(id),
 producto_id INTEGER NOT NULL REFERENCES producto(id), categoria_id INTEGER NOT NULL REFERENCES categoria(id),
 producto_nombre TEXT NOT NULL, categoria_nombre TEXT NOT NULL,
 precio_centavos INTEGER NOT NULL CHECK(precio_centavos BETWEEN 1 AND 9999999999),
 cantidad INTEGER NOT NULL CHECK(cantidad BETWEEN 1 AND 99), notas TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historial (
 id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER NOT NULL REFERENCES pedido(id),
 estado TEXT NOT NULL CHECK(estado IN ('PENDIENTE','EN_PREPARACION','LISTO','ENTREGADO','CANCELADO')),
 usuario_id INTEGER NOT NULL REFERENCES usuario(id), fecha TEXT NOT NULL, motivo TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auditoria (
 id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL REFERENCES usuario(id),
 accion TEXT NOT NULL, entidad TEXT NOT NULL, entidad_id INTEGER, fecha TEXT NOT NULL, descripcion TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operacion (
 id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL REFERENCES usuario(id),
 clave TEXT NOT NULL, huella TEXT NOT NULL, resultado TEXT NOT NULL, fecha TEXT NOT NULL,
 UNIQUE(usuario_id,clave)
);
CREATE INDEX IF NOT EXISTS ix_pedido_estado_fecha ON pedido(estado,creado,id);
CREATE INDEX IF NOT EXISTS ix_pedido_responsable ON pedido(responsable_id);
CREATE INDEX IF NOT EXISTS ix_detalle_pedido ON detalle(pedido_id);
CREATE INDEX IF NOT EXISTS ix_historial_pedido ON historial(pedido_id,id);
CREATE INDEX IF NOT EXISTS ix_sesion_usuario ON sesion(usuario_id);
CREATE TRIGGER IF NOT EXISTS historial_sin_update BEFORE UPDATE ON historial
BEGIN SELECT RAISE(ABORT,'El historial no se modifica'); END;
CREATE TRIGGER IF NOT EXISTS historial_sin_delete BEFORE DELETE ON historial
BEGIN SELECT RAISE(ABORT,'El historial no se elimina'); END;
CREATE TRIGGER IF NOT EXISTS auditoria_sin_update BEFORE UPDATE ON auditoria
BEGIN SELECT RAISE(ABORT,'La auditoria no se modifica'); END;
CREATE TRIGGER IF NOT EXISTS auditoria_sin_delete BEFORE DELETE ON auditoria
BEGIN SELECT RAISE(ABORT,'La auditoria no se elimina'); END;
INSERT OR IGNORE INTO sistema(id,version,creado) VALUES(1,1,strftime('%Y-%m-%dT%H:%M:%fZ','now'));
