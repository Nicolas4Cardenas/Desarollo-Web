# PoliRestaurante · Fase 2: backend con driver y consola

Esta entrega contiene el **backend funcional de administración, mesero y cocina**, presentado
mediante un menú de terminal. No incluye frontend web. El documento del curso repite la etiqueta
«Fase 2» para backend y frontend; esta versión sigue la aclaración de alcance: entregar ahora
el backend. La numeración definitiva de la fase de frontend debe confirmarse con el docente.

**Para empezar: `python main.py`.** En la primera ejecución creas al administrador dueño;
después ese administrador registra los usuarios, mesas, categorías y productos del restaurante.
No hay cuentas conocidas ni pedidos prefabricados.

## Por qué esta versión se puede llevar a la universidad

| Modo | Tecnología | Qué necesitas | Dónde guarda |
|---|---|---|---|
| **Portable, predeterminado** | Driver `sqlite3`, SQL directo | Python 3.10+ con sqlite3, carpeta con escritura | `datos/polirestaurante.db` |
| **MySQL opcional** | Driver oficial `mysql-connector-python`, el mismo servicio | Servidor MySQL 8.0.16+, un paquete Python y configuración | Base `polirestaurante_driver`, consultable en Workbench |

El modo portable no necesita pip, Flask, ORM, Alembic, Postman, Workbench, servidor MySQL,
Node ni acceso a Internet. **Python sí debe estar disponible en el equipo.** No es un `.exe`
y no se promete ejecutar donde la universidad haya bloqueado Python.

SQLite es una base SQL persistente, no una lista de prueba en memoria. La aplicación envía
INSERT/SELECT/UPDATE/DELETE con parámetros mediante su driver, igual que con un driver MySQL.
El programa no utiliza modelos ORM ni procedimientos almacenados en ninguno de los modos.

## Windows: instalación y primera ejecución

1. Descomprime el ZIP en una carpeta donde puedas guardar archivos, por ejemplo Documentos.
   No ejecutes dentro de la vista del ZIP. Abre la carpeta `backend_driver`.
2. Abre una terminal en esa carpeta. Ejecuta:

```powershell
python verificar_entorno.py
python main.py
```

Si tu equipo utiliza el lanzador `py`, reemplaza `python` por `py -3`. También puedes abrir
`iniciar.bat` con doble clic. En Linux/macOS: `python3 main.py` o `sh iniciar.sh`.

3. La primera ejecución muestra la ruta del archivo real de la base y solicita:
   - Nombre del dueño/administrador.
   - Usuario: de 3 a 40 caracteres, letras sin tilde/números/punto/guion/guion bajo.
   - Contraseña propia: de 10 a 128 caracteres, escrita dos veces y oculta en terminal.
4. Después elige `1) Iniciar sesión` y entra con esos datos. El rol sale de la cuenta;
   nadie puede escoger «ser admin» sin autenticarse.

**No ejecutes `crear_base.sql`, `esquema_mysql.sql`, `backend.sql` ni comandos Flask de la
entrega anterior. Este paquete es independiente y no modifica esas bases.** En SQLite el
esquema vacío se crea automáticamente, sin ejemplos comerciales. En arranques posteriores
se comprueba la versión y no se reinician datos.

## Configurar el restaurante desde el administrador

| Opción | Qué hacer al empezar |
|---|---|
| `30` Usuarios | Crear al menos un MESERO y un usuario COCINA. También puedes crear otro ADMINISTRADOR |
| `31` Categorías | Registrar categorías propias, por ejemplo Comidas o Bebidas |
| `32` Productos | Registrar nombre, descripción, precio y categoría. Precio: `18500` o `18500.50`, sin separadores de miles |
| `33` Mesas | Registrar número y capacidad; activa para ponerla en servicio |
| `43` Tablas reales | Consultar lo que acabas de guardar, sin mostrar hashes ni tokens de sesión |

Los datos de ejemplo de esta explicación **no se insertan automáticamente**. Escribe los
que quieras presentar. El programa distingue el **ID interno** del **número de mesa**:
selecciona el ID que muestra la tabla, aunque el número de mesa sea otro.

