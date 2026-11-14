// En cada petición:
// 1. Comprueba la sesión (cookie) y, si no hay, manda al usuario a /login.
// 2. Trae su inventario desde Django y lo deja en Astro.locals.inv.
import { defineMiddleware } from 'astro:middleware';
import { crearInventario } from './data/inventario.js';
import { clienteApi } from './lib/api.js';
import { COOKIE_SESION, borrarSesion, leerAviso } from './lib/sesion.js';

const PUBLICAS = new Set(['/login', '/registro']);
const SIN_INVENTARIO = new Set(['/cambiar-contrasena', '/salir']);

export const onRequest = defineMiddleware(async (contexto, siguiente) => {
  const { url, cookies, locals, redirect } = contexto;
  const ruta = url.pathname.replace(/\/+$/, '') || '/';
  locals.inv = crearInventario();
  locals.aviso = leerAviso(cookies);

  if (PUBLICAS.has(ruta)) return siguiente();

  const token = cookies.get(COOKIE_SESION)?.value;
  const alLogin = () => redirect(`/login?siguiente=${encodeURIComponent(url.pathname + url.search)}`);
  if (!token) return alLogin();

  const api = clienteApi(token);
  try {
    locals.usuario = (await api.yo()).usuario;
  } catch (error) {
    if (/** @type {any} */ (error)?.status === 401) {
      borrarSesion(cookies);
      return alLogin();
    }
    locals.errorApi = error instanceof Error ? error.message : String(error);
    return siguiente();
  }
  locals.api = api;

  if (!SIN_INVENTARIO.has(ruta)) {
    try {
      locals.inv = crearInventario(await api.inventario());
    } catch (error) {
      locals.errorApi = error instanceof Error ? error.message : String(error);
    }
  }
  return siguiente();
});
