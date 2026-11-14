// Utilidades para los formularios del CRUD.

/** Convierte los campos indicados del formulario en un objeto (texto sin espacios sobrantes). */
export function datosDe(formulario, campos) {
  const datos = {};
  for (const campo of campos) {
    const valor = formulario.get(campo);
    datos[campo] = typeof valor === 'string' ? valor.trim() : '';
  }
  return datos;
}

/**
 * Ejecuta una llamada a la API.
 * Devuelve { resultado } si salió bien, o { error, campos } si falló; `campos` son los errores
 * de cada campo que devuelve Django (por ejemplo { nombre: ['Este campo es obligatorio.'] }).
 */
export async function intentar(accion) {
  try {
    return { resultado: await accion(), error: null, campos: {} };
  } catch (e) {
    return {
      resultado: null,
      error: e instanceof Error ? e.message : String(e),
      campos: /** @type {any} */ (e)?.campos ?? {},
    };
  }
}
