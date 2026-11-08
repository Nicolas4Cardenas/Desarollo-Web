/** Modelo de dominio del cliente. El servidor vuelve a validar todas las reglas. */
export class Pedido {
  static entero(valor, nombre, maximo = 2147483647) {
    const n = Number(valor);
    if (!Number.isInteger(n) || n < 1 || n > maximo)
      throw new Error(`${nombre}: ingresa un entero entre 1 y ${maximo}.`);
    return n;
  }
  static crear(datos) {
    if (!["SALON", "LLEVAR"].includes(datos.tipo))
      throw new Error("Selecciona el tipo de servicio.");
    return datos.tipo === "SALON"
      ? { tipo: datos.tipo, mesa_id: this.entero(datos.mesa_id, "Mesa") }
      : { tipo: datos.tipo };
  }
  static detalle(datos) {
    const notas = (datos.notas || "").trim();
    if (notas.length > 255 || /[\u0000-\u001f\u007f]/.test(notas))
      throw new Error(
        "Las observaciones deben tener hasta 255 caracteres, sin saltos de línea.",
      );
    return { cantidad: this.entero(datos.cantidad, "Cantidad", 99), notas };
  }
  static motivo(valor) {
    const motivo = (valor || "").trim();
    if (!motivo || motivo.length > 255 || /[\u0000-\u001f\u007f]/.test(motivo))
      throw new Error(
        "Escribe un motivo de cancelación de 1 a 255 caracteres, en una línea.",
      );
    return motivo;
  }
  static permisos(pedido, usuario) {
    const admin = usuario.rol === "ADMINISTRADOR";
    const mesero =
      usuario.rol === "MESERO" && pedido.responsable_id === usuario.id;
    const cocina = usuario.rol === "COCINA";
    return {
      reasignar: admin && ["PENDIENTE", "EN_PREPARACION", "LISTO"].includes(pedido.estado),
      editar: (admin || mesero) && pedido.estado === "PENDIENTE",
      entregar: (admin || mesero) && pedido.estado === "LISTO",
      cancelar:
        (admin || mesero) &&
        ["PENDIENTE", "EN_PREPARACION", ...(admin ? ["LISTO"] : [])].includes(
          pedido.estado,
        ),
      preparar:
        (admin || cocina) &&
        pedido.estado === "PENDIENTE" &&
        pedido.detalles.length > 0,
      listo:
        (admin || (cocina && pedido.cocinero_id === usuario.id)) &&
        pedido.estado === "EN_PREPARACION",
    };
  }
}
