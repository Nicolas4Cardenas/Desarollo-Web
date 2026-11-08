# Validación de la entrega de Juan · 2 de noviembre de 2026

## Resultado

- **55 pruebas Python de la entrega original** aprobadas: 38 de servicio, 12 HTTP y 5 nuevas de DAO/CORS/archivos.
- La prueba de HU02 observa las dos llamadas reales, comprueba el mismo cursor y verifica
  el detalle persistido. Un fallo del segundo DAO no deja escrituras parciales.
- **5 pruebas JavaScript** aprobadas: validaciones, permisos por estado y recuperación de UUID.
- **22 verificaciones de integración MVC/DOM** aprobadas con jsdom y Flask test_client sobre
  una base SQLite real temporal. Incluyen login, listado, editar/quitar, entrega, cancelación,
  filtro, apoyo de cocina, sesión y reintento después de un commit con respuesta perdida.
  No son pruebas de navegador: se ejercitan los módulos reales a través de un puente de pruebas.
- **27 peticiones API contra MySQL 8.0.46 real**, binlog activo, sin requisito SUPER y con la
  cuenta de aplicación limitada. Pasaron HU01–HU05, dos DAO, rollback, estados y UUID.
- Revisión visual de acceso y vista de pedidos en navegador, usando una instantánea del DOM
  producido por la prueba de integración. La vista de pedidos es una muestra estática para
  inspeccionar diseño; no se presenta como prueba integral de clics contra Flask en navegador.
- Bootstrap 5.3.8 y licencia incluidos localmente; el cliente no necesita CDN.

## Reproducir pruebas entregadas

Desde backend_api:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Desde la carpeta completa, opcional con Node 22+:

```text
node --test cliente_juan/tests/modelos.test.mjs
```

Usan datos temporales. La utilidad preparar_clase y las acciones de pantalla sí modifican
la base que selecciones, de forma explícita. No se incluyen cuentas ni pedidos de prueba
precargados en el paquete.

## Límites de la revisión

El entorno de vista previa no pudo ejecutar el servidor Python del proyecto. Por ello no
se afirma haber completado el flujo integral desde el navegador remoto. CORS y las rutas
se probaron por HTTP de Flask; el recorrido del cliente se probó con los módulos reales y
DOM de pruebas. No se han probado físicamente los computadores de la universidad.

La aplicación es para demostración local, con Flask de desarrollo y sin despliegue público.
Los cambios al catálogo no modifican los precios históricos. Cancelar es baja lógica;
quitar un detalle pendiente es borrado SQL. No hay borrado físico de pedidos ni modificación
de historial. El acceso de otros módulos del backend se mantiene por compatibilidad, pero
esta interfaz se centra en Juan y el apoyo mínimo de cocina.

## Carga de demostración añadida

`cargar_demo.py` añade un dueño nuevo, tres meseros, tres cocineros y un catálogo de
6 categorías, 20 productos y 12 mesas. Sus ocho pruebas nuevas comprueban los logins,
la conservación de datos previos, la repetición sin duplicados, recuperación solo de
cuentas demo, colisiones de nombres, rollback, el TXT de credenciales y el flujo de pedidos.

La carga también se ejecutó sobre MySQL 8.0.46 con el usuario de conexión limitado: los
siete usuarios iniciaron sesión sin cambio temporal de clave; los datos anteriores se
conservaron; repetir/restablecer y el ciclo de Juan con cocina terminaron correctamente.
Las credenciales son de clase y las contraseñas se guardan derivadas con PBKDF2 en la base.
No se modifica la autenticación normal ni se crea una ruta pública para cargar administradores.
