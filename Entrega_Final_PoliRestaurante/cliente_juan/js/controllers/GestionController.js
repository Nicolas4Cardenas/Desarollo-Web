import { cuerpoRecurso, RECURSOS, seccionesDe } from "../models/GestionModel.js";
import { Pedido } from "../models/Pedido.js";

/** Enlaza módulos con la sesión y con el controlador de pedidos original. */
export class GestionController {
  constructor(api, modelo, vista, pedidos) {
    Object.assign(this, { api, modelo, vista, pedidos });
    this.limpiarSesion();
  }
  limpiarSesion() {
    this.actual = null;
    this.filtros = {};
    this.periodo = {};
    this.vista.limpiar();
  }
  iniciarSesion() {
    this.limpiarSesion();
    return this.abrir(this.api.usuario.rol === "COCINA" ? "cola" : "pedidos");
  }
  tarea(fn) { return this.pedidos.tarea(fn, { pedido: false }); }
  navegacion(seccion) {
    this.actual = seccion;
    this.vista.navegacion(this.api.usuario, seccion, s => this.tarea(() => this.abrir(s)));
  }
  async abrir(seccion) {
    if (!this.api.usuario || this.api.usuario.debe_cambiar
        || !seccionesDe(this.api.usuario.rol).some(([id]) => id === seccion))
      throw new Error("Tu cuenta no tiene acceso a este módulo.");
    if (["pedidos", "cola"].includes(seccion)) {
      await this.pedidos.modo(seccion);
      this.navegacion(seccion);
      return;
    }
    if (Object.hasOwn(RECURSOS, seccion)) return this.cargarRecurso(seccion);
    if (seccion === "auditoria") return this.auditoria(1);
    if (seccion === "datos") return this.datos("historial", 1);
    if (seccion === "reportes") {
      const [c, p] = await Promise.all([this.modelo.listar("categorias"), this.modelo.listar("productos")]);
      this.navegacion(seccion);
      this.vista.reportes(c, p, f => this.tarea(() => this.consultarReporte(f)), this.periodo);
    }
    if (seccion === "perfil") {
      const usuario = await this.api.perfil();
      const salud = await this.modelo.salud().catch(() => null);
      this.navegacion(seccion);
      this.vista.perfil(usuario, salud, this.pedidos.modelo.ultimoRecibo(),
        d => this.tarea(() => this.pedidos.cambiarClave(d)),
        c => this.tarea(async () => this.vista.recibo(await this.modelo.recibo(c.clave))));
    }
  }
  async cargarRecurso(recurso) {
    const [filas, categorias] = await Promise.all([
      this.modelo.listar(recurso),
      recurso === "productos" ? this.modelo.listar("categorias") : [],
    ]);
    this.navegacion(recurso);
    this.vista.recurso(recurso, filas, categorias, this.api.usuario, {
      recargar: () => this.tarea(() => this.cargarRecurso(recurso)),
      crear: () => this.tarea(() => this.editar(recurso, null, categorias)),
      ver: id => this.tarea(async () => this.vista.verRegistro(recurso, await this.modelo.obtener(recurso, id))),
      editar: id => this.tarea(() => this.editar(recurso, id, categorias)),
      clave: id => this.tarea(() => this.editar(recurso, id, categorias, true)),
      retirar: id => this.tarea(() => this.retirar(recurso, id)),
    }, this.filtros[recurso] ??= {});
  }
  async editar(recurso, id, categorias, soloClave = false) {
    if (recurso === "productos" && !categorias.length)
      throw new Error("Crea una categoría antes de registrar productos.");
    const fila = id == null ? null : await this.modelo.obtener(recurso, id);
    this.vista.editarRegistro(recurso, fila, categorias, this.api.usuario,
      d => this.tarea(() => this.guardar(recurso, fila, d)), soloClave);
  }
  async guardar(recurso, fila, d) {
    const actor = this.api.usuario;
    const body = cuerpoRecurso(recurso, d, fila, actor);
    const r = await this.escritura(() => this.modelo.guardar(recurso, fila?.id, body));
    this.vista.dialog.close();
    if (recurso === "usuarios" && fila?.id === actor.id) {
      this.api.limpiar();
      this.limpiarSesion();
      this.pedidos.vista.pantalla();
      this.pedidos.vista.mensaje("Tu cuenta fue actualizada. Vuelve a iniciar sesión con el usuario " + body.login + ".");
      return;
    }
    await this.refrescarTrasEscritura(recurso, r.mensaje);
  }
  async retirar(recurso, id) {
    const fila = await this.modelo.obtener(recurso, id);
    const { retiro, singular } = RECURSOS[recurso];
    const descripcion = {
      categorias: "Se eliminará la categoría si no está referenciada por productos o pedidos.",
      productos: "El producto dejará de estar disponible. Los pedidos anteriores conservarán sus datos. Puedes reactivarlo al editar.",
      mesas: "La mesa quedará archivada y no se podrá reservar. Debe estar libre; puedes reactivarla al editar.",
      usuarios: "Se cerrarán sus sesiones. Sus pedidos e historial se conservan. Puedes reactivar la cuenta al editar.",
    }[recurso];
    this.vista.dialogo(retiro + " " + singular + " · " + (fila.nombre ?? fila.numero), descripcion, [], retiro,
      () => this.tarea(async () => {
        const r = await this.escritura(() => this.modelo.retirar(recurso, id));
        this.vista.dialog.close();
        await this.refrescarTrasEscritura(recurso, r.mensaje);
      }), true);
  }
  async escritura(fn) {
    try { return await fn(); }
    catch (e) {
      if (e.codigo === "CONEXION" || e.codigo === "RESPUESTA" || e.estado >= 500) {
        this.vista.dialog.close();
        e.message += " Actualiza el listado y verifica el resultado antes de volver a enviar.";
      }
      throw e;
    }
  }
  async refrescarTrasEscritura(recurso, mensaje) {
    try {
      await this.cargarRecurso(recurso);
    } catch (e) {
      e.message = "El cambio se guardó, pero no se pudo recargar el listado. " + e.message;
      throw e;
    }
    this.pedidos.vista.mensaje(mensaje);
  }
  async reasignar(pedido) {
    if (this.api.usuario.rol !== "ADMINISTRADOR") throw new Error("Solo administración puede reasignar.");
    this.vista.reasignar(pedido, await this.modelo.elegibles(), d => this.pedidos.tarea(async () => {
      const body = { motivo: Pedido.motivo(d.motivo) };
      for (const id of ["responsable_id", "cocinero_id"])
        if (d[id]) body[id] = Pedido.entero(d[id], "Usuario");
      if (!body.responsable_id && !body.cocinero_id) throw new Error("Selecciona una asignación para cambiar.");
      await this.pedidos.resultado(await this.pedidos.modelo.reasignar(pedido, body), "Asignación actualizada.");
    }));
  }
  async consultarReporte(f) {
    this.periodo = f;
    const r = f.tipo === "tiempos" ? await this.modelo.tiempos(f) : await this.modelo.ventas(f);
    this.vista.resultadoReporte(f.tipo, r, f);
  }
  async auditoria(pagina) {
    const d = await this.modelo.auditoria(pagina);
    this.navegacion("auditoria");
    this.vista.auditoria(d, p => this.tarea(() => this.auditoria(p)));
  }
  async datos(nombre, pagina) {
    const d = await this.modelo.datos(nombre, pagina);
    this.navegacion("datos");
    this.vista.datos(nombre, d, (n, p) => this.tarea(() => this.datos(n, p)));
  }
}
