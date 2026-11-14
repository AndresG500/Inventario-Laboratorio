// Comunicación con el backend de Django. Solo se ejecuta en el servidor de Astro.
//
// Variables de entorno:
//   DJANGO_API_URL   URL del backend, por defecto http://localhost:8000

const env = (nombre) => process.env[nombre] ?? import.meta.env[nombre];

export const API_URL = (env('DJANGO_API_URL') || 'http://localhost:8000').replace(/\/+$/, '');

/** Error devuelto por la API. `campos` trae los errores de cada campo de un formulario. */
export class ErrorApi extends Error {
  constructor(mensaje, status = 0, campos = {}) {
    super(mensaje);
    this.status = status;
    this.campos = campos;
  }
}

async function pedir(ruta, { token, metodo = 'GET', json, cuerpo } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Token ${token}`;
  if (json !== undefined) headers['Content-Type'] = 'application/json';

  let res;
  try {
    res = await fetch(`${API_URL}${ruta}`, {
      method: metodo,
      headers,
      body: json !== undefined ? JSON.stringify(json) : cuerpo,
    });
  } catch {
    throw new ErrorApi('No se pudo conectar con el servidor. Intenta de nuevo en unos minutos.');
  }
  let datos = null;
  try {
    datos = await res.json();
  } catch {
    // respuesta sin JSON (por ejemplo, una página de error de Django)
  }
  if (!res.ok) throw new ErrorApi(datos?.error ?? `El servidor respondió con el código ${res.status}.`, res.status, datos?.campos ?? {});
  return datos;
}

export const dominiosRegistro = () => pedir('/api/auth/registro/');

export const registrarse = (datos) => pedir('/api/auth/registro/', { metodo: 'POST', json: datos });

export const iniciarSesion = (email, password) =>
  pedir('/api/auth/login/', { metodo: 'POST', json: { email, password } });

/** Cliente de la API con la sesión del usuario. */
export function clienteApi(token) {
  return {
    yo: () => pedir('/api/auth/yo/', { token }),
    cerrarSesion: () => pedir('/api/auth/logout/', { token, metodo: 'POST' }),
    cambiarContrasena: (datos) => pedir('/api/auth/cambiar-contrasena/', { token, metodo: 'POST', json: datos }),

    inventario: () => pedir('/api/inventario/', { token }),
    importaciones: () => pedir('/api/importaciones/', { token }),
    /** Reenvía el formulario de importación a Django. */
    importar(formulario) {
      const datos = new FormData();
      for (const campo of ['archivo', 'laboratorio', 'laboratorio_nuevo', 'sincronizar']) {
        const valor = formulario.get(campo);
        if (valor !== null && valor !== '') datos.append(campo, valor);
      }
      return pedir('/api/importar/', { token, metodo: 'POST', cuerpo: datos });
    },

    // CRUD: recurso = laboratorios | asignaturas | experiencias | equipos | componentes
    crear: (recurso, datos) => pedir(`/api/${recurso}/`, { token, metodo: 'POST', json: datos }),
    modificar: (recurso, id, datos) => pedir(`/api/${recurso}/${id}/`, { token, metodo: 'PATCH', json: datos }),
    eliminar: (recurso, id) => pedir(`/api/${recurso}/${id}/`, { token, metodo: 'DELETE' }),
  };
}

/** @typedef {ReturnType<typeof clienteApi>} ClienteApi */
