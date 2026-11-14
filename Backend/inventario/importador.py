"""Importación de inventarios desde archivos .xlsx.

El formato de referencia es INVENTARIO.xlsx (Hoja1):

    ÍTEM | EXPERIENCIA DE LABORATORIO | ASIGNATURA | PRODUCTO | DENOMINACIÓN | CANTIDAD | REFERENCIA | OBSERVACIÓN

- Cada experiencia es un "bloque" de filas: la primera fila trae el ÍTEM, el título de la
  experiencia, la asignatura, la descripción (DENOMINACIÓN), la cantidad de kits y la observación;
  esas celdas suelen estar combinadas verticalmente.
- Cada fila del bloque es un equipo (PRODUCTO + REFERENCIA).
- En la columna EXPERIENCIA, las filas siguientes a la del título traen los temas.

Las columnas se ubican por el texto del encabezado (no por su posición), así que el
orden de las columnas puede cambiar y puede haber columnas adicionales.
"""

from __future__ import annotations

import re
import unicodedata
import zipfile
from dataclasses import dataclass, field

from django.db import transaction
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .formularios import obtener_o_crear_asignatura
from .models import Asignatura, Equipo, Experiencia, Laboratorio


class ErrorImportacion(Exception):
    """Error que se le puede mostrar directamente al usuario."""


# Encabezados reconocidos. Se compara contra el inicio del texto normalizado
# (sin tildes, en mayúsculas), así "DENOMINACIÓN (PASCO, VERNIER, PHYWE)" coincide con "DENOMINACION".
SINONIMOS = {
    "item": ["ITEM", "N°", "NO.", "NUMERO"],
    "experiencia": ["EXPERIENCIA", "PRACTICA"],
    "asignatura": ["ASIGNATURA", "MATERIA"],
    "producto": ["PRODUCTO", "EQUIPO", "NOMBRE DEL EQUIPO", "ELEMENTO"],
    "descripcion": ["DENOMINACION", "DESCRIPCION"],
    "cantidad": ["CANTIDAD", "KITS"],
    "referencia": ["REFERENCIA", "REF", "CODIGO"],
    "observacion": ["OBSERVACION"],
    "marca": ["MARCA"],
    "estado": ["ESTADO"],
}
OBLIGATORIAS = ("item", "experiencia", "producto")
FILAS_BUSQUEDA_ENCABEZADO = 30


