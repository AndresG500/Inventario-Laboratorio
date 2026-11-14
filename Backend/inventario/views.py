"""API del inventario. Todas las vistas exigen sesión y solo ven los datos del usuario.

GET  /api/inventario/        Todo el inventario del usuario.
GET  /api/importaciones/     Últimas importaciones del usuario.
POST /api/importar/          Sube un .xlsx (multipart/form-data): archivo, laboratorio (id) o
                             laboratorio_nuevo (nombre), sincronizar ("1").

CRUD (JSON) para laboratorios, asignaturas, experiencias, equipos y componentes:
GET    /api/<recurso>/          Lista
POST   /api/<recurso>/          Crear
GET    /api/<recurso>/<id>/     Detalle
PATCH  /api/<recurso>/<id>/     Modificar (solo los campos enviados)
DELETE /api/<recurso>/<id>/     Eliminar (en cascada)
"""

from dataclasses import dataclass
from typing import Callable

from django.db.models import Prefetch
from django.forms.models import model_to_dict
from django.views.decorators.http import require_GET, require_POST

from core.api import error, leer_json, ok
from cuentas.autenticacion import requiere_sesion

from . import formularios
from .importador import ErrorImportacion, importar_excel
from .models import Asignatura, Componente, Equipo, Experiencia, Importacion, Laboratorio

TAMANO_MAXIMO = 10 * 1024 * 1024  # 10 MB


# --------------------------------------------------------------------------- serialización


def _laboratorio(l: Laboratorio):
    return {"id": l.id, "nombre": l.nombre, "hoja": l.hoja}


def _asignatura(a: Asignatura):
    return {"id": a.id, "nombre": a.nombre}


def _experiencia(x: Experiencia):
    return {
        "id": x.id, "laboratorio": x.laboratorio_id, "asignatura": x.asignatura_id, "item": x.item,
        "titulo": x.titulo, "temas": x.temas, "descripcion": x.descripcion,
        "observacion": x.observacion, "kits": x.kits,
    }


def _componente(c: Componente):
    return {"id": c.id, "equipo": c.equipo_id, "cantidad": c.cantidad, "nombre": c.nombre,
            "referencia": c.referencia, "enlace": c.enlace, "estado": c.estado}


def _equipo(e: Equipo):
    return {
        "id": e.id, "experiencia": e.experiencia_id, "laboratorio": e.experiencia.laboratorio_id,
        "nombre": e.nombre, "marca": e.marca, "referencia": e.referencia, "cantidad": e.cantidad,
        "estado": e.estado, "imagen": e.imagen, "enlace": e.enlace,
        "componentes": [_componente(c) for c in e.componentes.all()],
        "fila_excel": e.fila_excel,
    }


def _equipos_de(usuario):
    return (
        Equipo.objects.filter(experiencia__laboratorio__usuario=usuario)
        .select_related("experiencia")
        .prefetch_related(Prefetch("componentes", queryset=Componente.objects.order_by("orden", "id")))
    )


# --------------------------------------------------------------------------- consultas generales


@requiere_sesion
@require_GET
def inventario(request):
    u = request.usuario
    return ok({
        "asignaturas": [_asignatura(a) for a in Asignatura.objects.filter(usuario=u)],
        "laboratorios": [_laboratorio(l) for l in Laboratorio.objects.filter(usuario=u)],
        "experiencias": [_experiencia(x) for x in Experiencia.objects.filter(laboratorio__usuario=u)],
        "equipos": [_equipo(e) for e in _equipos_de(u)],
    })


@requiere_sesion
@require_GET
def importaciones(request):
    ultimas = Importacion.objects.filter(usuario=request.usuario).select_related("laboratorio")[:10]
    return ok([
        {"id": i.id, "archivo": i.archivo, "laboratorio": i.laboratorio.nombre if i.laboratorio else None,
         "fecha": i.fecha.isoformat(), "resumen": i.resumen}
        for i in ultimas
    ])