Toda cuenta creada o restablecida por el administrador empieza con contraseña temporal.
En su primer ingreso el programa exige cambiarla antes de permitir operaciones:
introduce la temporal como «actual», define una nueva dos veces y vuelve a iniciar sesión.
El dueño inicial ya define su contraseña privada y no necesita ese paso adicional.

## Probar los tres roles en un mismo computador

Abre tres terminales dentro de la misma carpeta y ejecuta `python main.py` en cada una.
Todas utilizarán el mismo archivo SQLite, cuya ruta se imprime al iniciar. Entra como
administrador, mesero y cocina respectivamente.

1. Mesero, `10`: crea un pedido de salón para una mesa libre, o para llevar sin mesa.
2. Mesero, `11`: agrega un producto, cantidad y notas. Puede repetirlo como otra línea
   para conservar preparaciones diferentes, por ejemplo con/sin cebolla.
3. Mesero, `12` y `13`: edita o quita líneas mientras siga PENDIENTE.
4. Cocina, `3`: consulta la cola, ordenada del más antiguo al más reciente.
5. Cocina, `20`: inicia preparación. El pedido queda asignado al cocinero que lo tomó.
6. Cocina, `21`: marca LISTO. Solo su cocinero asignado o el administrador pueden terminarlo.
7. Mesero, `3` o `4`: vuelve a consultar el pedido actualizado.
8. Mesero, `14`: confirma ENTREGADO. Se libera la reserva de mesa.
9. Administrador, `40` y `41`: consulta ventas y tiempos. Los filtros de fecha se interpretan
   en **UTC**, indicado en pantalla. Las fechas del detalle se muestran en zona local del PC.

La consola consulta la base al elegir una opción; no hay actualización automática de pantallas
abiertas. Usa nuevamente la consulta para ver el cambio hecho desde otra terminal.

## Facultades y límites de cada rol

| Acción | Administrador | Mesero | Cocina |
|---|---|---|---|
| Crear/editar/archivar usuarios, mesas y productos; categorías | Sí | No | No |
| Crear, editar y consultar pedidos | Todos; puede asignarlos a otro responsable | Propios | Solo consulta |
| Agregar/editar/quitar productos mientras PENDIENTE | Todos | Propios | No |
| Iniciar preparación y marcar LISTO | Todos | No | Preparar pendientes y finalizar los asignados |
| Entregar un pedido LISTO | Todos | Propios | No |
| Cancelar PENDIENTE / EN_PREPARACION con motivo | Todos | Propios | No |
| Cancelar LISTO por excepción con motivo | Sí, registrado como autorización del dueño | No | No |
| Reasignar responsable/cocina de un pedido abierto | Sí, con motivo | No | No |
| Reportes, auditoría, tablas y respaldos | Sí | No | No |
| Cambiar su contraseña y cerrar sesión | Sí | Sí | Sí |

Ser dueño no permite falsear datos: ningún rol puede preparar vacío, saltar estados,
editar un entregado, borrar auditorías ni eliminar físicamente pedidos. Un entregado no se
cancela; devoluciones/pagos/facturación están fuera de esta versión.

## Guardado y portabilidad

Cada operación se confirma con commit; ante error se revierte con rollback. Cerrar y abrir
el programa mantiene usuarios, pedidos, precios y estados. No se necesita importar SQL después
de crear o modificar registros.

- `0` dentro del rol cierra sesión; `0` en la pantalla inicial sale.
- `/cancelar` en cualquier dato vuelve sin enviar el formulario pendiente.
- El administrador puede respaldar SQLite en `44`; los reportes permiten exportar CSV.
- Para llevar datos a otro PC, cierra todas las terminales del programa y copia la carpeta
  completa, incluyendo `datos/`. Si solo llevas el código, el equipo nuevo empezará vacío.
- Guarda otra copia de seguridad. Los archivos `.db` contienen datos y hashes; no los publiques.
- No uses un archivo SQLite compartido por unidad de red o sincronización activa. Para varios
  computadores operando sobre los mismos datos utiliza MySQL con un servidor autorizado.
