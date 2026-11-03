# PoliRestaurante - Beta sencilla (INSERT y LISTAR)

Versión básica para clase, sin dashboard, imágenes, auditoría, UPDATE ni DELETE. Tiene cuatro pestañas: Pedidos, Cocina, Reportes e Historial.

## Ejecutar con CMD (Windows)

1. En VS Code abre la carpeta `backend` en CMD.
2. Si no tienes `.env`, ejecuta `copy .env.example .env` y escribe tus credenciales de MySQL. Si ya existe, no lo sobrescribas.
3. Ejecuta:
   ```cmd
   py -m venv .venv
   .venv\Scripts\activate.bat
   python -m pip install -r requirements.txt
   python app.py
   ```
4. Abre `http://127.0.0.1:5001/api/salud` para comprobar Flask.
5. En VS Code abre `frontend/index.html` con **Open with Live Server** (puerto 5500).

## Funcionalidades

- **Pedidos:** INSERT de pedido de demostración y LISTAR pedidos.
- **Cocina:** LISTAR cola pendiente (HU-06), preparación (HU-07) y listos (HU-08). Cambiar estados es UPDATE y por ahora no está habilitado.
- **Reportes:** INSERT y LISTAR configuraciones de ventas (HU-13) y tiempos (HU-14). No se calculan aún.
- **Historial:** INSERT y LISTAR registros de prueba (HU-15). Insertar un historial no actualiza automáticamente el estado del pedido.

El usuario administrador (ID 1) puede insertar en reportes e historial. Cocina (ID 4) se utiliza para los listados de cocina. Las credenciales disponibles dependen de tu base instalada.

## Base de datos

Se reutiliza `poli_restaurante`; si ya ejecutaste `extension_nicolas.sql` antes, no repitas la migración. **No ejecutes el esquema original sobre la base que ya utilizas**, porque puede borrar datos.

## El requisito de dos DAO sigue funcionando

- `backend/app.py` → `GET /api/cola` llama a `PedidoManager`.
- `backend/manager.py` → `PedidoManager.consultar_cola()` utiliza dos DAO.
- `backend/dao.py` → `PedidoDAO` consulta pedidos y `DetallePedidoDAO` consulta productos.
- `backend/db.py` → conexión y consultas MySQL.

Consulta `EXPLICACION_DAO_MANAGER.txt` para saber qué mostrar al profesor.

## Archivos de frontend MVC

- `frontend/js/model.js`: solicitudes fetch GET/POST.
- `frontend/js/view.js`: tablas y formularios.
- `frontend/js/controller.js`: conecta las acciones a los servicios.
- `frontend/js/app.js`: inicializa las clases.
