import { ROLES, RECURSOS, TABLAS, seccionesDe, hoyColombia, ZONA_COLOMBIA } from "../models/GestionModel.js";
import { ESTADOS } from "../config.js";

const $ = id => document.getElementById(id);
const node = (tag, text = "", cls = "") => {
  const el = document.createElement(tag);
  el.textContent = text;
  el.className = cls;
  return el;
};
const action = (text, fn, cls = "btn btn-sm btn-outline-primary") => {
  const b = node("button", text, cls);
  b.type = "button";
  b.addEventListener("click", fn);
  return b;
};
const pesos = c => new Intl.NumberFormat("es-CO", {
  style: "currency", currency: "COP", maximumFractionDigits: 2,
}).format(Number(c) / 100);
const fecha = v => v ? new Intl.DateTimeFormat("es-CO", {
  dateStyle: "short", timeStyle: "short", timeZone: ZONA_COLOMBIA,
}).format(new Date(v)) : "—";
const distintivo = (t, activo = true) => node("span", t, "gestion-estado" + (activo ? "" : " inactivo"));
const opcion = (value, label) => new Option(label, value);
const opcionesUsuario = (rows, sinCambio) => [["", sinCambio], ...rows.map(u => [u.id, `${u.nombre} · ${u.login}`])];
const etiquetaCampo = (label, input, cls = "") => {
  const out = node("label", "", cls);
  out.append(node("span", label, "form-label small"), input);
  return out;
};
function control(campo) {
  const { nombre, etiqueta, tipo = "text", valor = "", opciones, requerido, max, min, bloqueado, ayuda } = campo;
  const input = node(opciones ? "select" : "input", "", opciones ? "form-select" : "form-control");
  input.name = nombre;
  input.id = "gestion-campo-" + nombre;
  input.required = !!requerido;
  input.disabled = !!bloqueado;
  if (opciones) {
    input.append(...opciones.map(([v, t]) => opcion(v, t)));
  } else {
    input.type = tipo;
    if (tipo === "number") {
      input.min = min ?? 1; input.max = max; input.step = "1";
    } else if (max) input.maxLength = max;
    if (tipo === "password") {
      input.autocomplete = nombre === "actual" ? "current-password" : "new-password";
      if (nombre !== "actual") input.minLength = 10;
    }
  }
  if (tipo === "checkbox") {
    input.className = "form-check-input";
    input.checked = Boolean(valor);
    const label = node("label", "", "form-check d-flex align-items-center gap-2");
    label.append(input, node("span", etiqueta, "small"));
    return label;
  }
  input.value = String(valor);
  const label = etiquetaCampo(etiqueta, input);
  if (ayuda) label.append(node("span", ayuda, "gestion-nota d-block mt-1"));
  return label;
}

function tabla(columnas, filas, vacio = "No hay registros para mostrar.") {
  const wrap = node("div", "", "table-responsive");
  const t = node("table", "", "table gestion-table");
  const thead = node("thead");
  const cabecera = node("tr");
  for (const [label] of columnas) {
    const th = node("th", label); th.scope = "col"; cabecera.append(th);
  }
  thead.append(cabecera);
  const body = node("tbody");
  for (const f of filas) {
    const tr = node("tr");
    for (const [, render] of columnas) {
      const td = node("td");
      const valor = render(f);
      if (valor instanceof Node) td.append(valor);
      else td.textContent = valor ?? "—";
      tr.append(td);
    }
    body.append(tr);
  }
  if (!filas.length) {
    const tr = node("tr");
    const td = node("td", vacio, "empty-cell");
    td.colSpan = columnas.length;
    tr.append(td); body.append(tr);
  }
  t.append(thead, body); wrap.append(t);
  return wrap;
}

function paginas(datos, cargar) {
  const bar = node("div", "", "gestion-pagina");
  const control = node("div", "", "d-flex gap-2");
  for (const [txt, pagina, disabled] of [
    ["Anterior", datos.pagina - 1, datos.pagina <= 1],
    ["Siguiente", datos.pagina + 1, !datos.hay_mas],
  ]) {
    const b = action(txt, () => cargar(pagina));
    b.disabled = disabled; b.dataset.inhabilitado = String(disabled);
    control.append(b);
  }
  bar.append(node("span", `Página ${datos.pagina} · ${datos.items.length} registros`, "small text-secondary"), control);
  return bar;
}

