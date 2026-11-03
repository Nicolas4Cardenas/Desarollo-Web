-- Ejecutar DESPUÉS de backend_original.sql. No borra datos existentes.
USE poli_restaurante;
CREATE TABLE IF NOT EXISTS nicolas_reporte_guardado (
 id_reporte INT AUTO_INCREMENT PRIMARY KEY, tipo ENUM('VENTAS','TIEMPOS') NOT NULL,
 nombre VARCHAR(100) NOT NULL, fecha_inicio DATE NOT NULL, fecha_fin DATE NOT NULL,
 filtro_categoria INT NULL, filtro_producto INT NULL,
 creado_por INT NOT NULL, creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (creado_por) REFERENCES usuario(id_usuario)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS nicolas_auditoria (
 id_auditoria BIGINT AUTO_INCREMENT PRIMARY KEY, entidad VARCHAR(40) NOT NULL,
 registro_id INT NOT NULL, accion VARCHAR(20) NOT NULL,
 antes_json JSON NULL, despues_json JSON NULL,
 actor_id INT NOT NULL, fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (actor_id) REFERENCES usuario(id_usuario)
) ENGINE=InnoDB;
-- Los triggers originales protegen historial_estado. Para habilitar HU-15 CRUD
-- conservamos las correcciones/borrados en nicolas_auditoria desde la aplicación.
DROP TRIGGER IF EXISTS trg_historial_no_update;
DROP TRIGGER IF EXISTS trg_historial_no_delete;