def normalizar(texto) -> str:
    """Mayúsculas, sin tildes y con espacios simples. Se usa para comparar textos."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().upper()


def limpiar(texto) -> str | None:
    """Quita espacios repetidos. Devuelve None si queda vacío."""
    if texto is None:
        return None
    t = re.sub(r"\s+", " ", str(texto)).strip()
    return t or None


def limpiar_referencia(texto) -> str | None:
    """'ME - 5718' -> 'ME-5718', 'SF- 9323' -> 'SF-9323'."""
    t = limpiar(texto)
    if not t:
        return None
    t = re.sub(r"\s*-\s*", "-", t)
    return re.sub(r"\s*,\s*", ", ", t)


def a_entero(valor) -> int | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return int(valor)
    m = re.search(r"\d+", str(valor))
    return int(m.group()) if m else None


@dataclass
class BloqueExperiencia:
    item: int
    titulo: str
    fila: int
    asignatura: str | None = None
    descripcion: str | None = None
    observacion: str | None = None
    kits: int | None = None
    temas: list[str] = field(default_factory=list)
    equipos: list[dict] = field(default_factory=list)


# --------------------------------------------------------------------------- lectura


def _ubicar_encabezado(ws):
    for fila in ws.iter_rows(min_row=1, max_row=min(ws.max_row, FILAS_BUSQUEDA_ENCABEZADO)):
        columnas = {}
        for celda in fila:
            texto = normalizar(celda.value)
            if not texto:
                continue
            for clave, opciones in SINONIMOS.items():
                if clave not in columnas and any(texto.startswith(o) for o in opciones):
                    columnas[clave] = celda.column
                    break
        if all(c in columnas for c in OBLIGATORIAS):
            return fila[0].row, columnas
    return None, None


def leer_excel(archivo) -> tuple[list[BloqueExperiencia], dict]:
    """Lee el Excel y devuelve los bloques de experiencias más información del archivo."""
    try:
        wb = load_workbook(archivo, data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError) as exc:
        raise ErrorImportacion("El archivo no es un Excel .xlsx válido.") from exc

    for ws in wb.worksheets:
        fila_enc, columnas = _ubicar_encabezado(ws)
        if fila_enc:
            break
    else:
        raise ErrorImportacion(
            "No se encontró la fila de encabezados. El Excel debe tener al menos las columnas "
            "ÍTEM, EXPERIENCIA y PRODUCTO."
        )

    def valor(fila, clave):
        col = columnas.get(clave)
        return fila[col - 1].value if col and col - 1 < len(fila) else None

    bloques: list[BloqueExperiencia] = []
    advertencias: list[str] = []
    actual: BloqueExperiencia | None = None

    for fila in ws.iter_rows(min_row=fila_enc + 1):
        n = fila[0].row
        item = a_entero(valor(fila, "item"))
        texto_exp = limpiar(valor(fila, "experiencia"))
        producto = limpiar(valor(fila, "producto"))

        if item is not None and (actual is None or item != actual.item):
            if not texto_exp:
                advertencias.append(f"Fila {n}: el ítem {item} no tiene nombre de experiencia; se omitió el bloque.")
                actual = None
                continue
            actual = BloqueExperiencia(item=item, titulo=texto_exp.rstrip(". "), fila=n)
            bloques.append(actual)
        elif actual is not None and texto_exp and normalizar(texto_exp).rstrip(". ") != normalizar(actual.titulo):
            actual.temas.append(texto_exp)

        if actual is None:
            if producto:
                advertencias.append(f"Fila {n}: el producto «{producto}» no pertenece a ningún ítem; se omitió.")
            continue

        # Datos del bloque: se toman de la primera fila que los traiga.
        actual.asignatura = actual.asignatura or limpiar(valor(fila, "asignatura"))
        actual.descripcion = actual.descripcion or limpiar(valor(fila, "descripcion"))
        actual.observacion = actual.observacion or limpiar(valor(fila, "observacion"))
        if actual.kits is None:
            actual.kits = a_entero(valor(fila, "cantidad"))

        if producto:
            actual.equipos.append({
                "nombre": producto,
                "referencia": limpiar_referencia(valor(fila, "referencia")),
                "marca": limpiar(valor(fila, "marca")),
                "estado": limpiar(valor(fila, "estado")),
                "fila_excel": n,
            })

    if not bloques:
        raise ErrorImportacion("El archivo no contiene experiencias con equipos.")

    for b in bloques:
        if not b.equipos:
            advertencias.append(f"Fila {b.fila}: la experiencia «{b.titulo}» no tiene productos.")

    info = {"hoja": ws.title, "fila_encabezado": fila_enc, "advertencias": advertencias}
    return bloques, info


# --------------------------------------------------------------------------- guardado


def _resolver_asignatura(texto: str | None, usuario) -> Asignatura | None:
    """Busca la asignatura del usuario por nombre (sin tildes ni mayúsculas) o la crea."""
    if not texto:
        return None
    clave = normalizar(texto)
    for a in Asignatura.objects.filter(usuario=usuario):
        if normalizar(a.nombre) == clave:
            return a
    return obtener_o_crear_asignatura(usuario, texto.strip().capitalize())


@transaction.atomic
def guardar_bloques(bloques: list[BloqueExperiencia], laboratorio: Laboratorio, sincronizar: bool = False) -> dict:
    """Crea o actualiza experiencias y equipos.

    - Una experiencia se identifica por (laboratorio, ítem).
    - Un equipo se identifica por su nombre dentro de la experiencia.
    - Las celdas vacías del Excel NO borran datos existentes (imagen, estado, enlace,
      referencias completadas a mano, etc.).
    - Con sincronizar=True se eliminan los equipos y experiencias del laboratorio que no
      estén en el archivo.
    """
    r = {
        "experiencias_creadas": 0, "experiencias_actualizadas": 0, "experiencias_eliminadas": 0,
        "equipos_creados": 0, "equipos_actualizados": 0, "equipos_eliminados": 0,
        "equipos_no_incluidos": 0,
    }
    items_en_archivo = set()

    for b in bloques:
        items_en_archivo.add(b.item)
        exp = Experiencia.objects.filter(laboratorio=laboratorio, item=b.item).first()
        if exp is None:
            exp = Experiencia(laboratorio=laboratorio, item=b.item)
            r["experiencias_creadas"] += 1
        else:
            r["experiencias_actualizadas"] += 1

        exp.titulo = b.titulo
        if b.temas:
            exp.temas = " ".join(b.temas)
        exp.descripcion = b.descripcion or exp.descripcion
        exp.observacion = b.observacion or exp.observacion
        if b.kits is not None:
            exp.kits = b.kits
        exp.asignatura = _resolver_asignatura(b.asignatura, laboratorio.usuario) or exp.asignatura
        exp.save()

        # Equipos existentes agrupados por nombre normalizado (en orden).
        existentes: dict[str, list[Equipo]] = {}
        for eq in exp.equipos.order_by("orden", "id"):
            existentes.setdefault(normalizar(eq.nombre), []).append(eq)

        usados = set()
        for orden, datos in enumerate(b.equipos, start=1):
            candidatos = existentes.get(normalizar(datos["nombre"])) or []
            eq = candidatos.pop(0) if candidatos else None
            if eq is None:
                eq = Equipo(experiencia=exp, nombre=datos["nombre"])
                r["equipos_creados"] += 1
            else:
                r["equipos_actualizados"] += 1
            eq.orden = orden
            eq.fila_excel = datos["fila_excel"]
            for campo in ("referencia", "marca", "estado"):
                if datos[campo]:
                    setattr(eq, campo, datos[campo])
            if b.kits is not None:
                eq.cantidad = b.kits
            eq.save()
            usados.add(eq.pk)

        sobrantes = exp.equipos.exclude(pk__in=usados)
        if sincronizar:
            r["equipos_eliminados"] += sobrantes.count()
            sobrantes.delete()
        else:
            r["equipos_no_incluidos"] += sobrantes.count()

    if sincronizar:
        viejas = Experiencia.objects.filter(laboratorio=laboratorio).exclude(item__in=items_en_archivo)
        r["equipos_eliminados"] += Equipo.objects.filter(experiencia__in=viejas).count()
        r["experiencias_eliminadas"] = viejas.count()
        viejas.delete()

    return r


def importar_excel(archivo, laboratorio: Laboratorio, sincronizar: bool = False) -> dict:
    bloques, info = leer_excel(archivo)
    resultado = guardar_bloques(bloques, laboratorio, sincronizar=sincronizar)
    return {**info, **resultado, "experiencias_en_archivo": len(bloques),
            "equipos_en_archivo": sum(len(b.equipos) for b in bloques)}
