// Un único lugar para cambiar la dirección del servicio REST.
export const API_URL = location.pathname.startsWith("/cliente/")
  ? `${location.origin}/api/v1`
  : "http://127.0.0.1:5000/api/v1";
export const ESTADOS = {
  PENDIENTE: "Pendiente",
  EN_PREPARACION: "En preparación",
  LISTO: "Listo",
  ENTREGADO: "Entregado",
  CANCELADO: "Cancelado",
};