- SQLite y MySQL **no se sincronizan ni convierten automáticamente**. Elige un motor para la
  presentación; cambiar de motor apunta a una base independiente.

## Si quieres trabajar con Workbench

Sigue [docs/MYSQL.md](docs/MYSQL.md). Solo ese modo usa el servidor MySQL y el driver opcional.
No requiere SUPER, triggers ni cambiar `log_bin_trust_function_creators`. Los permisos de la
cuenta de conexión protegen historial y auditoría contra UPDATE/DELETE directos.

## Pruebas y revisión

Desde `backend_driver`:

```powershell
python -m unittest discover -s tests -v
```

Son pruebas con bases temporales: no necesitan pytest ni alteran la base de la presentación.
Incluyen ciclo completo, permisos, restablecimiento de contraseña, precios históricos,
rollback, persistencia, copia de seguridad y solicitudes concurrentes. Una prueba recorre el
menú verdadero de los tres roles desde la configuración inicial hasta los reportes.

```powershell
python main.py --verificar
```

Comprueba una base ya creada, sin crear administrador. Para una base SQLite separada:
`python main.py --base "C:\ruta\otra_presentacion.db"`.

## Organización para estudiar y sustentar

| Archivo | Qué explica |
|---|---|
| `main.py` | Configuración y arranque; elige driver, inicializa y abre el menú |
| `poli/menu.py` | Menús, entradas, tablas, exportaciones y confirmaciones |
| `poli/servicio.py` | SQL directo y reglas reales de los tres módulos |
| `poli/db.py` | Conexión, transacciones, adaptación de parámetros y respaldo SQLite |
| `poli/seguridad.py` | Hash de contraseñas y huella de sesiones |
| `poli/validaciones.py` | Tipos, límites, roles, estados y dinero |
| `sql/` | Esquema vacío SQLite; instalación MySQL opcional y cuenta restringida |
| `tests/` | Casos reproducibles con unittest, sin datos de muestra persistentes |
| `docs/` | Manual de entrega, reparto, sustentación y validación |

Empieza por [docs/GUIA_SUSTENTACION_JUAN.md](docs/GUIA_SUSTENTACION_JUAN.md) y
[docs/REPARTO_Y_REGLAS.md](docs/REPARTO_Y_REGLAS.md).

## Problemas habituales

| Mensaje/situación | Qué hacer |
|---|---|
| `python no se reconoce` | Prueba `py -3`. Si tampoco existe, ese PC necesita Python autorizado/preparado por la universidad |
| Falta `sqlite3` | Ejecuta verificar_entorno.py. Se necesita una distribución de Python que incluya ese módulo |
| No permite guardar | Descomprime en una carpeta del usuario; no uses Archivos de programa ni la vista del ZIP |
| Contraseña no aparece al escribir | Es normal: getpass oculta caracteres; escribe y pulsa Enter |
| Cuenta temporal | Cambia contraseña, luego inicia sesión de nuevo |
| Usuario bloqueado | Espera 15 minutos; otro administrador puede restablecer la contraseña desde 30 |
| No puedo crear primer admin | Ya hay usuarios en esa base. Inicia sesión con la cuenta creada o selecciona otra ruta de base |
| No se ve una mesa/producto | Revisa activa/disponible; consulta de nuevo. Archivar no borra los datos |
| El pedido cambió | Otra sesión actuó antes: vuelve a consultar y revisa la versión/estado |
| Error de conexión incierto | Conserva la clave impresa; usa 90 para repetir los mismos datos o 91 para consultar el resultado |
| Error MySQL 1045 | Cuenta/clave de conexión en config_mysql.json; no es el usuario del menú. Lee MYSQL.md |
| Ya tenía el backend web anterior | Este paquete usa otra base y otra carpeta. No vuelve a ejecutar sus migraciones ni importa sus datos |

Si olvidaste la contraseña del único administrador, no hay una clave maestra incorporada.
Necesitarás recuperación técnica autorizada sobre una copia de seguridad o ayuda del responsable
de la base. Conviene registrar un segundo administrador individual para continuidad.
