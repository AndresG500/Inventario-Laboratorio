// Cookies de la sesión y mensajes de un solo uso ("Equipo guardado", etc.).

export const COOKIE_SESION = 'sesion';
const COOKIE_AVISO = 'aviso';
const SIETE_DIAS = 60 * 60 * 24 * 7;

const opciones = (url) => ({
  path: '/',
  httpOnly: true,
  sameSite: /** @type {const} */ ('lax'),
  secure: url.protocol === 'https:',
});

export function guardarSesion(cookies, url, token) {
  cookies.set(COOKIE_SESION, token, { ...opciones(url), maxAge: SIETE_DIAS });
}

export function borrarSesion(cookies) {
  cookies.delete(COOKIE_SESION, { path: '/' });
}

/** Deja un mensaje que se muestra en la siguiente página que se cargue. */
export function avisar(cookies, url, texto) {
  cookies.set(COOKIE_AVISO, texto, { ...opciones(url), maxAge: 60 });
}

export function leerAviso(cookies) {
  const texto = cookies.get(COOKIE_AVISO)?.value;
  if (texto) cookies.delete(COOKIE_AVISO, { path: '/' });
  return texto;
}

/** Evita redirecciones a otros sitios: solo se aceptan rutas internas. */
export function rutaSegura(ruta, porDefecto = '/') {
  return typeof ruta === 'string' && ruta.startsWith('/') && !ruta.startsWith('//') && !ruta.startsWith('/\\')
    ? ruta
    : porDefecto;
}
