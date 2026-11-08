# Verificación de la entrega final

- **Backend:** 64 pruebas aprobadas. Cubren autenticación y roles, catálogo y usuarios, pedidos y reservas, concurrencia, reintentos, protección del historial, reversión de cambios y el límite exacto de ambos lados de la medianoche de Colombia.
- **Cliente:** 9 pruebas de modelos JavaScript aprobadas. Se verificó que la fecha predeterminada del reporte cambie a medianoche de Colombia.
- **Navegador, base SQLite temporal:** el filtro predeterminado mostraba el día local. Se consultaron ventas y tiempos de una orden de prueba cuyo estado listo se guardó como `2025-11-08T01:00:00Z`. La orden apareció el 7 de noviembre a las 8:00 p. m. de Colombia.
- **MySQL 8.0.46, base temporal y cuenta de aplicación con permisos limitados:** carga demo sin duplicados, inicio con los tres roles, cambio de clave temporal, desactivación y reactivación de cuentas, alta y detalle de pedido, cocina, liberación de mesa, auditoría y consulta de ventas y tiempos con el límite local.
- **Zona horaria:** la conversión también funcionó con la base de zonas del sistema deshabilitada y con `tzdata` como fuente, tal como necesita una instalación de Windows sin datos IANA.
- **Compatibilidad:** los scripts SQL del esquema y las credenciales de clase son idénticos a los de la versión anterior. Conserva tu base de datos y el archivo `config_mysql.json`.

Para repetir las pruebas del backend, ejecuta desde `backend_api` con los requisitos instalados:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Pruebas opcionales del cliente con Node.js 22 o superior, desde la carpeta principal:

```powershell
node --test cliente_juan/tests/modelos.test.mjs
```

Node.js se usa solo para estas pruebas. La aplicación funciona con Python y el navegador.