@requiere_sesion
@require_POST
def importar(request):
    u = request.usuario
    archivo = request.FILES.get("archivo")
    if not archivo:
        return error("Selecciona un archivo .xlsx.")
    if not archivo.name.lower().endswith(".xlsx"):
        return error("Solo se aceptan archivos .xlsx.")
    if archivo.size > TAMANO_MAXIMO:
        return error("El archivo supera el tamaño máximo de 10 MB.")

    lab_id = (request.POST.get("laboratorio") or "").strip()
    lab_nuevo = (request.POST.get("laboratorio_nuevo") or "").strip()
    if lab_nuevo:
        nombre = lab_nuevo if lab_nuevo.lower().startswith("laboratorio") else f"Laboratorio {lab_nuevo}"
        laboratorio = (
            Laboratorio.objects.filter(usuario=u, nombre__iexact=nombre).first()
            or Laboratorio.objects.create(usuario=u, nombre=nombre[:150])
        )
    elif lab_id.isdigit():
        laboratorio = Laboratorio.objects.filter(usuario=u, id=int(lab_id)).first()
        if not laboratorio:
            return error("El laboratorio elegido no existe.")
    else:
        return error("Elige el laboratorio al que pertenece el archivo.")

    sincronizar = request.POST.get("sincronizar") in ("1", "true", "on")

    try:
        resultado = importar_excel(archivo, laboratorio, sincronizar=sincronizar)
    except ErrorImportacion as exc:
        return error(str(exc))

    laboratorio.hoja = f"{archivo.name} · {resultado['hoja']}"[:255]
    laboratorio.save(update_fields=["hoja"])
    resultado["laboratorio"] = {"id": laboratorio.id, "nombre": laboratorio.nombre}
    resultado["sincronizar"] = sincronizar
    Importacion.objects.create(usuario=u, archivo=archivo.name, laboratorio=laboratorio, resumen=resultado)
    return ok(resultado, status=201)


# --------------------------------------------------------------------------- CRUD


@dataclass
class Recurso:
    consulta: Callable  # usuario -> QuerySet con solo lo que le pertenece
    formulario: type
    serializar: Callable


RECURSOS = {
    "laboratorios": Recurso(
        lambda u: Laboratorio.objects.filter(usuario=u), formularios.FormularioLaboratorio, _laboratorio),
    "asignaturas": Recurso(
        lambda u: Asignatura.objects.filter(usuario=u), formularios.FormularioAsignatura, _asignatura),
    "experiencias": Recurso(
        lambda u: Experiencia.objects.filter(laboratorio__usuario=u), formularios.FormularioExperiencia, _experiencia),
    "equipos": Recurso(_equipos_de, formularios.FormularioEquipo, _equipo),
    "componentes": Recurso(
        lambda u: Componente.objects.filter(equipo__experiencia__laboratorio__usuario=u),
        formularios.FormularioComponente, _componente),
}


def _guardar(request, recurso: Recurso, instancia=None):
    datos = leer_json(request)
    if instancia is not None:
        # Se parte de los valores actuales para que solo cambien los campos enviados.
        base = model_to_dict(instancia, fields=recurso.formulario._meta.fields)
        datos = {**base, **datos}
    formulario = recurso.formulario(data=datos, instance=instancia, usuario=request.usuario)
    if not formulario.is_valid():
        return error("Revisa los campos marcados.", campos=formulario.errors)
    objeto = formulario.save()
    objeto = recurso.consulta(request.usuario).get(pk=objeto.pk)
    return ok(recurso.serializar(objeto), status=200 if instancia else 201)


def coleccion(request, recurso):
    r = RECURSOS[recurso]
    if request.method == "GET":
        return ok([r.serializar(o) for o in r.consulta(request.usuario)])
    if request.method == "POST":
        return _guardar(request, r)
    return error("Método no permitido.", status=405)


def elemento(request, recurso, pk):
    r = RECURSOS[recurso]
    objeto = r.consulta(request.usuario).filter(pk=pk).first()
    if objeto is None:
        return error("No se encontró el registro.", status=404)
    if request.method == "GET":
        return ok(r.serializar(objeto))
    if request.method in ("PATCH", "PUT"):
        return _guardar(request, r, objeto)
    if request.method == "DELETE":
        objeto.delete()
        return ok({"eliminado": True})
    return error("Método no permitido.", status=405)


coleccion = requiere_sesion(coleccion)
elemento = requiere_sesion(elemento)
