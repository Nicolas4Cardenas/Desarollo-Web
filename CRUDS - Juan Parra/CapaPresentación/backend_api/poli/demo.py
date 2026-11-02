"""Carga explícita local para clase. No se ejecuta al iniciar la API ni desde una ruta pública."""

import json
from .datos_iniciales import PRODUCTOS
from .errores import exigir
from .seguridad import hash_clave
from .servicio import Restaurante

ACCION_MARCA = "DEMO_JUAN_V1"
CUENTAS = (
    ("Administrador de clase", "admin.demo", "ADMINISTRADOR", "AdminClase2026!"),
    ("Juan Parra", "juan.demo", "MESERO", "MeseroClase2026!"),
    ("Laura Gómez", "mesero2.demo", "MESERO", "MeseroClase2026!"),
    ("Carlos Ruiz", "mesero3.demo", "MESERO", "MeseroClase2026!"),
    ("Cocina principal", "cocina1.demo", "COCINA", "CocinaClase2026!"),
    ("Cocina auxiliar", "cocina2.demo", "COCINA", "CocinaClase2026!"),
    ("Cocina de turno", "cocina3.demo", "COCINA", "CocinaClase2026!"),
)
PRODUCTOS_DEMO = PRODUCTOS + (
    ("Aros de cebolla", "Porción con salsa de la casa", 1000000, "Entradas"),
    ("Sopa del día", "Porción de sopa casera", 900000, "Entradas"),
    ("Arroz con pollo", "Arroz con pollo y ensalada", 2100000, "Platos fuertes"),
    ("Churrasco", "Carne a la parrilla con papas", 3200000, "Parrilla"),
    ("Costillas BBQ", "Costillas con salsa BBQ y papas", 3000000, "Parrilla"),
    ("Ensalada de la huerta", "Vegetales frescos y vinagreta", 1600000, "Vegetarianos"),
    ("Hamburguesa de lentejas", "Lentejas, vegetales y papas", 2000000, "Vegetarianos"),
    ("Gaseosa", "Bebida de 350 ml", 450000, "Bebidas"),
    ("Café", "Taza de café colombiano", 400000, "Bebidas"),
    ("Helado", "Dos bolas de helado", 650000, "Postres"),
)
MESAS_DEMO = tuple(
    (numero, (2, 4, 4, 6, 2, 8)[(numero - 1) % 6]) for numero in range(1, 13)
)


def texto_credenciales():
    lineas = [
        "POLIRESTAURANTE - CREDENCIALES DE DEMOSTRACIÓN",
        "============================================",
        "",
        "Usar después de ejecutar cargar_demo.py con el motor de tu base.",
        "Estas son cuentas del RESTAURANTE, no de MySQL ni de Postman.",
        "Elige Juan para probar HU01-HU05 y cocina1 para preparar sus pedidos.",
        "Son cuentas de clase con contraseñas conocidas; no usarlas como cuentas de producción.",
        "",
    ]
    for nombre, login, rol, password in CUENTAS:
        lineas += [
            f"Nombre: {nombre}",
            f"Usuario: {login}",
            f"Contraseña: {password}",
            f"Rol: {rol}",
            "",
        ]
    lineas += [
        "ACCESO",
        "------",
        "Flask: http://127.0.0.1:5000/",
        "Live Server: abrir cliente_juan/cliente.html con Open with Live Server.",
        "No necesitas Postman para entrar ni cambiar estas claves al primer ingreso.",
        "",
        "CARGA EN TU MYSQL ACTUAL (desde backend_api)",
        ".venv\\Scripts\\python.exe cargar_demo.py --motor mysql",
        ".venv\\Scripts\\python.exe iniciar_api.py --motor mysql",
        "",
        "SI SE BLOQUEÓ O CAMBIASTE UNA CUENTA DE ESTE ARCHIVO",
        ".venv\\Scripts\\python.exe cargar_demo.py --motor mysql --restablecer-claves-demo",
        "Ese parámetro solo restablece las cuentas creadas por esta carga.",
        "No cambia las contraseñas de tus cuentas anteriores.",
        "",
        "NOTAS",
        "- La base sigue siendo polirestaurante_driver. Conserva tu config_mysql.json.",
        "- Las mayúsculas, números y el signo ! de las contraseñas sí importan.",
        "- No hay espacios al principio ni al final de una contraseña.",
        "- Los ID dependen de la base existente; los logins anteriores son los que debes usar.",
        "- Carga: 1 administrador, 3 meseros, 3 cocineros; catálogo de 6 categorías, 20 productos y 12 mesas.",
        "- Si ya hay productos/mesas con los mismos nombres/números, se conservan.",
        "- Repetir la carga normal no duplica datos ni restablece contraseñas.",
    ]
    return "\n".join(lineas) + "\n"


