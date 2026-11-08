import { API_URL } from "../config.js";
export class ApiError extends Error {
  constructor(mensaje, codigo, estado = 0) {
    super(mensaje);
    this.codigo = codigo;
    this.estado = estado;
  }
}
/** Modelo HTTP: no consulta ni modifica el DOM. Nunca almacena contraseñas. */
export class ApiModel {
  constructor(storage = sessionStorage) {
    this.storage = storage;
    this.url = storage.getItem("poli_api_url") || API_URL;
    this.token = storage.getItem("poli_token") || "";
    this.usuario = null;
  }
  configurar(url) {
    const u = new URL(url);
    if (
      !["http:", "https:"].includes(u.protocol) ||
      u.username ||
      u.password ||
      u.search ||
      u.hash
    )
      throw new Error(
        "La dirección de la API debe ser HTTP/HTTPS y no contener credenciales, consulta o fragmentos.",
      );
    this.url = u.href.replace(/\/$/, "");
    this.storage.setItem("poli_api_url", this.url);
  }
  async enviar(ruta, { method = "GET", body, clave } = {}) {
    const headers = {};
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (clave) headers["Idempotency-Key"] = clave;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(this.url + ruta, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
        cache: "no-store",
      });
      let data;
      try {
        data = await response.json();
      } catch {
        throw new ApiError(
          "El servidor no devolvió una respuesta JSON válida.",
          "RESPUESTA",
          response.status,
        );
      }
      if (!response.ok || !data.ok)
        throw new ApiError(
          data.error?.mensaje || "No se completó la solicitud.",
          data.error?.codigo || "HTTP",
          response.status,
        );
      return data.datos;
    } catch (e) {
      if (e instanceof ApiError) throw e;
      throw new ApiError(
        "No se pudo confirmar la respuesta. Revisa que la API esté activa y que el origen de Live Server esté permitido.",
        "CONEXION",
      );
    } finally {
      clearTimeout(timer);
    }
  }
  async login(login, password, url) {
    this.configurar(url);
    // Si cambia la cuenta no se envía un Bearer de la cuenta anterior al login.
    this.token = "";
    this.usuario = null;
    this.storage.removeItem("poli_token");
    const d = await this.enviar("/auth/login", {
      method: "POST",
      body: { login, password },
    });
    this.token = d.token;
    this.usuario = d.usuario;
    this.storage.setItem("poli_token", d.token);
    return d.usuario;
  }
  async perfil() {
    this.usuario = await this.enviar("/auth/me");
    return this.usuario;
  }
  limpiar() {
    this.token = "";
    this.usuario = null;
    this.storage.removeItem("poli_token");
  }
  async salir() {
    try {
      if (this.token) await this.enviar("/auth/logout", { method: "POST" });
    } finally {
      this.limpiar();
    }
  }
  async cambiarClave(actual, nueva) {
    await this.enviar("/auth/password", {
      method: "PUT",
      body: { actual, nueva },
    });
    this.limpiar();
  }
}
