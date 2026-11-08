"""Catálogo de presentación, explícito, atómico y ejecutable una sola vez por base."""

from .dao import AuditoriaDAO, CategoriaDAO, MesaDAO, ProductoDAO

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


def completar_catalogo(c, nombres_categorias, productos, mesas):
    """Comparte el mismo cursor que la carga y conserva los registros existentes."""
    categorias_dao, productos_dao, mesas_dao = CategoriaDAO(c), ProductoDAO(c), MesaDAO(c)
    categorias = {}
    nuevos = {"categorias": 0, "productos": 0, "mesas": 0}
    for nombre in nombres_categorias:
        fila = categorias_dao.buscar_nombre(nombre)
        if fila:
            categorias[nombre] = fila["id"]
        else:
            categorias[nombre] = categorias_dao.crear(nombre)
            nuevos["categorias"] += 1
    for nombre, descripcion, precio, categoria in productos:
        if productos_dao.buscar_nombre(nombre) is None:
            productos_dao.crear(nombre, descripcion, precio, categorias[categoria])
            nuevos["productos"] += 1
    for numero, capacidad in mesas:
        if mesas_dao.buscar_numero(numero) is None:
            mesas_dao.crear(numero, capacidad)
            nuevos["mesas"] += 1
    return nuevos


def cargar_catalogo(servicio, token):
    with servicio.base.transaccion(True) as c:
        u = servicio._actor(c, token, ("ADMINISTRADOR",))
        if AuditoriaDAO(c).buscar_primera_accion("CARGA_INICIAL"):
            return {
                "cargado": False,
                "mensaje": "El catálogo inicial ya se cargó. Tus cambios se conservan.",
            }
        nuevos = completar_catalogo(
            c, CATEGORIAS, PRODUCTOS, ((1, 2), (2, 4), (3, 4), (4, 6), (5, 2), (6, 8))
        )
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
