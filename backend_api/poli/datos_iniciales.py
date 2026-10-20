"""Catálogo de presentación, explícito, atómico y ejecutable una sola vez por base."""

CATEGORIAS = ("Entradas", "Platos fuertes", "Bebidas", "Postres")
PRODUCTOS = (
    ("Papas criollas", "Porción de papas con salsa de la casa", 800000, "Entradas"),
    ("Patacones", "Patacones con hogao", 900000, "Entradas"),
    (
        "Hamburguesa de la casa",
        "Carne, queso, vegetales y papas",
        2200000,
        "Platos fuertes",
    ),
    ("Pollo a la plancha", "Pechuga con arroz y ensalada", 2400000, "Platos fuertes"),
    ("Pasta napolitana", "Pasta con salsa de tomate", 1900000, "Platos fuertes"),
    ("Limonada natural", "Vaso de limonada", 600000, "Bebidas"),
    ("Agua", "Botella de agua", 350000, "Bebidas"),
    ("Jugo de mora", "Jugo preparado en agua", 700000, "Bebidas"),
    ("Brownie", "Brownie de chocolate", 850000, "Postres"),
    ("Flan", "Flan de caramelo", 750000, "Postres"),
)


def cargar_catalogo(servicio, token):
    with servicio.base.transaccion(True) as c:
        u = servicio._actor(c, token, ("ADMINISTRADOR",))
        c.execute("SELECT id FROM auditoria WHERE accion='CARGA_INICIAL' LIMIT 1")
        if c.one():
            return {
                "cargado": False,
                "mensaje": "El catálogo inicial ya se cargó. Tus cambios se conservan.",
            }
        categorias, nuevos = {}, {"categorias": 0, "productos": 0, "mesas": 0}
        for nombre in CATEGORIAS:
            c.execute("SELECT id FROM categoria WHERE nombre=?", (nombre,))
            fila = c.one()
            if fila:
                categorias[nombre] = fila["id"]
            else:
                c.execute("INSERT INTO categoria(nombre) VALUES(?)", (nombre,))
                categorias[nombre] = c.lastrowid
                nuevos["categorias"] += 1
        for nombre, descripcion, precio, categoria in PRODUCTOS:
            c.execute("SELECT id FROM producto WHERE nombre=? LIMIT 1", (nombre,))
            if c.one():
                continue
            c.execute(
                "INSERT INTO producto(nombre,descripcion,precio_centavos,categoria_id,disponible,activo) VALUES(?,?,?,?,1,1)",
                (nombre, descripcion, precio, categorias[categoria]),
            )
            nuevos["productos"] += 1
        for numero, capacidad in ((1, 2), (2, 4), (3, 4), (4, 6), (5, 2), (6, 8)):
            c.execute("SELECT id FROM mesa WHERE numero=?", (numero,))
            if c.one():
                continue
            c.execute(
                "INSERT INTO mesa(numero,capacidad,activa) VALUES(?,?,1)",
                (numero, capacidad),
            )
            nuevos["mesas"] += 1
        servicio._auditar(
            c,
            u["id"],
            "CARGA_INICIAL",
            "catalogo",
            None,
            "Catálogo de presentación cargado explícitamente por administrador.",
        )
        return {
            "cargado": True,
            "creados": nuevos,
            "mensaje": "Catálogo listo. Los empleados se crean desde POST /usuarios; no se crean pedidos ficticios.",
        }
