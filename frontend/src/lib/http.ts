/**
 * Cliente HTTP único. Agrega el token y traduce los errores del backend a mensajes en español.
 * `codigo` es la etiqueta corta que manda el backend (ej. "consentimiento_requerido") para que la app sepa qué hacer.
 */
const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(public status: number, message: string, public codigo?: string) {
    super(message);
    this.name = 'ApiError';
  }
}

let obtenerToken: () => string | null = () => null;
let alPerderSesion: () => void = () => {};

export function configurarHttp(o: { obtenerToken: () => string | null; alPerderSesion: () => void }) {
  obtenerToken = o.obtenerToken;
  alPerderSesion = o.alPerderSesion;
}

type Opciones = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'; body?: unknown; conToken?: boolean;
  /** Corta la espera a los N milisegundos (ej. la IA: si tarda más de 15 s se muestra un error). */
  limiteMs?: number;
};

const SIN_CONEXION = 'No hay conexión con el servidor. Revisa tu internet e intenta de nuevo.';

function errorDeRespuesta(status: number, datos: unknown): ApiError {
  const d = datos as { detail?: unknown; codigo?: string } | null;
  const msg =
    typeof d?.detail === 'string' ? d.detail
      : status >= 500 ? 'Ocurrió un error en el servidor. Intenta de nuevo.'
      : 'No se pudo completar la acción.';
  return new ApiError(status, msg, d?.codigo);
}

export async function api<T>(ruta: string, { method = 'GET', body, conToken = true, limiteMs }: Opciones = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const token = conToken ? obtenerToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let r: Response;
  try {
    r = await fetch(`${BASE_URL}/api${ruta}`, {
      method, headers, body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: limiteMs ? AbortSignal.timeout(limiteMs) : undefined,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === 'TimeoutError') throw new ApiError(0, 'El servidor tardó demasiado en responder.', 'tiempo_agotado');
    throw new ApiError(0, SIN_CONEXION, 'sin_conexion');
  }

  if (r.status === 401 && token) alPerderSesion(); // sesión vencida o cerrada desde otro lado

  const datos = r.status === 204 ? null : await r.json().catch(() => null);
  if (!r.ok) throw errorDeRespuesta(r.status, datos);
  return datos as T;
}

/** Las rutas de fotos que da la API (/api/fotos/…) se vuelven absolutas si el backend vive en otro dominio. */
export const urlApi = (ruta: string) => `${BASE_URL}${ruta}`;

export interface Subida<T> { promesa: Promise<T>; cancelar: () => void }

/**
 * Sube un archivo mostrando el progreso (0–100) y permitiendo cancelar (PG-07).
 * Usa XMLHttpRequest porque fetch todavía no informa el progreso de subida.
 */
export function subirArchivo<T>(ruta: string, campo: string, archivo: Blob, nombre: string, alProgreso: (pct: number) => void): Subida<T> {
  const xhr = new XMLHttpRequest();
  const promesa = new Promise<T>((resolver, rechazar) => {
    xhr.open('POST', `${BASE_URL}/api${ruta}`);
    const token = obtenerToken();
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.upload.onprogress = e => { if (e.lengthComputable) alProgreso(Math.round((e.loaded / e.total) * 100)); };
    xhr.onload = () => {
      let datos: unknown = null;
      try { datos = xhr.responseText ? JSON.parse(xhr.responseText) : null; } catch { /* respuesta vacía */ }
      if (xhr.status === 401 && token) alPerderSesion();
      if (xhr.status >= 200 && xhr.status < 300) resolver(datos as T);
      else rechazar(errorDeRespuesta(xhr.status, datos));
    };
    xhr.onerror = () => rechazar(new ApiError(0, SIN_CONEXION, 'sin_conexion'));
    xhr.onabort = () => rechazar(new ApiError(0, 'Subida cancelada.', 'cancelada'));
    const form = new FormData();
    form.append(campo, archivo, nombre);
    xhr.send(form);
  });
  return { promesa, cancelar: () => xhr.abort() };
}
