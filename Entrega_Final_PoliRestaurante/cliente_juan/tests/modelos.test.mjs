// Pruebas opcionales: node --test cliente_juan/tests/modelos.test.mjs (Node 22+).
import { test } from "node:test";
import assert from "node:assert/strict";
globalThis.location = {
  pathname: "/cliente_juan/cliente.html",
  origin: "http://localhost:5500",
};
const { Pedido } = await import("../js/models/Pedido.js");
const { PedidoModel } = await import("../js/models/PedidoModel.js");
const { ApiError } = await import("../js/models/ApiModel.js");
const storage = () => {
  const m = new Map();
  return {
    getItem: (k) => m.get(k) || null,
    setItem: (k, v) => m.set(k, v),
    removeItem: (k) => m.delete(k),
  };
};
test("Salón requiere mesa; llevar no envía una mesa accidental", () => {
  assert.throws(() => Pedido.crear({ tipo: "SALON", mesa_id: "" }));
  assert.deepEqual(Pedido.crear({ tipo: "LLEVAR", mesa_id: "8" }), {
    tipo: "LLEVAR",
  });
  assert.deepEqual(Pedido.crear({ tipo: "SALON", mesa_id: "3" }), {
    tipo: "SALON",
    mesa_id: 3,
  });
});
test("Cantidad, notas y motivo se validan antes de enviar", () => {
  for (const x of ["0", "100", "1.5", ""])
    assert.throws(() => Pedido.detalle({ cantidad: x }));
  assert.throws(() => Pedido.detalle({ cantidad: 2, notas: "linea\notra" }));
  assert.throws(() => Pedido.motivo("  "));
  assert.deepEqual(Pedido.detalle({ cantidad: "2", notas: " Sin sal " }), {
    cantidad: 2,
    notas: "Sin sal",
  });
});
test("No se ofrece edición ni entrega en estados incorrectos", () => {
  const p = {
    responsable_id: 2,
    cocinero_id: 3,
    estado: "PENDIENTE",
    detalles: [{}],
  };
  assert.equal(Pedido.permisos(p, { id: 2, rol: "MESERO" }).editar, true);
  assert.equal(Pedido.permisos(p, { id: 4, rol: "MESERO" }).editar, false);
  assert.equal(
    Pedido.permisos({ ...p, estado: "LISTO" }, { id: 2, rol: "MESERO" })
      .entregar,
    true,
  );
  assert.equal(
    Pedido.permisos({ ...p, estado: "LISTO" }, { id: 2, rol: "MESERO" })
      .cancelar,
    false,
  );
  assert.equal(
    Pedido.permisos(
      { ...p, estado: "ENTREGADO" },
      { id: 1, rol: "ADMINISTRADOR" },
    ).editar,
    false,
  );
});
test("Una respuesta perdida conserva la UUID y el reintento usa los mismos datos", async () => {
  const enviados = [];
  let falla = true;
  const api = {
    storage: storage(),
    usuario: { id: 2 },
    url: "http://localhost:5000/api/v1",
    enviar: async (r, op) => {
      enviados.push([r, op]);
      if (falla) throw new ApiError("Sin respuesta", "CONEXION");
      return { id: 1, version: 1 };
    },
  };
  const m = new PedidoModel(api);
  await assert.rejects(m.crear({ tipo: "LLEVAR" }));
  assert.ok(m.pendiente());
  await assert.rejects(m.crear({ tipo: "LLEVAR" }));
  falla = false;
  await m.reintentarPendiente();
  assert.deepEqual(enviados[0], enviados[1]);
  assert.equal(m.pendiente(), null);
});
test("Errores definitivos limpian el pendiente y otra cuenta no recupera el recibo", async () => {
  const api = {
    storage: storage(),
    usuario: { id: 2 },
    url: "http://localhost:5000/api/v1",
    enviar: async () => {
      throw new ApiError("Conflicto", "CONFLICTO", 409);
    },
  };
  const m = new PedidoModel(api);
  await assert.rejects(m.crear({ tipo: "LLEVAR" }));
  assert.equal(m.pendiente(), null);
  api.storage.setItem(
    "poli_operacion",
    JSON.stringify({ usuario_id: 9, api_url: api.url }),
  );
  assert.equal(m.pendiente(), null);
  await assert.rejects(m.consultarPendiente(), /No hay una operación pendiente/);
  api.usuario = { id: 9 };
  assert.equal(m.pendiente().usuario_id, 9);
  assert.equal(api.storage.getItem("poli_operacion"), null);
});

