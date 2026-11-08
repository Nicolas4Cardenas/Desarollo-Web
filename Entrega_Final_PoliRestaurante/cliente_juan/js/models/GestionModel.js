/** Modelos de gestión: contrato REST y validación de formularios. */
export const ROLES = {
  ADMINISTRADOR: "Administrador",
  MESERO: "Mesero",
  COCINA: "Cocina",
};

export const RECURSOS = {
  productos: { titulo: "Productos", singular: "producto", retiro: "Archivar" },
  categorias: { titulo: "Categorías", singular: "categoría", retiro: "Eliminar" },
  mesas: { titulo: "Mesas", singular: "mesa", retiro: "Archivar" },
  usuarios: { titulo: "Usuarios", singular: "usuario", retiro: "Desactivar" },
};

export const TABLAS = {
  pedido: "Pedidos", detalle: "Detalles", historial: "Historial de estados",
  mesa: "Mesas", ocupacion: "Ocupación", producto: "Productos",
  categoria: "Categorías", usuario: "Usuarios", auditoria: "Auditoría", sistema: "Sistema",
};

const TODOS = Object.keys(ROLES);
const ADMIN = ["ADMINISTRADOR"];
const COCINA = ["ADMINISTRADOR", "COCINA"];
export const SECCIONES = [
  ["pedidos", "Pedidos", TODOS],
  ["cola", "Cola de cocina", COCINA],
  ["productos", "Productos", TODOS],
  ["categorias", "Categorías", TODOS],
  ["mesas", "Mesas", TODOS],
  ["usuarios", "Usuarios", ADMIN],
  ["reportes", "Reportes", ADMIN],
  ["auditoria", "Auditoría", ADMIN],
  ["datos", "Datos e historial", ADMIN],
  ["perfil", "Mi perfil", TODOS],
];

export function seccionesDe(rol) {
  return SECCIONES.filter(([, , roles]) => roles.includes(rol));
}

function entero(valor, maximo, nombre) {
  const n = Number(valor);
  if (!Number.isInteger(n) || n < 1 || n > maximo)
    throw new Error(`${nombre}: debe ser un entero entre 1 y ${maximo}.`);
  return n;
}

function texto(valor, maximo, nombre, requerido = true) {
  const v = String(valor ?? "").trim();
  if ((requerido && !v) || v.length > maximo || /[\x00-\x1f\x7f]/.test(v))
    throw new Error(`${nombre}: escribe hasta ${maximo} caracteres en una línea${requerido ? ", sin dejarlo vacío" : ""}.`);
  return v;
}

export function cuerpoRecurso(recurso, valores, fila = null, actor = null) {
  switch (recurso) {
    case "categorias":
      return { nombre: texto(valores.nombre, 50, "Nombre") };
    case "mesas":
      return {
        numero: entero(valores.numero, 9999, "Número de mesa"),
        capacidad: entero(valores.capacidad, 100, "Capacidad"),
        activa: valores.activa === "on",
      };
    case "productos": {
      const precio = String(valores.precio ?? "").trim().replace(",", ".");
      if (!/^\d{1,8}(\.\d{1,2})?$/.test(precio) || Number(precio) <= 0)
        throw new Error("Escribe un precio en pesos mayor que cero, sin separador de miles y con hasta dos decimales.");
      return {
        nombre: texto(valores.nombre, 100, "Nombre"),
        descripcion: texto(valores.descripcion, 255, "Descripción", false),
        precio,
        categoria_id: entero(valores.categoria_id, 2147483647, "Categoría"),
        activo: valores.activo === "on",
        disponible: valores.disponible === "on",
      };
    }
    case "usuarios": {
      const propia = fila && fila.id === actor?.id;
      const login = String(valores.login ?? "").trim().toLowerCase();
      if (!/^[a-z0-9_.-]{3,40}$/.test(login))
        throw new Error("El usuario debe tener entre 3 y 40 caracteres: letras, números, puntos, guiones o guiones bajos.");
      const rol = propia ? fila.rol : valores.rol;
      if (!Object.hasOwn(ROLES, rol)) throw new Error("Selecciona un rol válido.");
      const d = {
        nombre: texto(valores.nombre, 100, "Nombre"),
        login, rol, activo: propia ? true : valores.activo === "on",
      };
      if (!propia && (!fila || valores.password)) {
        const p = valores.password ?? "";
        if (p.length < 10 || p.length > 128 || p !== p.trim() || /[\x00-\x1f\x7f]/.test(p))
          throw new Error("La contraseña temporal debe tener entre 10 y 128 caracteres, sin espacios en los extremos ni caracteres de control.");
        d.password = p;
      }
      return d;
    }
    default: throw new Error("Recurso no disponible.");
  }
}

