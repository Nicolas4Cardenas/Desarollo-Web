import { Pedido } from "../models/Pedido.js";
/** CONTROLADOR MVC: recibe eventos, valida intención y coordina Modelo y Vista. */
export class PedidoController {
  constructor(api, modelo, vista) {
    this.api = api;
    this.modelo = modelo;
    this.vista = vista;
    this.pedido = null;
    this.datos = { items: [], pagina: 1, hay_mas: false };
    this.estado = "";
    this.abiertos = false;
    this.seccion = "pedidos";
    this.busqueda = "";
    this.bloqueado = false;
    vista.conectar({
      login: (d) => this.tarea(() => this.login(d)),
      password: (d) => this.tarea(() => this.cambiarClave(d)),
      crear: (d) => this.tarea(() => this.crear(d)),
      agregar: (d) => this.tarea(() => this.agregar(d)),
      editar: (d) => this.tarea(() => this.editar(d)),
      confirmar: (d) => this.tarea(() => this.confirmar(d)),
      filtrar: (d) =>
        this.tarea(() => {
          this.estado = d.estado;
          this.abiertos = d.abiertos === "on";
          return this.cargar(1);
        }),
      buscar: (t) => {
        this.busqueda = t;
        this.pintarLista();
      },
      accion: (a, id) => this.tarea(() => this.accion(a, id)),
    });
  }
  async iniciar() {
    this.vista.configurar(this.api.url);
    if (!this.api.token) {
      this.vista.pantalla();
      return;
    }
    await this.tarea(async () => {
      await this.api.perfil();
      await this.entrar();
    });
  }
  async tarea(fn, { pedido = true } = {}) {
    if (this.bloqueado) return;
    this.bloqueado = true;
    this.vista.ocupado(true);
    try {
      await fn();
    } catch (e) {
      if (e.codigo === "SESION") {
        this.api.limpiar();
        this.gestion?.limpiarSesion();
        this.pedido = null;
        this.vista.cerrarDialogos();
        this.vista.detalle(null);
        this.vista.pantalla();
      }
      if (pedido && e.codigo === "NO_EXISTE" && this.modelo.pendiente())
        e.message =
          "Aún no hay un resultado confirmado para esa clave. Reintenta la misma operación con el botón del aviso.";
      if (pedido && e.estado === 409 && this.api.usuario) {
        this.vista.cerrarDialogos();
        try {
          await this.cargar(this.datos.pagina);
          if (this.pedido) await this.seleccionar(this.pedido.id);
        } catch {
          /* Se mantiene el error original si la recarga también falla. */
        }
      }
      this.vista.mensaje(e.message || "No se completó la operación.", "danger");
    } finally {
      this.bloqueado = false;
      this.vista.ocupado(false);
      this.vista.pendiente(this.api.usuario ? this.modelo.pendiente() : null);
    }
  }
  async login(d) {
    await this.api.login(d.login.trim(), d.password, d.api_url);
    this.vista.limpiarLogin();
    await this.entrar();
    this.vista.mensaje("Sesión iniciada correctamente.");
  }
  async entrar() {
    this.vista.pantalla(this.api.usuario);
    this.vista.mensaje("");
    if (this.api.usuario.debe_cambiar) {
      this.gestion?.limpiarSesion();
      return;
    }
    this.pedido = null;
    this.vista.detalle(null);
    if (this.gestion) await this.gestion.iniciarSesion();
    else await Promise.all([this.cargarCatalogo(), this.cargar(1)]);
  }
  async cambiarClave(d) {
    if (d.nueva !== d.repite)
      throw new Error("Las contraseñas nuevas no coinciden.");
    if (d.nueva.length < 10 || d.nueva.length > 128)
      throw new Error("La contraseña debe tener de 10 a 128 caracteres.");
    await this.api.cambiarClave(d.actual, d.nueva);
    this.gestion?.limpiarSesion();
    this.vista.limpiarClaves();
    this.vista.pantalla();
    this.vista.mensaje(
      "Contraseña actualizada. Vuelve a iniciar sesión con la nueva contraseña.",
    );
  }
  pintarLista() {
    this.vista.listado(this.datos, this.pedido?.id, this.busqueda);
  }
  async modo(seccion) {
    const cola = seccion === "cola";
    const [datos] = await Promise.all([
      cola ? this.modelo.cola(1) : this.modelo.listar("", 1),
      this.cargarCatalogo(),
    ]);
    this.seccion = seccion;
    this.estado = "";
    this.abiertos = false;
    this.busqueda = "";
    this.pedido = null;
    this.vista.modo(cola, this.api.usuario.rol);
    this.vista.detalle(null);
    this.datos = datos;
    this.pintarLista();

  }
  async cargar(pagina = this.datos.pagina) {
    this.datos = this.seccion === "cola" ? await this.modelo.cola(pagina) :
      await this.modelo.listar(this.estado, pagina, this.abiertos);
    this.pintarLista();
  }
  async cargarCatalogo() {
    const [p, c] = await Promise.all([
      this.modelo.productos(),
      this.modelo.categorias(),
    ]);
    this.vista.catalogo(p, c);
  }
  async seleccionar(id, enfocar = false) {
    this.pedido = await this.modelo.obtener(id);
    this.vista.detalle(
      this.pedido,
      Pedido.permisos(this.pedido, this.api.usuario),
      enfocar,
    );
    this.pintarLista();
  }
  exigirPedido() {
    if (!this.pedido) throw new Error("Abre primero un pedido.");
    return this.pedido;
  }
  async resultado(r, mensaje) {
    this.vista.cerrarDialogos();
    this.vista.limpiarAgregar();
    if (this.gestion && !["pedidos", "cola"].includes(this.gestion.actual))
      await this.gestion.abrir(this.api.usuario.rol === "COCINA" ? "cola" : "pedidos");
    else await this.cargar();
    if (r.id) await this.seleccionar(r.id, true);
    this.vista.mensaje(mensaje || r.mensaje || "Operación completada.");
  }
  async crear(d) {
    const body = Pedido.crear(d);
    if (this.api.usuario.rol === "ADMINISTRADOR" && d.responsable_id)
      body.responsable_id = Pedido.entero(d.responsable_id, "Responsable");
    const r = await this.modelo.crear(body);
    await this.resultado(r, "Pedido creado. Agrega sus productos.");
  }
  async agregar(d) {
    const p = this.exigirPedido();
    const datos = {
      ...Pedido.detalle(d),
      producto_id: Pedido.entero(d.producto_id, "Producto"),
    };
    await this.resultado(
      await this.modelo.agregar(p, datos),
      "Producto agregado al pedido.",
    );
  }
  async editar(d) {
    const p = this.exigirPedido();
    await this.resultado(
      await this.modelo.editar(
        p,
        Pedido.entero(d.detalle_id, "Detalle"),
        Pedido.detalle(d),
      ),
      "Cambios guardados.",
    );
  }
  async confirmar(d) {
    const p = this.exigirPedido();
    const c = this.vista.confirmacionActual();
    if (c.accion === "quitar")
      return this.resultado(
        await this.modelo.quitar(p, c.id),
        "Producto retirado del pedido.",
      );
    const motivo = c.accion === "CANCELADO" ? Pedido.motivo(d.motivo) : "";
    return this.resultado(await this.modelo.estado(p, c.accion, motivo));
  }
  async accion(a, id) {
    if (a === "salir") {
      try {
        await this.api.salir();
      } finally {
        this.pedido = null;
        this.gestion?.limpiarSesion();
        this.vista.detalle(null);
        this.vista.cerrarDialogos();
        this.vista.pantalla();
      }
      this.vista.mensaje("Sesión cerrada.");
      return;
    }
    if (a === "nuevo") {
      const admin = this.api.usuario.rol === "ADMINISTRADOR";
      const [mesas, elegibles] = await Promise.all([
        this.modelo.mesas(), admin && this.gestion ? this.gestion.modelo.elegibles() : null,
      ]);
      this.vista.nuevo(mesas, elegibles?.responsables.filter(u => u.id !== this.api.usuario.id) ?? null);
      return;
    }
    if (a === "abrir") return this.seleccionar(id, true);
    if (a === "recargar") {
      await this.cargar();
      await this.cargarCatalogo();
      if (this.pedido) await this.seleccionar(this.pedido.id);
      this.vista.mensaje("Pedidos y catálogo actualizados.");
      return;
    }
    if (a === "anterior") return this.cargar(this.datos.pagina - 1);
    if (a === "siguiente") return this.cargar(this.datos.pagina + 1);
    if (a === "catalogo") {
      const r = await this.modelo.catalogo();
      await this.cargarCatalogo();
      this.vista.mensaje(r.mensaje);
      return;
    }
    if (a === "consultar-operacion")
      return this.resultado(
        await this.modelo.consultarPendiente(),
        "Operación confirmada y recuperada.",
      );
    if (a === "reintentar-operacion")
      return this.resultado(
        await this.modelo.reintentarPendiente(),
        "Resultado recuperado sin duplicar la operación.",
      );
    const p = this.exigirPedido();
    if (a === "reasignar") return this.gestion?.reasignar(p);
    if (a === "editar-linea") {
      const d = p.detalles.find((x) => x.id === id);
      if (!d) throw new Error("Actualiza el pedido antes de editar.");
      this.vista.editar(d);
      return;
    }
    if (a === "quitar-linea") {
      this.vista.confirmar(
        "quitar",
        id,
        "Quitar producto",
        "Se retirará esta línea del pedido pendiente.",
      );
      return;
    }
    const estados = {
      preparar: [
        "EN_PREPARACION",
        "Iniciar preparación",
        "La cocina tomará el pedido y sus productos dejarán de ser editables.",
      ],
      listo: [
        "LISTO",
        "Marcar pedido listo",
        "Confirma que la preparación de todos los productos terminó.",
      ],
      entregar: [
        "ENTREGADO",
        "Registrar entrega",
        "Confirma que entregaste la orden. La mesa quedará disponible.",
      ],
      cancelar: [
        "CANCELADO",
        "Cancelar pedido",
        "El pedido y su historial se conservarán. La mesa quedará disponible.",
      ],
    };
    if (estados[a]) {
      const [e, t, x] = estados[a];
      this.vista.confirmar(e, p.id, t, x, e === "CANCELADO");
    }
  }
}