const { GestionModel, cuerpoRecurso, hoyColombia, periodo, seccionesDe } =
  await import("../js/models/GestionModel.js");

test("El catálogo de gestión consulta archivos solo para administración", async () => {
  const peticiones = [];
  const api = { usuario: { rol: "ADMINISTRADOR" }, enviar: async (...args) => peticiones.push(args) };
  const gestion = new GestionModel(api);
  await gestion.listar("productos");
  await gestion.listar("mesas");
  await gestion.guardar("categorias", null, { nombre: "Ejemplo" });
  await gestion.guardar("categorias", 5, { nombre: "Editada" });
  await gestion.retirar("categorias", 5);
  api.usuario.rol = "MESERO";
  await gestion.listar("productos");
  assert.deepEqual(peticiones, [
    ["/productos?incluir_archivados=true"], ["/mesas?incluir_archivadas=true"],
    ["/categorias", { method: "POST", body: { nombre: "Ejemplo" } }],
    ["/categorias/5", { method: "PUT", body: { nombre: "Editada" } }],
    ["/categorias/5", { method: "DELETE" }], ["/productos"],
  ]);
  assert.ok(!seccionesDe("MESERO").some(([id]) => id === "usuarios" || id === "cola"));
  assert.ok(seccionesDe("COCINA").some(([id]) => id === "cola"));
  assert.throws(() => gestion.datos("sesion", 1), /Tabla no disponible/);
});

test("La edición de cuenta conserva una clave no ingresada y no degrada al propio administrador", () => {
  const d = { nombre: " Dueño ", login: "ADMIN.DEMO", rol: "COCINA", password: "ClaveTemporal123!" };
  assert.deepEqual(cuerpoRecurso("usuarios", d, { id: 1, rol: "ADMINISTRADOR" }, { id: 1 }),
    { nombre: "Dueño", login: "admin.demo", rol: "ADMINISTRADOR", activo: true });
  assert.ok(!("password" in cuerpoRecurso("usuarios", { ...d, password: "", activo: "on" }, { id: 2 }, { id: 1 })));
  assert.throws(() => cuerpoRecurso("usuarios", { ...d, password: " corta " }), /contraseña/);
  assert.deepEqual(cuerpoRecurso("productos",
    { nombre: "Jugo", precio: "6800,50", categoria_id: "2", activo: "on" }),
    { nombre: "Jugo", descripcion: "", precio: "6800.50", categoria_id: 2, activo: true, disponible: false });
  assert.throws(() => periodo("2024-01-01", "2025-01-01"));
  assert.doesNotThrow(() => periodo("2024-01-01", "2024-12-31"));
});

test("Un pendiente y un recibo se aíslan por cuenta y conexión", async () => {
  const api = { storage: storage(), usuario: { id: 2 }, url: "http://localhost:5000/api/v1",
    enviar: async (_ruta, { body }) => {
      if (body.tipo === "SALON") throw new ApiError("Sin respuesta", "CONEXION");
      return { id: 7 };
    },
  };
  const m = new PedidoModel(api);
  await assert.rejects(m.crear({ tipo: "SALON", mesa_id: 1 }));
  const clave = m.pendiente().clave;
  api.usuario = { id: 3 };
  assert.equal(m.pendiente(), null);
  assert.equal(m.ultimoRecibo(), "");
  await m.crear({ tipo: "LLEVAR" });
  assert.match(m.ultimoRecibo(), /^[0-9a-f-]{36}$/);
  api.usuario = { id: 2 };
  assert.equal(m.ultimoRecibo(), "");
  assert.equal(m.pendiente().clave, clave);
  api.url = "http://localhost:5001/api/v1";
  assert.equal(m.pendiente(), null);
});

test("La fecha inicial de reportes cambia a medianoche de Colombia", () => {
  assert.equal(hoyColombia(new Date("2026-12-01T04:59:59.999Z")), "2026-11-30");
  assert.equal(hoyColombia(new Date("2026-12-01T05:00:00.000Z")), "2026-12-01");
});
