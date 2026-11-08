# Validación de la entrega · 20 de octubre de 2026

## Comprobaciones realizadas

- 38 pruebas de servicio con SQL directo y SQLite temporal: HU01–HU05, tres roles,
  precios históricos, versiones, reintentos, concurrencia, rollback y protección de auditoría.
- 12 pruebas HTTP con Flask: JSON inválido, límites/tipos, login y contraseña temporal,
  Bearer, permisos, CRUD, carga inicial atómica, ciclo completo, cancelación, reasignación,
  reportes, errores JSON y revocación de sesiones.
- Colección Postman ejecutada con Newman 6.2.3 frente a un servidor HTTP local real y
  **SQLite**: 75 peticiones, 157 comprobaciones, cero fallos.
- Misma colección frente a **MySQL 8.0.46** real, driver oficial y cuenta con permisos
  limitados: 75 peticiones, 157 comprobaciones, cero fallos. Binlog activado y
  log_bin_trust_function_creators=0. Se comprobó que la cuenta no puede borrar historial,
  auditoría ni recibos de operaciones.
- Dependencias instaladas: Python 3.12, Flask 3.1.3 y mysql-connector-python 26.7.0.
- Se revisan formato Python, diferencias sin errores de espacio y ausencia de bases,
  entornos virtuales, credenciales reales y binarios dentro del paquete de entrega.

Los resultados de Newman se reproducen sobre bases temporales nuevas con dueño creado
para prueba. No se han probado físicamente los computadores de la universidad ni la GUI de
la extensión de VS Code: la compatibilidad se basa en su importación oficial de colecciones
y entornos, y en ejecutar los archivos reales con el runtime de Postman/Newman.
Newman/Node.js se usaron para verificar aquí; **no son requisito para presentar con Send**.

## Cómo verificarlo tú

Desde backend_api, instala requirements y ejecuta:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Esto no toca tu base. Para validar MySQL de la presentación, ejecuta `--motor mysql --verificar`
y después las carpetas de Postman sobre los datos que quieras conservar. Esa colección sí
crea y archiva recursos y registra pedidos. No se debe ejecutar sin revisar en una base con
operación real del restaurante.

## Límites concretos

- Servicio de desarrollo local, sin HTTPS ni despliegue público incluido.
- Transacciones de escritura serializadas, pensadas para la escala de clase; no hay prueba
  de carga de producción ni promesa de escalabilidad ilimitada.
- Los permisos se aplican en la API/servicio; alguien con root MySQL o acceso al archivo
  SQLite puede modificar su propia base por fuera del programa.
- Autenticación sin correo de recuperación: el dueño restablece claves; no se inventa
  un mecanismo para recuperar la contraseña perdida del único dueño.
- No se implementan pagos, inventario, facturación fiscal o domicilios.
- La colección asume el precio inicial de hamburguesa COP 22.000 para su comprobación de
  COP 66.000. Si modificas el catálogo, ajusta ese valor esperado.
- Los bloques asignados son historias/funcionalidades; no se presentan falsamente como
  quince entidades con CRUD completo. Cada integrante registra y explica sus aportes reales.
