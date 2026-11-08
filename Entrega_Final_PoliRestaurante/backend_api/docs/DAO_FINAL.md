# Capa de acceso a datos · Entrega final

El backend contiene **13 DAO usados por la aplicación**: uno por cada una de las 12 tablas y uno para consultas de reportes. Los archivos están en `backend_api/poli/dao/`. Las utilidades compartidas de `base.py` y `inspeccion.py` no cuentan como DAO.

| # | DAO y archivo | Qué hace y dónde se usa |
| --- | --- | --- |
| 1 | `UsuarioDAO` · `usuario_dao.py` | Alta, consulta, edición, desactivación, fallos y contraseñas. Login, administración de usuarios y carga demo. |
| 2 | `SesionDAO` · `sesion_dao.py` | Crea y busca sesiones por la huella del token; limpia las vencidas y revoca una sesión o todas las de una cuenta. Login, autorización, logout y cambio de clave. |
| 3 | `CategoriaDAO` · `categoria_dao.py` | Lista, consulta, inserta, edita y elimina categorías. Catálogo y carga inicial. |
| 4 | `ProductoDAO` · `producto_dao.py` | Catálogo, precio, categoría, alta, cambios, disponibilidad y archivo. Administración y HU02. |
| 5 | `MesaDAO` · `mesa_dao.py` | Consulta mesas con su ocupación, crea, edita y archiva. Catálogo y pedidos de salón. |
| 6 | `PedidoDAO` · `pedido_dao.py` | Alta, detalle general, listados, cola, estado, asignación y versionado. Operación diaria del restaurante. |
| 7 | `OcupacionDAO` · `ocupacion_dao.py` | Consulta, reserva y libera la mesa. Creación de salón, entrega y cancelación. |
| 8 | `DetalleDAO` · `detalle_dao.py` | Agrega, lista, edita y quita líneas. Cuenta y suma sus precios históricos. |
| 9 | `HistorialDAO` · `historial_dao.py` | Registra y lista cambios de estado por pedido. Detalle de pedidos. |
| 10 | `AuditoriaDAO` · `auditoria_dao.py` | Registra y pagina acciones. Consulta marcas de carga para no duplicar datos. |
| 11 | `OperacionDAO` · `operacion_dao.py` | Guarda y consulta recibos por usuario y UUID. Reintentos de pedidos y recibos en Mi perfil. |
| 12 | `SistemaDAO` · `sistema_dao.py` | Verifica la versión del esquema y adquiere el bloqueo de escritura en MySQL. Inicio, salud y transacciones. |
| 13 | `ReporteDAO` · `reporte_dao.py` | Consulta ventas entregadas y tiempos mediante uniones de pedidos, detalles e historial. Reportes de administración. |

Historial, auditoría y recibos conservan registros: sus DAO insertan y consultan. El DAO de sistema opera sobre la fila técnica instalada por el SQL. El archivado de productos y mesas, la desactivación de usuarios y la cancelación de pedidos son las operaciones de retiro del negocio.

**Flujo del código.** La vista llama a Flask (`poli/api.py`); el servicio (`poli/servicio.py`) aplica los permisos y reglas. Los DAO reciben el cursor de `Base.transaccion` y ejecutan SQL con parámetros. Si falla una operación, la transacción revierte todos sus cambios.

**Demostración de HU02.** En `Restaurante.agregar_producto`, pon puntos de interrupción en `PedidoDAO.obtener`, `ProductoDAO.obtener` y `DetalleDAO.crear`. Abre un pedido pendiente y pulsa **Agregar al pedido**. Se consultan el estado y la versión del pedido, se comprueba el producto y se guarda una copia del precio y la categoría en la línea. Los tres DAO usan el mismo cursor; el total, la auditoría y el recibo se confirman junto con la línea.

**Demostración de reportes.** En `Restaurante.ventas` o `Restaurante.tiempos`, sigue el cálculo en `poli/fechas.py` y la consulta en `ReporteDAO`. Se convierte la medianoche de Colombia a UTC para comparar las marcas persistidas. Por ejemplo, el 7 de noviembre de 2026 empieza a las `05:00Z` de ese día y termina justo antes de las `05:00Z` del día siguiente. Una venta del 7 a las 8 p. m. en Colombia pertenece al 7, aunque su marca UTC diga 8. Los tiempos del reporte se devuelven y se muestran en hora local.
