# PoliRestaurante · Cliente MVC de Juan Parra

Este documento explica el módulo original de pedidos. Para ejecutar la entrega de los tres roles y gestionar cuentas desde el navegador, empieza por [GUIA_PRESENTACION_COMPLETA.md](GUIA_PRESENTACION_COMPLETA.md).

**Para la versión con usuarios y catálogo ya preparados**, empieza por
[LEEME_DEMO.txt](LEEME_DEMO.txt) y [CREDENCIALES_DEMO.txt](CREDENCIALES_DEMO.txt).
La carga compatible con tu MySQL se ejecuta con `python cargar_demo.py --motor mysql`
desde backend_api. Las instrucciones de creación manual que siguen son una alternativa.

Cliente local **HTML + Bootstrap + JavaScript**, conectado a la API Flask mediante fetch.
Implementa las HU01–HU05 de Juan: crear/consultar pedidos, agregar productos, editar/quitar
líneas, entregar y cancelar. Conserva el backend REST anterior y su base versión 1, añadiendo
CORS y acceso a datos por DAO en HU02. No requiere Node.js para ejecutarlo.

La organización sigue el ejemplo `cliente-personas.zip` y las diapositivas 10 y 14–17 del
material del profesor: cliente MVC, API y base de datos por separado. Bootstrap 5.3.8 está
incluido localmente, con su licencia, para que la interfaz funcione sin CDN.

## Antes de empezar

Descomprime el paquete completo. Mantén juntas estas carpetas:

- `backend_api/`: API REST, driver SQL, DAO, SQL, pruebas y colección de Postman.
- `cliente_juan/`: cliente.html, estilos, Bootstrap y módulos JavaScript MVC.
- `docs_juan/`: ejecución, explicación DAO y guía de sustentación.

Abre la carpeta completa en VS Code. Instala Python 3.10+ (recomendado 3.11/3.12) y las
extensiones Live Server (Ritwick Dey), Python y, opcionalmente, Prettier/HTML CSS Support.

**Si ya usabas MySQL en la entrega anterior**, reutiliza `polirestaurante_driver`, sus
usuarios y tu `config_mysql.json`. No crees otro dueño ni importes esquemas ORM antiguos.

## Ejecución con tu MySQL actual

Desde la carpeta completa del paquete:

```powershell
cd backend_api
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-mysql.txt
```

Copia tu configuración real al archivo `backend_api/config_mysql.json` (una sola extensión).
No reemplaces tu contraseña con la del ejemplo. Después:

```powershell
.venv\Scripts\python.exe iniciar_api.py --motor mysql --verificar
.venv\Scripts\python.exe iniciar_api.py --motor mysql
```

Deja esa terminal abierta. Si nunca creaste el administrador, hazlo antes del último comando:

```powershell
.venv\Scripts\python.exe iniciar_api.py --motor mysql --crear-admin
```

El login del restaurante es independiente del usuario de conexión de config_mysql.json.
La interfaz hace login y maneja Bearer automáticamente: no tienes que copiar tokens.

## Alternativa SQLite para un computador sin MySQL

Desde `backend_api`:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe iniciar_api.py --crear-admin
.venv\Scripts\python.exe iniciar_api.py
```

`--crear-admin` se ejecuta una sola vez por base nueva. SQLite persiste en
`backend_api/datos/polirestaurante.db`; MySQL y SQLite son bases distintas. Usa siempre
el mismo motor durante la demostración. No se incluyen bases con contraseñas precreadas.

## Abrir el cliente

1. En el Explorador de VS Code abre `cliente_juan/cliente.html`.
2. Clic derecho > **Open with Live Server**.
3. Normalmente abre `http://127.0.0.1:5500/cliente_juan/cliente.html` (la ruta depende de la
   carpeta que abriste). Deja puerto 5500. No abras con doble clic/file://.
4. Entra con el administrador o mesero del restaurante. Con contraseña temporal aparece
   el formulario para cambiarla; después inicia sesión de nuevo.
5. Si faltan productos, el dueño puede pulsar **Cargar menú inicial**. Carga 4 categorías,
   10 productos y 6 mesas una sola vez, sin sobrescribir lo ya editado.

**También puedes abrir `http://127.0.0.1:5000/`** con Flask activo. El mismo cliente se sirve
por Flask y no necesita Live Server en esta alternativa. La configuración detecta esa ruta
para llamar a la API del mismo origen. Conserva ambas carpetas juntas.

