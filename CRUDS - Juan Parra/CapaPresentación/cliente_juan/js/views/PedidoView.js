import { ESTADOS } from "../config.js";
const $ = (id) => document.getElementById(id);
const moneda = (n) =>
  new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 2,
  }).format(n / 100);
const fecha = (valor) =>
  new Intl.DateTimeFormat("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Bogota",
  }).format(new Date(valor));
function nodo(tag, texto = "", clase = "") {
  const n = document.createElement(tag);
  n.textContent = texto;
  if (clase) n.className = clase;
  return n;
}
function boton(texto, accion, id, clase = "btn btn-outline-primary btn-sm") {
  const b = nodo("button", texto, clase);
  b.type = "button";
  b.dataset.accion = accion;
  if (id !== undefined) b.dataset.id = id;
  return b;
}
function estado(valor) {
  return nodo("span", ESTADOS[valor] || valor, "state-badge state-" + valor);
}
/** VISTA: única capa que conoce el DOM. Los datos de la API se escriben con textContent. */
export class PedidoView {
  constructor() {
    this.productos = [];
    this.confirmacion = null;
    this.ocupada = false;
  }
  conectar(eventos) {
    const forms = [
      ["login-form", "login"],
      ["password-form", "password"],
      ["nuevo-form", "crear"],
      ["agregar-form", "agregar"],
      ["editar-form", "editar"],
      ["confirmar-form", "confirmar"],
      ["filtros-form", "filtrar"],
    ];
    for (const [id, event] of forms)
      $(id).addEventListener("submit", (e) => {
        e.preventDefault();
        eventos[event](Object.fromEntries(new FormData(e.currentTarget)));
      });
    document.addEventListener("click", (e) => {
      const cerrar = e.target.closest("[data-cerrar]");
      if (cerrar) {
        cerrar.closest("dialog").close();
        return;
      }
      const b = e.target.closest("[data-accion]");
      if (b && !b.disabled)
        eventos.accion(b.dataset.accion, Number(b.dataset.id));
    });
    $("tipo").addEventListener("change", () => this.tipoServicio());
    $("categoria").addEventListener("change", () => this.opcionesProductos());
    $("buscar").addEventListener("input", () =>
      eventos.buscar($("buscar").value),
    );
  }
  configurar(url) {
    $("api-url").value = url;
  }
  datosLogin() {
    return Object.fromEntries(new FormData($("login-form")));
  }
  limpiarLogin() {
    $("password").value = "";
  }
  pantalla(usuario = null) {
    $("login-panel").hidden = !!usuario;
    $("sesion-activa").hidden = !usuario;
    $("password-panel").hidden = !usuario?.debe_cambiar;
    $("pedidos-panel").hidden = !usuario || !!usuario.debe_cambiar;
    if (usuario) {
      $("usuario-nombre").textContent = usuario.nombre;
      $("usuario-rol").textContent = {
        ADMINISTRADOR: "Administrador",
        MESERO: "Mesero",
        COCINA: "Cocina",
      }[usuario.rol];
      $("titulo-pedidos").textContent =
        usuario.rol === "MESERO"
          ? "Mis pedidos"
          : usuario.rol === "COCINA"
            ? "Pedidos de cocina"
            : "Pedidos del restaurante";
      $("nuevo-pedido").hidden = usuario.rol === "COCINA";
      $("cargar-catalogo").hidden = usuario.rol !== "ADMINISTRADOR";
    }
  }
  mensaje(texto, tipo = "success") {
    const p = $("mensaje");
    p.textContent = texto;
    p.className = "alert alert-" + tipo;
    p.hidden = !texto;
    // Un dialog modal deja el resto de la página inerte: el error también se anuncia allí.
    document.querySelectorAll(".dialog-error").forEach((n) => n.remove());
    if (tipo === "danger" && document.querySelector("dialog[open]")) {
      const aviso = nodo("p", texto, "dialog-error alert alert-danger");
      aviso.setAttribute("role", "alert");
      document.querySelector("dialog[open] form").append(aviso);
    }
  }
  ocupado(valor) {
    this.ocupada = valor;
    $("actividad").hidden = !valor;
    document.querySelectorAll("button").forEach((b) => {
      b.disabled = valor || b.dataset.inhabilitado === "true";
    });
    document.querySelectorAll("dialog").forEach((d) => {
      d.oncancel = (e) => {
        if (valor) e.preventDefault();
      };
    });
  }
  inhabilitar(id, valor) {
    $(id).dataset.inhabilitado = String(valor);
    $(id).disabled = this.ocupada || valor;
  }
  listado(datos, seleccionado, busqueda = "") {
    const filas = datos.items.filter((p) =>
      `${p.id} ${p.mesa || ""} ${p.responsable}`
        .toLowerCase()
        .includes(busqueda.toLowerCase().trim()),
    );
    $("contador").textContent = filas.length;
    $("tabla-pedidos").replaceChildren();
    for (const p of filas) {
      const tr = nodo("tr");
      if (p.id === seleccionado) tr.className = "selected";
      const id = nodo("td");
      id.append(
        nodo("span", "#" + String(p.id).padStart(4, "0"), "order-id"),
        nodo("small", fecha(p.creado)),
      );
      const servicio = nodo(
        "td",
        p.tipo === "SALON" ? `Mesa ${p.mesa}` : "Para llevar",
      );
      servicio.append(nodo("small", p.responsable));
      const st = nodo("td");
      st.append(estado(p.estado));
      const total = nodo("td", moneda(p.total_centavos), "text-end money");
      const acciones = nodo("td");
      const abrir = boton("Abrir", "abrir", p.id);
      abrir.setAttribute("aria-label", `Abrir pedido ${p.id}`);
      acciones.append(abrir);
      tr.append(id, servicio, st, total, acciones);
      $("tabla-pedidos").append(tr);
    }
    if (!filas.length) {
      const tr = nodo("tr");
      const td = nodo(
        "td",
        busqueda
          ? "No hay coincidencias en esta página."
          : "No hay pedidos con este filtro.",
        "empty-cell",
      );
      td.colSpan = 5;
      tr.append(td);
      $("tabla-pedidos").append(tr);
    }
    $("pagina-info").textContent =
      `Página ${datos.pagina} · ${datos.items.length} pedidos en esta página`;
    this.inhabilitar("pagina-anterior", datos.pagina <= 1);
    this.inhabilitar("pagina-siguiente", !datos.hay_mas);
  }
  detalle(p, permisos, enfocar = false) {
    $("detalle-vacio").hidden = !!p;
    $("detalle-panel").hidden = !p;
    if (!p) return;
    $("detalle-titulo").textContent =
      "Pedido #" + String(p.id).padStart(4, "0");
    $("detalle-servicio").textContent =
      `${p.tipo === "SALON" ? "Mesa " + p.mesa : "Para llevar"} · ${p.responsable}`;
    $("detalle-estado").textContent = ESTADOS[p.estado];
    $("detalle-estado").className = "state-badge state-" + p.estado;
    $("detalle-total").textContent = moneda(p.total_centavos);
    $("detalle-regla").textContent = {
      PENDIENTE:
        "Puedes ajustar los productos antes de iniciar la preparación.",
      EN_PREPARACION:
        "La cocina está preparando esta orden. Sus productos ya no se pueden editar.",
      LISTO: "La preparación terminó. El mesero puede registrar la entrega.",
      ENTREGADO: "Pedido entregado. Se conserva su detalle e historial.",
      CANCELADO:
        "Pedido cancelado. La mesa quedó disponible y el historial se conserva.",
    }[p.estado];
    $("tabla-detalles").replaceChildren();
    for (const d of p.detalles) {
      const tr = nodo("tr");
      const producto = nodo("td");
      producto.append(
        nodo("span", d.producto_nombre, "line-name"),
        nodo("small", moneda(d.precio_centavos) + " por unidad", "line-price"),
      );
      if (d.notas) producto.append(nodo("small", d.notas, "line-notes"));
      const cantidad = nodo("td", String(d.cantidad), "text-center");
      const subtotal = nodo(
        "td",
        moneda(d.precio_centavos * d.cantidad),
        "text-end money",
      );
      const acciones = nodo("td");
      if (permisos.editar) {
        const div = nodo("div", "", "line-buttons");
        for (const [texto, accion, clase] of [
          ["Editar", "editar-linea", "btn-line"],
          ["Quitar", "quitar-linea", "btn-line remove"],
        ]) {
          const b = boton(texto, accion, d.id, clase);
          b.setAttribute("aria-label", `${texto} ${d.producto_nombre}`);
          div.append(b);
        }
        acciones.append(div);
      }
      tr.append(producto, cantidad, subtotal, acciones);
      $("tabla-detalles").append(tr);
    }
    if (!p.detalles.length) {
      const tr = nodo("tr");
      const td = nodo(
        "td",
        "Aún no hay productos. Agrega el primero para completar la orden.",
        "empty-cell",
      );
      td.colSpan = 4;
      tr.append(td);
      $("tabla-detalles").append(tr);
    }
    $("agregar-form").hidden = !permisos.editar;
    for (const [id, permiso] of [
      ["preparar", "preparar"],
      ["listo", "listo"],
      ["entregar", "entregar"],
      ["cancelar-pedido", "cancelar"],
    ])
      $(id).hidden = !permisos[permiso];
    $("historial").replaceChildren();
    for (const h of p.historial) {
      const li = nodo("li", ESTADOS[h.estado]);
      li.append(nodo("small", `${fecha(h.fecha)} · ${h.usuario}`));
      if (h.motivo) li.append(nodo("p", h.motivo));
      $("historial").append(li);
    }
    if (enfocar) $("detalle-titulo").focus({ preventScroll: true });
  }
  catalogo(productos, categorias) {
    this.productos = productos;
    const previo = $("categoria").value;
    $("categoria").replaceChildren(new Option("Todas las categorías", ""));
    for (const c of categorias)
      $("categoria").append(new Option(c.nombre, c.id));
    if (categorias.some((x) => String(x.id) === previo))
      $("categoria").value = previo;
    this.opcionesProductos();
  }
  opcionesProductos() {
    const valor = $("producto").value;
    const categoria = $("categoria").value;
    const productos = this.productos.filter(
      (p) => !categoria || String(p.categoria_id) === categoria,
    );
    $("producto").replaceChildren(
      new Option(
        productos.length
          ? "Selecciona un producto"
          : "No hay productos disponibles",
        "",
      ),
    );
    for (const p of productos)
      $("producto").append(
        new Option(`${p.nombre} · ${moneda(p.precio_centavos)}`, p.id),
      );
    if (productos.some((x) => String(x.id) === valor))
      $("producto").value = valor;
  }
  nuevo(mesas) {
    $("nuevo-form").reset();
    const libres = mesas.filter((m) => m.activa && m.estado === "LIBRE");
    $("mesa").replaceChildren(
      new Option(
        libres.length ? "Selecciona una mesa" : "Sin mesas disponibles",
        "",
      ),
    );
    for (const m of libres)
      $("mesa").append(
        new Option(`Mesa ${m.numero} · ${m.capacidad} personas`, m.id),
      );
    $("sin-mesas").hidden = libres.length > 0;
    if (!libres.length) $("tipo").value = "LLEVAR";
    this.tipoServicio();
    $("nuevo-dialog").showModal();
  }
  tipoServicio() {
    const salon = $("tipo").value === "SALON";
    $("mesa-campo").hidden = !salon;
    $("mesa").required = salon;
  }
  editar(d) {
    const f = $("editar-form");
    f.elements.detalle_id.value = d.id;
    f.elements.cantidad.value = d.cantidad;
    f.elements.notas.value = d.notas;
    $("editar-nombre").textContent = d.producto_nombre;
    $("editar-dialog").showModal();
  }
  confirmar(accion, id, titulo, texto, motivo = false) {
    this.confirmacion = { accion, id };
    $("confirmar-titulo").textContent = titulo;
    $("confirmar-texto").textContent = texto;
    $("motivo-campo").hidden = !motivo;
    $("motivo").required = motivo;
    $("motivo").value = "";
    $("confirmar-boton").textContent =
      accion === "quitar"
        ? "Quitar producto"
        : accion === "CANCELADO"
          ? "Cancelar pedido"
          : "Confirmar";
    $("confirmar-boton").className =
      "btn " + (motivo || accion === "quitar" ? "btn-danger" : "btn-primary");
    $("confirmar-dialog").showModal();
  }
  confirmacionActual() {
    return this.confirmacion;
  }
  cerrarDialogos() {
    document.querySelectorAll("dialog[open]").forEach((d) => d.close());
    document.querySelectorAll(".dialog-error").forEach((n) => n.remove());
  }
  limpiarAgregar() {
    $("cantidad").value = 1;
    $("notas").value = "";
  }
  limpiarClaves() {
    $("password-form").reset();
    this.limpiarLogin();
  }
  pendiente(op) {
    $("pendiente-banner").hidden = !op;
    if (op)
      $("pendiente-texto").textContent =
        `${op.nombre}. Se conserva la clave ${op.clave}. Consulta el resultado antes de iniciar otra operación.`;
  }
}
