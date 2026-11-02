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
  await assert.rejects(m.consultarPendiente(), /otra cuenta/);
});
