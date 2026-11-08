import { ApiError } from "./ApiModel.js";
/** Modelo del cliente: peticiones y reintentos. No es un DAO del servidor. */
export class PedidoModel {
  constructor(api) {
    this.api = api;
  }
  listar(estado = "", pagina = 1, abiertos = false) {
    const q = new URLSearchParams({ pagina });
    if (estado) q.set("estado", estado);
    if (abiertos) q.set("abiertos", "true");
    return this.api.enviar("/pedidos?" + q);
  }
  cola(pagina = 1) {
    return this.api.enviar("/cocina/cola?pagina=" + pagina);
  }
  obtener(id) {
    return this.api.enviar(`/pedidos/${id}`);
  }
  productos() {
    return this.api.enviar("/productos");
  }
  categorias() {
    return this.api.enviar("/categorias");
  }
  mesas() {
    return this.api.enviar("/mesas");
  }
  catalogo() {
    return this.api.enviar("/admin/datos-iniciales", {
      method: "POST",
      body: {},
    });
  }
  claveLocal(tipo, id = this.api.usuario?.id, url = this.api.url) {
    return id == null ? null : `poli_${tipo}:${id}:${url}`;
  }
  pendiente() {
    const clave = this.claveLocal("operacion");
    if (!clave) return null;
    const storage = this.api.storage;
    try {
      const actual = storage.getItem(clave);
      if (actual) return JSON.parse(actual);
      // Recupera una operación pendiente de la versión anterior, solo para su dueño.
      const anterior = storage.getItem("poli_operacion");
      const op = JSON.parse(anterior || "null");
      if (op?.usuario_id !== this.api.usuario.id || op.api_url !== this.api.url) return null;
      storage.setItem(clave, anterior);
      storage.removeItem("poli_operacion");
      return op;
    } catch {
      return null;
    }
  }
  ultimoRecibo() {
    const clave = this.claveLocal("recibo");
    return clave ? this.api.storage.getItem(clave) || "" : "";
  }
  registrarConfirmacion(op) {
    this.api.storage.setItem(this.claveLocal("recibo", op.usuario_id, op.api_url), op.clave);
    this.api.storage.removeItem(this.claveLocal("operacion", op.usuario_id, op.api_url));
  }
  async ejecutar(op) {
    try {
      const r = await this.api.enviar(op.ruta, {
        method: op.method,
        body: op.body,
        clave: op.clave,
      });
      this.registrarConfirmacion(op);
      return r;
    } catch (e) {
      if (e instanceof ApiError && e.estado >= 400 && e.estado < 500)
        this.api.storage.removeItem(this.claveLocal("operacion", op.usuario_id, op.api_url));
      throw e;
    }
  }
  async mutar(nombre, ruta, method, body) {
    if (this.pendiente())
      throw new Error("Resuelve primero la operación pendiente de confirmar.");
    const op = {
      nombre,
      ruta,
      method,
      body,
      clave: crypto.randomUUID(),
      usuario_id: this.api.usuario.id,
      api_url: this.api.url,
    };
    this.api.storage.setItem(this.claveLocal("operacion"), JSON.stringify(op));
    return this.ejecutar(op);
  }
  crear(d) {
    return this.mutar("Crear pedido", "/pedidos", "POST", d);
  }
  agregar(p, d) {
    return this.mutar("Agregar producto", `/pedidos/${p.id}/detalles`, "POST", {
      ...d,
      version: p.version,
    });
  }
  editar(p, id, d) {
    return this.mutar(
      "Editar producto",
      `/pedidos/${p.id}/detalles/${id}`,
      "PUT",
      { ...d, version: p.version },
    );
  }
  quitar(p, id) {
    return this.mutar(
      "Quitar producto",
      `/pedidos/${p.id}/detalles/${id}?version=${p.version}`,
      "DELETE",
    );
  }
  estado(p, estado, motivo = "") {
    return this.mutar("Actualizar estado", `/pedidos/${p.id}/estado`, "PATCH", {
      estado,
      version: p.version,
      motivo,
    });
  }
  reasignar(p, d) {
    return this.mutar("Reasignar pedido", `/pedidos/${p.id}/asignacion`, "PATCH", { ...d, version: p.version });
  }
  validarCuenta(op) {
    if (op.usuario_id !== this.api.usuario?.id || op.api_url !== this.api.url)
      throw new Error(
        "Esta operación pertenece a otra cuenta o dirección de API. Entra con la cuenta y conexión originales para resolverla.",
      );
  }
  async consultarPendiente() {
    const op = this.pendiente();
    if (!op) throw new Error("No hay una operación pendiente.");
    this.validarCuenta(op);
    const r = await this.api.enviar("/operaciones/" + op.clave);
    this.registrarConfirmacion(op);
    return r.resultado;
  }
  reintentarPendiente() {
    const op = this.pendiente();
    if (!op) throw new Error("No hay una operación pendiente.");
    this.validarCuenta(op);
    return this.ejecutar(op);
  }
}
