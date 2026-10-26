# CRUD_ORM_SQLAlchemy
Aplicación de consola para HU-06, HU-07, HU-08, HU-13, HU-14 y HU-15.

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edite .env con la contraseña de MySQL
python main.py
```

Las opciones 1-15 incluyen consulta, altas, modificaciones y bajas. Para reportes se gestionan definiciones guardadas; los cálculos se obtienen de pedidos reales. Usuario de cocina ID 4 y administrador ID 1 en base semilla; son identificadores locales de demostración, NO autenticación segura.