function listaDatos(pares) {
  const dl = node("dl", "", "gestion-detalle");
  for (const [k, v] of pares) dl.append(node("dt", k), node("dd", v == null ? "—" : String(v)));
  return dl;
}

function cifras(items) {
  const out = node("div", "", "gestion-tarjetas");
  for (const [nombre, dato] of items) {
    const card = node("div", "", "gestion-cifra");
    card.append(node("span", nombre, "gestion-nota"), node("strong", String(dato)));
    out.append(card);
  }
  return out;
}

function formulario(campos, etiqueta, fn, clase = "gestion-form") {
  const f = node("form", "", clase);
  f.append(...campos.map(control));
  const b = node("button", etiqueta, "btn btn-primary align-self-end");
  b.type = "submit"; f.append(b);
  f.addEventListener("submit", e => {
    e.preventDefault();
    fn(Object.fromEntries(new FormData(f)));
  });
  return f;
}

/** Vistas de administración; se renderiza texto de datos, nunca HTML de la API. */
export class GestionView {
  constructor() {
    this.menu = $("menu-gestion");
    this.panel = $("gestion-panel");
    this.dialog = $("gestion-dialog");
    this.dialog.addEventListener("close", () => {
      if (!this.dialog.open) this.dialog.replaceChildren();
    });
  }
  limpiar() {
    this.menu.hidden = true;
    this.menu.replaceChildren();
    this.panel.hidden = true;
    this.panel.replaceChildren();
    if (this.dialog.open) this.dialog.close();
    this.dialog.replaceChildren();
  }
  navegacion(usuario, actual, abrir) {
    this.menu.replaceChildren(...seccionesDe(usuario.rol).map(([id, label]) => {
      const b = action(label, () => abrir(id), "");
      if (id === actual) b.setAttribute("aria-current", "page");
      return b;
    }));
    this.menu.hidden = false;
    const pedidos = ["pedidos", "cola"].includes(actual);
    $("pedidos-panel").hidden = !pedidos;
    this.panel.hidden = pedidos;
    if (pedidos) this.panel.replaceChildren();
  }
  encabezado(titulo, descripcion, accion) {
    const cont = node("div", "", "page-heading");
    const copy = node("div");
    const h = node("h1", titulo);
    h.id = "gestion-titulo";
    copy.append(node("span", "POLIRESTAURANTE", "eyebrow"), h, node("p", descripcion, "text-secondary mb-0"));
    cont.append(copy);
    if (accion) cont.append(accion);
    this.panel.replaceChildren(cont);
  }
  dialogo(titulo, descripcion, campos, etiqueta, fn, peligro = false) {
    const f = formulario(campos, etiqueta, fn);
    const h = node("h2", titulo); h.id = "gestion-dialog-titulo";
    const head = node("div", "", "dialog-heading");
    const close = action("×", () => this.dialog.close(), "close-dialog");
    close.setAttribute("aria-label", "Cerrar");
    head.append(h, close);
    f.prepend(head, node("p", descripcion, "text-secondary mb-0"));
    const buttons = node("div", "", "dialog-actions");
    const submit = f.querySelector('[type="submit"]');
    submit.className = "btn btn-" + (peligro ? "danger" : "primary");
    buttons.append(action("Volver", () => this.dialog.close(), "btn btn-outline-secondary"), submit);
    f.append(buttons);
    this.dialog.replaceChildren(f);
    this.dialog.showModal();
  }
  verRegistro(recurso, fila) {
    const pares = {
      categorias: [["ID", fila.id], ["Nombre", fila.nombre]],
      productos: [["ID", fila.id], ["Nombre", fila.nombre], ["Categoría", fila.categoria], ["Descripción", fila.descripcion],
        ["Precio", pesos(fila.precio_centavos)], ["Activo", fila.activo ? "Sí" : "No"], ["Disponible", fila.disponible ? "Sí" : "No"]],
      mesas: [["ID", fila.id], ["Número", fila.numero], ["Capacidad", fila.capacidad], ["Estado", fila.activa ? fila.estado : "Archivada"], ["Pedido", fila.pedido_id]],
      usuarios: [["ID", fila.id], ["Nombre", fila.nombre], ["Usuario", fila.login], ["Rol", ROLES[fila.rol]],
        ["Activo", fila.activo ? "Sí" : "No"], ["Clave temporal", fila.debe_cambiar ? "Sí" : "No"],
        ["Bloqueado hasta", fecha(fila.bloqueado_hasta)]],
    };
    this.dialogo(RECURSOS[recurso].titulo + " · #" + fila.id, "Datos del registro.", [], "Cerrar", () => this.dialog.close());
    this.dialog.querySelector(".dialog-actions").before(listaDatos(pares[recurso]));
    this.dialog.querySelector(".dialog-actions button").remove();
  }
  editarRegistro(recurso, fila, categorias, actor, guardar, soloClave = false) {
    const f = fila || {};
    const propia = f.id === actor.id;
    const campo = (nombre, etiqueta, extra = {}) => ({ nombre, etiqueta, valor: f[nombre], requerido: true, ...extra });
    const check = (nombre, etiqueta, inicial = true) => campo(nombre, etiqueta, {
      tipo: "checkbox", valor: fila ? f[nombre] : inicial, requerido: false, bloqueado: propia && recurso === "usuarios",
    });
    const campos = {
      categorias: [campo("nombre", "Nombre de la categoría", { max: 50 })],
      productos: [
        campo("nombre", "Nombre del producto", { max: 100 }),
        campo("descripcion", "Descripción", { max: 255, requerido: false }),
        campo("categoria_id", "Categoría", { opciones: [["", "Selecciona"], ...categorias.map(c => [c.id, c.nombre])] }),
        campo("precio", "Precio en pesos colombianos", {
          max: 11, valor: fila ? (f.precio_centavos / 100).toFixed(2) : "", ayuda: "Ejemplo: 12500 o 12500.50.",
        }),
        check("activo", "Producto activo"), check("disponible", "Disponible para pedidos"),
      ],
      mesas: [
        campo("numero", "Número de mesa", { tipo: "number", max: 9999 }),
        campo("capacidad", "Capacidad", { tipo: "number", max: 100, valor: f.capacidad ?? 4 }),
        check("activa", "Mesa activa"),
      ],
      usuarios: [
        campo("nombre", "Nombre completo", { max: 100 }),
        campo("login", "Nombre de usuario", { max: 40, ayuda: "Letras, números, punto, guion o guion bajo." }),
        campo("rol", "Rol", { opciones: Object.entries(ROLES), valor: f.rol ?? "MESERO", bloqueado: propia }),
        check("activo", "Cuenta activa"),
        ...(!propia ? [campo("password", fila ? "Nueva clave temporal (opcional)" : "Contraseña temporal", {
          tipo: "password", max: 128, requerido: !fila, valor: "", ayuda: fila ? "Vacío conserva la clave actual." : "Mínimo 10 caracteres; se cambia en el primer acceso.",
        })] : []),
      ],
    };
    if (soloClave) {
      this.dialogo("Restablecer contraseña", `Cuenta: ${f.login}. Se quitará el bloqueo y se cerrarán sus sesiones.`,
        [campo("password", "Nueva contraseña temporal", { tipo: "password", max: 128, valor: "" })], "Restablecer",
        v => guardar({ ...f, activo: f.activo ? "on" : "", password: v.password }));
      return;
    }
    const { singular } = RECURSOS[recurso];
    this.dialogo(
      (fila ? "Editar " : "Crear ") + singular,
      recurso === "usuarios" && propia
        ? "Editar tu cuenta cierra la sesión. Cambia tu contraseña desde Mi perfil."
        : recurso === "usuarios" ? "Los permisos de la cuenta corresponden al rol elegido."
        : "Completa los campos para guardar los cambios.",
      campos[recurso], "Guardar", guardar,
    );
  }
  recurso(recurso, filas, categorias, usuario, acciones, filtros) {
    const admin = usuario.rol === "ADMINISTRADOR";
    const config = RECURSOS[recurso];
    const descripciones = {
      productos: "Carta, precios, disponibilidad y archivo.",
      categorias: "Organiza los productos de la carta.",
      mesas: "Capacidad y ocupación calculada a partir de los pedidos.",
      usuarios: "Cuentas, roles, bloqueos y contraseñas temporales.",
    };
    const top = node("div", "", "d-flex flex-wrap gap-2");
    top.append(action("Actualizar", acciones.recargar, "btn btn-outline-secondary"));
    if (admin) top.append(action("Crear " + config.singular, acciones.crear, "btn btn-primary"));
    this.encabezado(config.titulo, descripciones[recurso], top);
    const box = node("div", "", "panel");
    const toolbar = node("div", "", "gestion-toolbar");
    const input = node("input", "", "form-control");
    input.type = "search"; input.placeholder = "Nombre, número o ID"; input.value = filtros.busqueda || "";
    toolbar.append(etiquetaCampo("Buscar", input, "crece"));
    const status = node("select", "", "form-select");
    status.append(opcion("", "Todos"));
    const estados = {
      productos: [["disponible", "Disponibles"], ["nodisponible", "No disponibles"], ["archivo", "Archivados"]],
      mesas: [["LIBRE", "Libres"], ["OCUPADA", "Ocupadas"], ...(admin ? [["archivo", "Archivadas"]] : [])],
      usuarios: [["activo", "Activos"], ["inactivo", "Inactivos"], ["bloqueado", "Bloqueados"]],
    };
    if (estados[recurso] && (admin || recurso === "mesas")) {
      status.append(...estados[recurso].map(([v, t]) => opcion(v, t)));
      status.value = filtros.estado || "";
      toolbar.append(etiquetaCampo("Estado", status));
    }
    const grupo = node("select", "", "form-select");
    grupo.append(opcion("", "Todas"));
    if (recurso === "productos" || recurso === "usuarios") {
      const gs = recurso === "productos" ? categorias.map(c => [c.id, c.nombre]) : Object.entries(ROLES);
      grupo.append(...gs.map(([v, t]) => opcion(v, t)));
      grupo.value = filtros.grupo || "";
      toolbar.append(etiquetaCampo(recurso === "productos" ? "Categoría" : "Rol", grupo));
    }
    const cont = node("div");
    const columns = {
      categorias: [["Nombre", f => f.nombre]],
      productos: [["Producto", f => f.nombre], ["Categoría", f => f.categoria],
        ["Precio", f => pesos(f.precio_centavos)], ["Estado", f => distintivo(!f.activo ? "Archivado" : f.disponible ? "Disponible" : "No disponible", f.activo && f.disponible)]],
      mesas: [["Mesa", f => "Mesa " + f.numero], ["Capacidad", f => f.capacidad + " personas"],
        ["Estado", f => distintivo(!f.activa ? "Archivada" : f.estado === "OCUPADA" ? "Ocupada" : "Libre", f.activa && f.estado === "LIBRE")],
        ["Pedido", f => f.pedido_id ? "#" + f.pedido_id : "—"]],
      usuarios: [["Nombre", f => f.nombre], ["Usuario", f => f.login], ["Rol", f => ROLES[f.rol]],
        ["Estado", f => distintivo(!f.activo ? "Inactivo" : bloqueado(f) ? "Bloqueado" : f.debe_cambiar ? "Clave temporal" : "Activo", f.activo && !bloqueado(f))]],
    };
    const bloqueado = f => Date.parse(f.bloqueado_hasta) > Date.now();
    const retirarPermitido = f => {
      if (recurso === "usuarios") return f.activo && f.id !== usuario.id;
      if (recurso === "mesas") return f.activa && f.estado !== "OCUPADA";
      if (recurso === "productos") return f.activo;
      return true;
    };
    const botones = f => {
      const out = node("div", "", "acciones-registro");
      const b = (t, fn, cls) => {
        const el = action(t, () => fn(f.id), cls);
        el.setAttribute("aria-label", t + " " + (f.nombre ?? "mesa " + f.numero));
        return el;
      };
      out.append(b("Ver", acciones.ver));
      if (admin && !(recurso === "mesas" && f.estado === "OCUPADA")) {
        out.append(b("Editar", acciones.editar));
        if (recurso === "usuarios" && f.id !== usuario.id) out.append(b("Restablecer clave", acciones.clave));
        if (retirarPermitido(f)) out.append(b(config.retiro, acciones.retirar, "btn btn-sm btn-outline-danger"));
      }
      return out;
    };
    const actualizar = () => {
      const q = input.value.trim().toLocaleLowerCase("es");
      const e = status.value;
      const g = grupo.value;
      Object.assign(filtros, { busqueda: input.value, estado: e, grupo: g });
      const fs = filas.filter(f => {
        if (q && ![f.id, f.nombre, f.descripcion, f.login, f.numero, f.categoria].join(" ").toLocaleLowerCase("es").includes(q)) return false;
        if (g && String(recurso === "productos" ? f.categoria_id : f.rol) !== g) return false;
        if (!e) return true;
        if (recurso === "productos") return e === "archivo" ? !f.activo : f.activo && Boolean(f.disponible) === (e === "disponible");
        if (recurso === "mesas") return e === "archivo" ? !f.activa : f.activa && f.estado === e;
        if (recurso === "usuarios") return e === "bloqueado" ? f.activo && bloqueado(f) : Boolean(f.activo) === (e === "activo");
        return true;
      });
      cont.replaceChildren(tabla([["ID", f => f.id], ...columns[recurso], ["Acciones", botones]], fs),
        node("p", `${fs.length} de ${filas.length} registros`, "gestion-pagina small text-secondary mb-0"));
    };
    for (const [el, evento] of [[input, "input"], [status, "change"], [grupo, "change"]]) el.addEventListener(evento, actualizar);
    box.append(toolbar, cont);
    this.panel.append(box);
    actualizar();
  }
  reasignar(pedido, elegibles, guardar) {
    const campos = [{ nombre: "responsable_id", etiqueta: "Mesero o administrador",
      opciones: opcionesUsuario(elegibles.responsables.filter(u => u.id !== pedido.responsable_id), "Mantener responsable") }];
    if (pedido.estado === "EN_PREPARACION") campos.push({ nombre: "cocinero_id", etiqueta: "Cocinero",
      opciones: opcionesUsuario(elegibles.cocineros.filter(u => u.id !== pedido.cocinero_id), "Mantener cocinero") });
    campos.push({ nombre: "motivo", etiqueta: "Motivo", max: 255, requerido: true });
    this.dialogo("Reasignar pedido #" + pedido.id, "Elige qué asignación cambiar. El motivo queda en auditoría.", campos, "Guardar asignación", guardar);
  }
  reportes(categorias, productos, consultar, filtros) {
    this.encabezado("Reportes", "Ventas entregadas y tiempos de preparación. Rango inclusivo en hora de Colombia.");
    const box = node("div", "", "panel");
    const hoy = hoyColombia();
    const f = formulario([
      { nombre: "tipo", etiqueta: "Reporte", opciones: [["ventas", "Ventas"], ["tiempos", "Tiempos"]], valor: filtros.tipo || "ventas" },
      { nombre: "desde", etiqueta: "Desde (Colombia)", tipo: "date", requerido: true, valor: filtros.desde || hoy.slice(0, 7) + "-01" },
      { nombre: "hasta", etiqueta: "Hasta (Colombia)", tipo: "date", requerido: true, valor: filtros.hasta || hoy },
      { nombre: "categoria_id", etiqueta: "Categoría", opciones: [["", "Todas"], ...categorias.map(c => [c.id, c.nombre])], valor: filtros.categoria_id },
      { nombre: "producto_id", etiqueta: "Producto", opciones: [["", "Todos"], ...productos.map(p => [p.id, p.nombre + " · #" + p.id])], valor: filtros.producto_id },
    ], "Consultar", consultar, "gestion-toolbar");
    const actualizar = () => {
      for (const id of ["categoria_id", "producto_id"]) f.elements[id].closest("label").hidden = f.elements.tipo.value === "tiempos";
    };
    f.elements.tipo.addEventListener("change", actualizar);
    actualizar();
    const r = node("div", "", "gestion-contenido"); r.id = "reporte-resultado";
    r.append(node("p", "Selecciona un periodo para consultar.", "text-secondary mb-0"));
    box.append(f, r); this.panel.append(box);
  }
  resultadoReporte(tipo, r, filtros) {
    const out = $("reporte-resultado");
    const titulo = node("h2", (tipo === "ventas" ? "Ventas" : "Tiempos de preparación") + ` · ${filtros.desde} a ${filtros.hasta} (hora de Colombia)`);
    if (tipo === "ventas") {
      out.replaceChildren(titulo, cifras([["Total vendido", pesos(r.total_centavos)], ["Unidades", r.unidades], ["Pedidos entregados", r.pedidos]]),
        tabla([["Producto", f => f.producto], ["Categoría", f => f.categoria], ["Unidades", f => f.unidades],
          ["Subtotal", f => pesos(f.total_centavos)]], r.items, "No hay ventas entregadas en este periodo."));
    } else {
      out.replaceChildren(titulo, cifras([["Tiempo promedio", r.promedio_segundos == null ? "Sin datos" : r.promedio_segundos + " s"],
        ["Pedidos preparados", r.items.length]]),
        tabla([["Pedido", f => "#" + f.id], ["Inicio (Colombia)", f => fecha(f.inicio)], ["Listo (Colombia)", f => fecha(f.listo)],
          ["Segundos", f => f.segundos]], r.items, "No hay preparaciones terminadas en este periodo."));
    }
  }
  auditoria(datos, cargar) {
    this.encabezado("Auditoría", "Registro de acciones y responsables. Consulta de solo lectura.",
      action("Actualizar", () => cargar(datos.pagina), "btn btn-outline-secondary"));
    const box = node("div", "", "panel");
    box.append(tabla([["Fecha", f => fecha(f.fecha)], ["Usuario", f => f.usuario], ["Acción", f => f.accion],
      ["Registro", f => f.entidad + (f.entidad_id ? " #" + f.entidad_id : "")], ["Descripción", f => f.descripcion]], datos.items),
      paginas(datos, cargar));
    this.panel.append(box);
  }
  datos(nombre, datos, cargar) {
    this.encabezado("Datos e historial", "Consulta las tablas permitidas. Las contraseñas y sesiones no se muestran.");
    const box = node("div", "", "panel");
    const f = formulario([{ nombre: "tabla", etiqueta: "Tabla", valor: nombre, opciones: Object.entries(TABLAS) }],
      "Consultar", d => cargar(d.tabla, 1), "gestion-toolbar");
    const columnas = Object.keys(datos.items[0] || {}).map(k => [k.replaceAll("_", " "), f =>
      f[k] == null ? "—" : Object.hasOwn(ESTADOS, f[k]) ? ESTADOS[f[k]] : String(f[k])]);
    box.append(f, tabla(columnas.length ? columnas : [["Datos", () => ""]], datos.items),
      paginas(datos, p => cargar(nombre, p)));
    this.panel.append(box);
  }
  perfil(usuario, salud, ultimaClave, cambiar, recibo) {
    this.encabezado("Mi perfil", "Identidad de la sesión y acceso a tus recibos de operación.");
    const grid = node("div", "", "row g-3");
    const tarjeta = (titulo, contenido) => {
      const col = node("div", "", "col-12 col-md-6");
      const panel = node("div", "", "panel gestion-contenido h-100");
      panel.append(node("h2", titulo, "mb-3"), contenido);
      col.append(panel); return col;
    };
    grid.append(tarjeta("Cuenta", listaDatos([["Nombre", usuario.nombre], ["Usuario", usuario.login], ["Rol", ROLES[usuario.rol]],
      ["Conexión", salud ? "Activa · " + salud.motor : "No verificada"], ["Versión del esquema", salud?.version]])),
      tarjeta("Cambiar mi contraseña", formulario([
        { nombre: "actual", etiqueta: "Contraseña actual", tipo: "password", requerido: true, max: 128 },
        { nombre: "nueva", etiqueta: "Nueva contraseña", tipo: "password", requerido: true, max: 128 },
        { nombre: "repite", etiqueta: "Confirma la nueva contraseña", tipo: "password", requerido: true, max: 128 },
      ], "Cambiar contraseña", cambiar)));
    this.panel.append(grid);
    const box = node("div", "", "panel gestion-contenido mt-3");
    box.append(node("h2", "Consultar recibo"), node("p", "Puedes consultar operaciones confirmadas por esta cuenta usando su UUID.", "gestion-nota mt-2"),
      formulario([{ nombre: "clave", etiqueta: "Clave de operación", valor: ultimaClave, max: 36, requerido: true }], "Buscar recibo", recibo));
    const result = node("div"); result.id = "gestion-recibo"; box.append(result); this.panel.append(box);
  }
  recibo(resultado) {
    const out = $("gestion-recibo");
    out.replaceChildren(node("p", "Confirmado: " + fecha(resultado.fecha), "mt-3 fw-semibold"),
      node("pre", JSON.stringify(resultado.resultado, null, 2), "gestion-recibo"));
  }
}
