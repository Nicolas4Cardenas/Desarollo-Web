-- OPCIONAL. Ejecutar como root después de mysql_01_esquema.sql.
-- Reemplazar TODAS las apariciones de TU_CLAVE_PRIVADA_DRIVER antes de ejecutar.
-- Este usuario es la CONEXIÓN del programa; NO es un rol del restaurante.
CREATE USER IF NOT EXISTS 'poli_driver_app'@'localhost' IDENTIFIED BY 'TU_CLAVE_PRIVADA_DRIVER';
ALTER USER 'poli_driver_app'@'localhost' IDENTIFIED BY 'TU_CLAVE_PRIVADA_DRIVER';
CREATE USER IF NOT EXISTS 'poli_driver_app'@'127.0.0.1' IDENTIFIED BY 'TU_CLAVE_PRIVADA_DRIVER';
ALTER USER 'poli_driver_app'@'127.0.0.1' IDENTIFIED BY 'TU_CLAVE_PRIVADA_DRIVER';
GRANT SELECT,UPDATE ON polirestaurante_driver.sistema TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT,UPDATE,DELETE ON polirestaurante_driver.usuario TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT,UPDATE,DELETE ON polirestaurante_driver.sesion TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT,UPDATE,DELETE ON polirestaurante_driver.categoria TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT,UPDATE,DELETE ON polirestaurante_driver.producto TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT,UPDATE,DELETE ON polirestaurante_driver.mesa TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT,UPDATE,DELETE ON polirestaurante_driver.pedido TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT,UPDATE,DELETE ON polirestaurante_driver.ocupacion TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT,UPDATE,DELETE ON polirestaurante_driver.detalle TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
-- Auditoría y respuestas de reintentos son de solo inserción/consulta.
GRANT SELECT,INSERT ON polirestaurante_driver.historial TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT ON polirestaurante_driver.auditoria TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
GRANT SELECT,INSERT ON polirestaurante_driver.operacion TO 'poli_driver_app'@'localhost','poli_driver_app'@'127.0.0.1';
-- No se conceden SUPER, CREATE ROUTINE, TRIGGER, DROP ni ALTER.
-- Si ya usabas estas cuentas con permisos más amplios, revísalos con SHOW GRANTS.
SHOW GRANTS FOR 'poli_driver_app'@'127.0.0.1';
