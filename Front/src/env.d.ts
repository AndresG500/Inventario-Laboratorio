declare namespace App {
  interface Locals {
    inv: import('./data/inventario.js').Inventario;
    api: import('./lib/api.js').ClienteApi;
    usuario?: { email: string; nombre: string };
    aviso?: string;
    errorApi?: string;
  }
}
