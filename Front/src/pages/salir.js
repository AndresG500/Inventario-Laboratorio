// Cierra la sesión (se llama con el botón "Cerrar sesión", que envía un formulario POST).
import { borrarSesion } from '../lib/sesion.js';

export async function POST({ cookies, locals, redirect }) {
  try {
    await locals.api?.cerrarSesion();
  } catch {
    // Aunque falle en el servidor, la sesión se borra del navegador.
  }
  borrarSesion(cookies);
  return redirect('/login');
}

export const GET = ({ redirect }) => redirect('/');
