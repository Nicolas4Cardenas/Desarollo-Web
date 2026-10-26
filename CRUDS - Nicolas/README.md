# CRUDS - Nicolas | PoliRestaurante

Basado en la estructura de Juan Parra: **Driver MySQL**, **ORM SQLAlchemy**, **REST Flask + Postman**. HU-06 cola, HU-07 preparación, HU-08 listos, HU-13 ventas, HU-14 tiempos, HU-15 historial.

## Instalación obligatoria (MySQL Workbench)
1. Haga una copia de su base actual: `backend_original.sql` contiene `DROP DATABASE IF EXISTS poli_restaurante` y **BORRA DATOS**. Si ya tiene la base de Juan, **NO ejecute el original**.
2. Para instalación limpia, abra `database/backend_original.sql` y ejecútelo completo en Workbench.
3. Ejecute `database/extension_nicolas.sql` **una sola vez**, después del original. Crea reportes guardados, auditoría y permite edición de historial.
4. Abra cualquiera de las tres carpetas, copie `.env.example` a `.env`, configure su contraseña MySQL, instale `requirements.txt` y ejecute `python main.py` (Driver/ORM) o `python app.py` (REST).
5. En Postman importe `CRUD_REST_Nicolas/postman/Nicolas_Polirestaurante.postman_collection.json` y pruebe `GET /api/salud`.

## Flujo de demostración Postman
- POST `/api/pedidos/demo` como administrador, con una mesa libre y un producto disponible; guardar `id_pedido`.
- GET `/api/cola` como cocina → PUT `/api/pedidos/{id}/estado` a `EN_PREPARACION` → GET `/api/preparacion` → PUT estado `LISTO` → GET `/api/listos`.
- Como administrador, POST/GET/PUT/DELETE `/api/historial` y `/api/reportes`; GET `/api/reportes/{id}/calcular` muestra datos derivados.
- El pedido LISTO no cuenta como venta: para contabilizarlo, Juan debe entregarlo mediante HU-04 o administrador corregirlo bajo las reglas del módulo.

## Reglas y límites
- `X-Usuario-Id` es un mecanismo **didáctico**, no una sesión ni JWT. No publicar en red; requiere integrar HU-16 de Santiago.
- Cocina solo cambia `PENDIENTE -> EN_PREPARACION -> LISTO`. Admin puede corregir estados, editar/borrar historial y CRUD de reportes guardados.
- Crear y eliminar registros de cola se realiza sobre pedidos, no sobre una segunda cola duplicada. Eliminar pedidos solo se permite si están PENDIENTE o CANCELADO, para proteger ventas entregadas.
- El historial es editable por petición académica; la auditoría `nicolas_auditoria` conserva antes/después para cambios realizados por estas aplicaciones. Las ediciones pueden alterar reportes calculados.
- La extensión cambia la regla de historial inmutable del SQL original. **Coordinar con Juan y Santiago** antes de aplicar en base compartida.
- No se incluyen contraseñas reales. IDs de ejemplo corresponden a la semilla de `backend_original.sql` (admin=1, cocina=4).
- Las tres aplicaciones usan el mismo esquema, pero cada una abre su propia conexión a MySQL. ORM emplea modelos declarativos y SQLAlchemy Core para consultas y transacciones.
- Las pruebas de integración requieren MySQL local; aquí se valida sintaxis Python y formato de colección, no se afirma ejecución real de MySQL.
