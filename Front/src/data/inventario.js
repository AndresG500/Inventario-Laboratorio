// Datos del inventario del usuario. El middleware los pide a la API de Django en cada petición
// y los deja en Astro.locals.inv (ver src/middleware.js).

// Estados que se pueden elegir al editar un equipo. "valor" es lo que se guarda en la base de datos.
export const ESTADOS = [
  { valor: 'OK', etiqueta: 'Operativo', tono: 'ok' },
  { valor: 'EN REPARACION', etiqueta: 'En reparación', tono: 'aviso' },
  { valor: 'DAÑADO', etiqueta: 'Dañado', tono: 'malo' },
  { valor: 'DADO DE BAJA', etiqueta: 'Dado de baja', tono: 'baja' },
];

export function estadoDe(estado) {
  if (!estado) return { etiqueta: 'Sin registrar', tono: 'vacio' };
  return ESTADOS.find((e) => e.valor === estado.toUpperCase()) ?? { etiqueta: legible(estado), tono: 'neutro' };
}

/** Opciones del campo "Estado"; si el equipo tiene un estado que no está en la lista, también se incluye. */
export function opcionesEstado(actual) {
  const opciones = [{ valor: '', texto: 'Sin registrar' }, ...ESTADOS.map((e) => ({ valor: e.valor, texto: e.etiqueta }))];
  if (actual && !opciones.some((o) => o.valor === actual.toUpperCase())) opciones.push({ valor: actual, texto: legible(actual) });
  return opciones;
}

// El Excel viene en MAYÚSCULAS; se pasa a tipo oración solo cuando todo el texto está en mayúsculas.
export function legible(texto) {
  if (!texto) return '';
  if (texto !== texto.toUpperCase()) return texto;
  const t = texto.toLowerCase();
  return t.charAt(0).toUpperCase() + t.slice(1);
}

// Separa los temas por comas o puntos, sin cortar lo que va entre paréntesis.
export function temasDe(experiencia) {
  if (!experiencia.temas) return [];
  const partes = [];
  let actual = '';
  let nivel = 0;
  for (const c of experiencia.temas) {
    if (c === '(') nivel++;
    if (c === ')') nivel = Math.max(0, nivel - 1);
    if (nivel === 0 && (c === ',' || c === '.')) {
      partes.push(actual);
      actual = '';
    } else {
      actual += c;
    }
  }
  partes.push(actual);
  return partes
    .map((t) => legible(t.replace(/\s+/g, ' ').trim()).replace(/\s+\(/, ' ('))
    .filter((t) => t.length > 2);
}

export const INVENTARIO_VACIO = { asignaturas: [], laboratorios: [], experiencias: [], equipos: [] };

/**
 * Recibe la respuesta de GET /api/inventario/ y devuelve los datos con las mismas
 * funciones de consulta que usaban las páginas cuando todo venía del JSON.
 */
export function crearInventario(datos = INVENTARIO_VACIO) {
  const { asignaturas = [], laboratorios = [], experiencias = [], equipos = [] } = datos;

  // Los id son números en la API y texto en las URL; se comparan siempre como texto.
  const igual = (a, b) => a != null && b != null && String(a) === String(b);
  const porId = (lista) => new Map(lista.map((x) => [String(x.id), x]));
  const mapaAsig = porId(asignaturas);
  const mapaLab = porId(laboratorios);
  const mapaExp = porId(experiencias);

  const mapaEq = porId(equipos);
  const asignaturaDe = (id) => mapaAsig.get(String(id));
  const laboratorioDe = (id) => mapaLab.get(String(id));
  const experienciaDe = (id) => mapaExp.get(String(id));
  const equipoDe = (id) => mapaEq.get(String(id));
  const componenteDe = (id) => {
    for (const e of equipos) {
      const c = (e.componentes ?? []).find((c) => igual(c.id, id));
      if (c) return c;
    }
    return undefined;
  };
  const equiposDe = (expId) => equipos.filter((e) => igual(e.experiencia, expId));
  const experienciasDe = (asigId) => experiencias.filter((x) => igual(x.asignatura, asigId));
  const experienciasDeLaboratorio = (labId) => experiencias.filter((x) => igual(x.laboratorio, labId));
  const equiposDeLaboratorio = (labId) => equipos.filter((e) => igual(e.laboratorio, labId));
  const equiposDeAsignatura = (asigId) => equipos.filter((e) => igual(experienciaDe(e.experiencia)?.asignatura, asigId));

  function resumen(lista = equipos) {
    return {
      equipos: lista.length,
      unidades: lista.reduce((s, e) => s + (e.cantidad ?? 0), 0),
      conEstado: lista.filter((e) => e.estado).length,
      sinNombre: lista.filter((e) => !e.nombre).length,
      malos: lista.filter((e) => estadoDe(e.estado).tono === 'malo').length,
      sinReferencia: lista.filter((e) => !e.referencia).length,
    };
  }

  // Versión plana de cada equipo para el panel de detalle (se envía al navegador como JSON).
  function fichaEquipo(e) {
    const exp = experienciaDe(e.experiencia);
    const estado = estadoDe(e.estado);
    return {
      id: e.id,
      nombre: e.nombre ? legible(e.nombre) : null,
      marca: e.marca,
      referencia: e.referencia,
      cantidad: e.cantidad,
      estado: estado.etiqueta,
      tono: estado.tono,
      imagen: e.imagen,
      enlace: e.enlace,
      componentes: e.componentes ?? [],
      experiencia: legible(exp?.titulo),
      experienciaId: e.experiencia,
      asignatura: asignaturaDe(exp?.asignatura)?.nombre,
      laboratorio: laboratorioDe(e.laboratorio)?.nombre,
      fila: e.fila_excel,
      editar: `/equipos/${e.id}/editar`,
    };
  }

  return {
    asignaturas, laboratorios, experiencias, equipos, igual,
    asignaturaDe, laboratorioDe, experienciaDe, equipoDe, componenteDe, equiposDe, experienciasDe,
    experienciasDeLaboratorio, equiposDeLaboratorio, equiposDeAsignatura,
    resumen, fichaEquipo,
  };
}

/** @typedef {ReturnType<typeof crearInventario>} Inventario */
