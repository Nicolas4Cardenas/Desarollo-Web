# Reparto, alcance y decisiones de negocio

## Alcance de la entrega

Se entrega API REST con Flask como adaptador HTTP y SQL directo mediante driver.
Postman (incluida la extensión de VS Code) prueba los endpoints; no se entrega frontend.
El servicio y el esquema proceden del backend driver anterior, con las mismas relaciones.
La API no depende de ejecutarlo ni importa su menú.

El administrador crea empleados y puede cargar explícitamente un catálogo inicial de
4 categorías, 10 productos y 6 mesas. No se crean pedidos ni cuentas con claves automáticas.
La carga es atómica y única por base. Se conservan datos previos de polirestaurante_driver.

## Cinco bloques por integrante

| Integrante | Bloques de responsabilidad |
|---|---|
| Juan Miguel Parra Garzón | 1. Crear/consultar pedido. 2. Agregar producto. 3. Editar/quitar detalle. 4. Entregar. 5. Cancelar |
| Nicolas Abril Cárdenas | 1. Cola FIFO. 2. Iniciar preparación. 3. Marcar listo. 4. Reporte de ventas. 5. Reporte de tiempos |
| Santiago Cortes Mojica | 1. CRUD usuarios. 2. CRUD categorías. 3. CRUD productos. 4. CRUD mesas. 5. Autenticación/roles |

Historial, auditoría, transacciones y persistencia son transversales. Esta entrega integra
los tres módulos para que puedan ejecutar la sustentación completa, no solo el de Juan.

**Precisar con el docente:** cinco historias/funcionalidades no equivalen a cinco entidades
CRUD completas por persona. Aquí se mantienen las HU previas y los cinco bloques acordados;
no se inventan tablas de negocio para declarar quince CRUD completos inexistentes. Cancelar
un pedido no lo borra; historial no ofrece edición/borrado.

Cada integrante debe revisar y registrar sus aportes reales con su cuenta Git. El reparto
no fabrica autoría, fechas ni commits a nombre de compañeros.

## Reglas de usuarios

- Solo una base sin usuarios permite crear el primer administrador con el comando local --crear-admin.
- Solo administrador crea cuentas. Los roles son fijos: ADMINISTRADOR, MESERO y COCINA.
- POST /auth/login valida contraseña, cuenta activa, bloqueo y expiración de sesión. No basta con
  pasar un id_usuario, ni hay una opción de simular otro rol.
- Usuarios nuevos/restablecidos deben cambiar contraseña temporal. Se revocan sesiones al
  editar usuario, cambiar contraseña o desactivar. La propia contraseña exige la actual.
- Cinco intentos fallidos bloquean esa cuenta durante 15 minutos. El restablecimiento por
  administrador quita el bloqueo. No se registran contraseñas en auditoría.
- El administrador no puede desactivarse ni quitarse su propio rol. Debe quedar un dueño
  activo. No se retira ni cambia de rol un usuario con pedidos abiertos como responsable
  o cocinero; antes se cierran o reasignan esos pedidos.

## Reglas de pedidos y mesas

| Origen | Destino | Quién |
|---|---|---|
| PENDIENTE | EN_PREPARACION | Cocina o administrador; al menos una línea |
| EN_PREPARACION | LISTO | Cocinero asignado o administrador |
| LISTO | ENTREGADO | Mesero responsable o administrador |
| PENDIENTE / EN_PREPARACION | CANCELADO | Mesero responsable o administrador; motivo obligatorio |
| LISTO | CANCELADO | Solo administrador por excepción, motivo obligatorio |

La excepción de cancelar LISTO por el dueño es una ampliación explícita para resolver el
retiro del cliente cuando la comida ya se preparó. Queda trazada. El mesero no obtiene esa
facultad. Ninguno puede cancelar ENTREGADO, volver atrás ni saltar estados. Si el docente
prefiere prohibir también al dueño cancelar LISTO, es una regla localizada en cambiar_estado.

- SALON reserva una mesa activa; LLEVAR no usa mesa. Una reserva por mesa, garantizada por
  PK de ocupacion. No se usa un campo editable «ocupada» que contradiga al pedido.
- Una mesa tiene número único y capacidad. No se edita/archiva mientras esté ocupada.
- El pedido puede nacer vacío para completarlo; cocina no lo toma vacío.
- Solo PENDIENTE permite agregar, editar o quitar líneas; cantidades enteras 1–99 y notas
  de hasta 255 caracteres. Máximo 100 líneas por pedido.
- Se aceptan líneas repetidas para notas diferentes. No se sobrescriben observaciones
  de una preparación al agregar el mismo producto de nuevo.
- Se copian nombre, categoría y precio al detalle. Cambiar/archivar el menú no altera ventas
  anteriores. Cada importe se guarda en centavos enteros para evitar redondeos binarios.
- Cada cambio de estado y su usuario se registra en la misma transacción. Cerrar pedido
  libera la reserva de la mesa y conserva la referencia histórica.
- Administración puede crear un pedido propio o asignarlo a otro mesero/admin activo,
  intervenir cualquier pedido y reasignar responsable/cocinero con motivo.
- Asignación de cocina cambia únicamente mientras EN_PREPARACION. Una reasignación se
  registra en auditoría; no inventa otra transición de estado.

## CRUD y borrados

Categorías vacías se eliminan físicamente; no se eliminan si tienen productos o referencias
históricas. Usuarios, productos y mesas se archivan/desactivan y pueden reactivarse con edición.
No hay DELETE de pedidos, historial ni auditoría desde el servicio. Quitar una línea de un
pedido pendiente sí usa DELETE SQL, dentro de transacción.

## Consistencia

SQLite abre BEGIN IMMEDIATE para escrituras; MySQL bloquea la fila técnica sistema con
SELECT FOR UPDATE. Ambas estrategias serializan las escrituras del programa: elección
conservadora para una demostración, no una afirmación de escalabilidad ilimitada.

Pedido.version detecta formularios que quedaron obsoletos entre consulta y confirmación.
Las operaciones HTTP de pedidos requieren Idempotency-Key (UUID), huella de la solicitud y
resultado persistido en la misma transacción. Repetir clave/datos con el mismo usuario
recupera el resultado original; cambiar datos con esa clave se rechaza. Tras respuesta
incierta conserva la clave y consulta GET /operaciones/{uuid}. El token puede renovarse
mediante login con la misma cuenta. El catálogo y los usuarios no usan recibos UUID.

En SQLite hay triggers locales que rechazan UPDATE/DELETE de historial/auditoría. En MySQL
se usan permisos de solo SELECT/INSERT en esas tablas y operacion, evitando el requisito
SUPER al crear triggers con binlog activado. Ninguno de estos controles pretende impedir
que un root o alguien con control total sobre el archivo físico modifique su propia base.

## Fuera de alcance

No se incorporan inventario, pagos, impuestos, facturación, domicilios, devoluciones ni
mensajería por correo, porque necesitan requisitos propios. La API HTTP sí forma parte de esta entrega. No hay menú ni frontend web.
Flask sirve HTTP local; las tablas siguen usando driver, no ORM.