## Crear empleados si todavía no existen

Con el dueño ya creado, puedes usar la utilidad opcional desde backend_api:

```powershell
.venv\Scripts\python.exe preparar_clase.py --motor mysql
```

Para SQLite omite `--motor mysql`. Pide las credenciales del dueño, carga el catálogo y
pregunta si deseas crear un MESERO (ejemplo de login: juan.parra) y COCINA. Tú eliges sus
contraseñas temporales. Responde N si ya existen: no cambia usuarios previos. También
puedes seguir creando empleados con la colección de Postman que ya conoces.

## Cómo probar tus funcionalidades

| HU | Operación en pantalla | Resultado |
|---|---|---|
| HU01 | Nuevo pedido, salón/mesa libre o para llevar | Pedido pendiente y mesa reservada si corresponde |
| Consulta | Listado, filtro, búsqueda en página y Abrir | Detalle, productos, total e historial |
| HU02 | Elegir categoría/producto, cantidad/notas y Agregar | Precio de BD, tres DAO en servidor y nuevo total |
| HU03 | Editar o Quitar en una línea pendiente | PUT o DELETE del detalle, con confirmación al quitar |
| HU04 | Marcar entregado cuando esté LISTO | Registra entrega y libera mesa |
| HU05 | Cancelar pedido con motivo | Conserva historial y libera mesa |

Para probar HU04, cocina debe marcar EN_PREPARACION y LISTO. Se incluyen botones de apoyo
para esos pasos al entrar con una cuenta COCINA o ADMINISTRADOR. Con mesero no aparecen.
Puedes cerrar sesión, entrar como cocina, preparar/marcar listo y volver a Juan para entregar.
El dueño puede efectuar el recorrido completo para una prueba técnica.

Cancelar un pedido es su baja lógica, no un borrado de ventas/historial. Quitar una línea
pendiente sí ejecuta DELETE. No se agrega un DELETE físico del pedido porque rompería las
reglas ya establecidas. Solo se editan líneas mientras PENDIENTE; cantidades 1–99.

## Los DAO y el MVC

**La funcionalidad HU02 usa `PedidoDAO`, `ProductoDAO` y `DetalleDAO` en una misma transacción**. El [inventario final](backend_api/docs/DAO_FINAL.md) documenta los 13 DAO del backend.
Los DAO son del backend; el MVC del navegador es una separación distinta. No se requieren
dos bases ni dos servidores. Detalles en:

- [DOS_DAOS_JUAN.txt](docs_juan/DOS_DAOS_JUAN.txt): qué significa y dónde buscarlo.
- [EXPLICACION_MVC_Y_DAO.md](docs_juan/EXPLICACION_MVC_Y_DAO.md): clases, flujo y guion.
- [PASO_A_PASO.txt](docs_juan/PASO_A_PASO.txt): comandos, primera carga y solución de errores.
- [VALIDACION.md](docs_juan/VALIDACION.md): comprobaciones y límites de la revisión.

## Reglas de conexión y recuperación

CORS permite por defecto los orígenes `http://127.0.0.1:5500` y `http://localhost:5500`.
Se admiten Authorization, Content-Type e Idempotency-Key. Para un puerto distinto, define
`POLI_CORS_ORIGINS` antes de arrancar Flask y ajusta la dirección de API del cliente solo si
cambias el puerto de Flask. No hace falta instalar flask-cors manualmente: está en requirements.

En el cliente se conserva el token en sessionStorage (por pestaña, no la contraseña).
Cerrar sesión limpia el token. Una operación de pedido con respuesta incierta conserva
su UUID y cuerpo: el aviso ofrece consultar/reintentar sin duplicarla. Si cierras sesión,
resuélvela después con la misma cuenta y dirección de API. No abras operaciones nuevas
hasta resolver esa respuesta pendiente. Un conflicto 409 recarga el estado para revisarlo.

## Pruebas y repositorio

Desde backend_api:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Opcional con Node 22+ desde la carpeta completa:
`node --test cliente_juan/tests/modelos.test.mjs`. Node no es necesario para usar el cliente.

Para incorporar, copia backend_api, cliente_juan, docs_juan y este README al repositorio.
Respalda tu código primero. Instala requirements nuevamente; conserva configuración y base.
No subas .venv, config_mysql.json, bases, tokens ni contraseñas. La entrega es local para
clase. No se publica un servidor ni se modifica el repositorio remoto automáticamente.
