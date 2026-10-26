# CRUD REST Nicolás (Flask + MySQL)

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Configure .env
python app.py
```

Base URL: `http://127.0.0.1:5001`. Importar `postman/Nicolas_Polirestaurante.postman_collection.json` en Postman. Variables `base_url`, `admin_id=1`, `cocina_id=4`, `pedido_id`, `historial_id`, `reporte_id`.

**Advertencia:** `X-Usuario-Id` es solo identificación para la práctica, no autenticación. No exponer esta API en Internet. HU-16 JWT real debe integrarse antes de producción. En cocina se permiten cambios de estado válidos, y en administración CRUD de historial y reportes. Para un pedido nuevo de demostración use `POST /api/pedidos/demo` como administrador; no reemplaza HU-01 de Juan.

El historial original de la BD prohíbe cambios. `extension_nicolas.sql` elimina esos triggers para permitir el CRUD solicitado, y guarda auditoría antes/después de cada cambio hecho desde esta API. Las modificaciones directas por Workbench no pasan por esa auditoría. La corrección manual de historial no cambia automáticamente el estado actual de pedido: usar `/api/pedidos/{id}/estado` con `correccion=true` (administrador). Borrar entradas de historial puede modificar los cálculos; la auditoría permite revisar quién lo hizo.