export const ZONA_COLOMBIA = "America/Bogota";
const diaColombia = new Intl.DateTimeFormat("en", {
  timeZone: ZONA_COLOMBIA, calendar: "iso8601", numberingSystem: "latn",
  year: "numeric", month: "2-digit", day: "2-digit",
});

export function hoyColombia(instante = new Date()) {
  const partes = Object.fromEntries(diaColombia.formatToParts(instante).map(p => [p.type, p.value]));
  return `${partes.year}-${partes.month}-${partes.day}`;
}

export function periodo(desde, hasta) {
  const milisegundos = Date.parse(hasta) - Date.parse(desde);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(desde) || !/^\d{4}-\d{2}-\d{2}$/.test(hasta)
      || !Number.isFinite(milisegundos) || milisegundos < 0 || milisegundos >= 366 * 86400000)
    throw new Error("Selecciona un rango inclusivo de hasta 366 días, con inicio anterior o igual al fin.");
  return { desde, hasta };
}

export class GestionModel {
  constructor(api) { this.api = api; }
  ruta(recurso, id) {
    if (!Object.hasOwn(RECURSOS, recurso)) throw new Error("Recurso no disponible.");
    return "/" + recurso + (id == null ? "" : "/" + entero(id, 2147483647, "ID"));
  }
  listar(recurso) {
    const extra = this.api.usuario?.rol === "ADMINISTRADOR"
      ? { productos: "?incluir_archivados=true", mesas: "?incluir_archivadas=true" }[recurso] || ""
      : "";
    return this.api.enviar(this.ruta(recurso) + extra);
  }
  obtener(recurso, id) { return this.api.enviar(this.ruta(recurso, id)); }
  guardar(recurso, id, body) {
    return this.api.enviar(this.ruta(recurso, id), { method: id == null ? "POST" : "PUT", body });
  }
  retirar(recurso, id) {
    return this.api.enviar(this.ruta(recurso, id), { method: "DELETE" });
  }
  async elegibles() {
    const activos = (await this.listar("usuarios")).filter(u => u.activo);
    return {
      responsables: activos.filter(u => ["MESERO", "ADMINISTRADOR"].includes(u.rol)),
      cocineros: activos.filter(u => ["COCINA", "ADMINISTRADOR"].includes(u.rol)),
    };
  }
  ventas(filtros) {
    const q = new URLSearchParams(periodo(filtros.desde, filtros.hasta));
    for (const id of ["categoria_id", "producto_id"]) if (filtros[id]) q.set(id, filtros[id]);
    return this.api.enviar("/reportes/ventas?" + q);
  }
  tiempos(filtros) {
    return this.api.enviar("/reportes/tiempos?" + new URLSearchParams(periodo(filtros.desde, filtros.hasta)));
  }
  auditoria(pagina) { return this.api.enviar("/admin/auditoria?pagina=" + pagina); }
  datos(tabla, pagina) {
    if (!Object.hasOwn(TABLAS, tabla)) throw new Error("Tabla no disponible.");
    return this.api.enviar(`/admin/tablas/${tabla}?pagina=${pagina}`);
  }
  recibo(clave) {
    clave = clave.trim().toLowerCase();
    if (!/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(clave))
      throw new Error("Escribe una clave de operación UUID válida.");
    return this.api.enviar("/operaciones/" + clave);
  }
  salud() { return this.api.enviar("/salud"); }
}