def cargar_demo(base, restablecer_claves=False):
    """Una transacción, sin borrar negocio previo ni cambiar cuentas ajenas al demo."""
    base.verificar_esquema()
    servicio = Restaurante(base)
    hashes = {login: hash_clave(password) for _, login, _, password in CUENTAS}
    with base.transaccion(True) as c:
        c.execute(
            "SELECT descripcion FROM auditoria WHERE accion=? ORDER BY id LIMIT 1",
            (ACCION_MARCA,),
        )
        marca = c.one()
        if marca:
            registro = json.loads(marca["descripcion"])
            exigir(
                registro.get("version") == 1,
                "Marca demo incompatible; no se cambió la base.",
                "CONFLICTO",
            )
            cuentas = registro["cuentas"]
            esperadas = {(login, rol) for _, login, rol, _ in CUENTAS}
            exigir(
                {(x["login"], x["rol"]) for x in cuentas} == esperadas,
                "La marca demo no coincide con las cuentas esperadas.",
                "CONFLICTO",
            )
            for cuenta in cuentas:
                c.execute(
                    "SELECT id,login,rol,activo FROM usuario WHERE id=?",
                    (cuenta["id"],),
                )
                u = c.one()
                exigir(
                    u
                    and u["login"] == cuenta["login"]
                    and u["rol"] == cuenta["rol"]
                    and u["activo"],
                    "Una cuenta demo cambió de rol, login o fue desactivada. Revísala con tu administrador; no se modificó.",
                    "CONFLICTO",
                )
            admin_id = next(x["id"] for x in cuentas if x["login"] == "admin.demo")
            if restablecer_claves:
                for cuenta in cuentas:
                    c.execute(
                        "UPDATE usuario SET password_hash=?,debe_cambiar=0,fallos=0,bloqueado_hasta=NULL WHERE id=?",
                        (hashes[cuenta["login"]], cuenta["id"]),
                    )
                    c.execute("DELETE FROM sesion WHERE usuario_id=?", (cuenta["id"],))
                servicio._auditar(
                    c,
                    admin_id,
                    "RESET_DEMO_JUAN",
                    "usuario",
                    admin_id,
                    "Restablecidas únicamente las cuentas marcadas de la demostración local.",
                )
            return {
                "cargado": False,
                "claves_restablecidas": bool(restablecer_claves),
                "cuentas": cuentas,
                "creados": {"usuarios": 0, "categorias": 0, "productos": 0, "mesas": 0},
                "mensaje": (
                    "Cuentas demo restablecidas y desbloqueadas."
                    if restablecer_claves
                    else "La demostración ya se cargó. No se duplicaron ni cambiaron datos."
                ),
            }

        # Si hay un login reservado que no fue creado por esta carga, no se toca ni se eleva su rol.
        for _, login, _, _ in CUENTAS:
            c.execute("SELECT id FROM usuario WHERE login=?", (login,))
            exigir(
                c.one() is None,
                f"Ya existe {login} sin marca de esta demostración. No se modificó ninguna cuenta; revisa ese login con el administrador.",
                "CONFLICTO",
            )
        cuentas = []
        for nombre, login, rol, _ in CUENTAS:
            c.execute(
                "INSERT INTO usuario(nombre,login,password_hash,rol,activo,debe_cambiar,fallos) VALUES(?,?,?,?,1,0,0)",
                (nombre, login, hashes[login], rol),
            )
            cuentas.append({"id": c.lastrowid, "login": login, "rol": rol})
        admin_id = cuentas[0]["id"]
        nuevos = {"usuarios": len(cuentas), "categorias": 0, "productos": 0, "mesas": 0}
        categorias = {}
        for nombre in dict.fromkeys(p[3] for p in PRODUCTOS_DEMO):
            c.execute("SELECT id FROM categoria WHERE nombre=?", (nombre,))
            fila = c.one()
            if fila:
                categorias[nombre] = fila["id"]
            else:
                c.execute("INSERT INTO categoria(nombre) VALUES(?)", (nombre,))
                categorias[nombre] = c.lastrowid
                nuevos["categorias"] += 1
        for nombre, descripcion, precio, categoria in PRODUCTOS_DEMO:
            c.execute("SELECT id FROM producto WHERE nombre=? LIMIT 1", (nombre,))
            if c.one():
                continue
            c.execute(
                "INSERT INTO producto(nombre,descripcion,precio_centavos,categoria_id,disponible,activo) VALUES(?,?,?,?,1,1)",
                (nombre, descripcion, precio, categorias[categoria]),
            )
            nuevos["productos"] += 1
        for numero, capacidad in MESAS_DEMO:
            c.execute("SELECT id FROM mesa WHERE numero=?", (numero,))
            if c.one():
                continue
            c.execute(
                "INSERT INTO mesa(numero,capacidad,activa) VALUES(?,?,1)",
                (numero, capacidad),
            )
            nuevos["mesas"] += 1
        # La marca y los ID demuestran qué cuentas puede restablecer esta utilidad en el futuro.
        servicio._auditar(
            c,
            admin_id,
            ACCION_MARCA,
            "demo",
            admin_id,
            json.dumps({"version": 1, "cuentas": cuentas}, ensure_ascii=True),
        )
        return {
            "cargado": True,
            "claves_restablecidas": False,
            "cuentas": cuentas,
            "creados": nuevos,
            "mensaje": "Demostración cargada. Todas sus cuentas pueden entrar directamente desde la página.",
        }
