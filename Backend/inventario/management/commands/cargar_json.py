"""Carga un inventario.json en el inventario de un usuario.

Uso:
    python manage.py cargar_json datos/inventario.json --usuario correo@ejemplo.com
    python manage.py cargar_json datos/inventario.json --usuario correo@ejemplo.com --limpiar

Se puede ejecutar varias veces: los laboratorios y asignaturas se reconocen por su nombre, las
experiencias por (laboratorio, ítem) y los equipos por su posición dentro de la experiencia.
--limpiar borra antes todo el inventario de ese usuario.
"""

import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventario.models import Asignatura, Componente, Equipo, Experiencia, Laboratorio


def _int(v):
    if v in (None, ""):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class Command(BaseCommand):
    help = "Carga asignaturas, laboratorios, experiencias y equipos desde inventario.json para un usuario."

    def add_arguments(self, parser):
        parser.add_argument("ruta", help="Ruta al archivo inventario.json")
        parser.add_argument("--usuario", required=True, help="Correo del usuario dueño del inventario.")
        parser.add_argument("--limpiar", action="store_true", help="Elimina el inventario del usuario antes de cargar.")

    @transaction.atomic
    def handle(self, *args, ruta, usuario, limpiar, **opciones):
        archivo = Path(ruta)
        if not archivo.exists():
            raise CommandError(f"No existe el archivo {archivo}")
        dueno = get_user_model().objects.filter(email__iexact=usuario.strip()).first()
        if dueno is None:
            raise CommandError(f"No hay ningún usuario con el correo {usuario}. Créalo primero en /admin/.")
        datos = json.loads(archivo.read_text(encoding="utf-8"))

        if limpiar:
            Laboratorio.objects.filter(usuario=dueno).delete()  # en cascada: experiencias, equipos y componentes
            Asignatura.objects.filter(usuario=dueno).delete()

        asignaturas = {}
        for i, a in enumerate(datos.get("asignaturas", []), start=1):
            asignaturas[a["id"]], _ = Asignatura.objects.update_or_create(
                usuario=dueno, nombre=a["nombre"], defaults={"orden": i})

        laboratorios = {}
        for l in datos.get("laboratorios", []):
            laboratorios[l["id"]], _ = Laboratorio.objects.update_or_create(
                usuario=dueno, nombre=l["nombre"], defaults={"hoja": l.get("hoja") or ""})

        experiencias = {}
        for x in datos.get("experiencias", []):
            experiencias[x["id"]], _ = Experiencia.objects.update_or_create(
                laboratorio=laboratorios[x["laboratorio"]],
                item=_int(x.get("item")) or 0,
                defaults={
                    "asignatura": asignaturas.get(x.get("asignatura")),
                    "titulo": x.get("titulo") or "",
                    "temas": x.get("temas"),
                    "descripcion": x.get("descripcion"),
                    "observacion": x.get("observacion"),
                    "kits": _int(x.get("kits")),
                },
            )

        orden_por_exp = {}
        n_equipos = n_componentes = 0
        for e in datos.get("equipos", []):
            orden = orden_por_exp[e["experiencia"]] = orden_por_exp.get(e["experiencia"], 0) + 1
            exp = experiencias[e["experiencia"]]
            valores = {
                "nombre": e.get("nombre"),
                "marca": e.get("marca"),
                "referencia": e.get("referencia"),
                "cantidad": _int(e.get("cantidad")),
                "estado": e.get("estado"),
                "imagen": e.get("imagen"),
                "enlace": e.get("enlace"),
                "fila_excel": _int(e.get("fila_excel")),
            }
            equipo = Equipo.objects.filter(experiencia=exp, orden=orden).first()
            if equipo is None:
                equipo = Equipo(experiencia=exp, orden=orden)
            for campo, valor in valores.items():
                setattr(equipo, campo, valor)
            equipo.save()
            n_equipos += 1

            equipo.componentes.all().delete()
            for i, c in enumerate(e.get("componentes") or [], start=1):
                Componente.objects.create(
                    equipo=equipo, orden=i, nombre=c.get("nombre") or "",
                    cantidad=_int(c.get("cantidad")), referencia=c.get("referencia"),
                    enlace=c.get("enlace"), estado=c.get("estado"),
                )
                n_componentes += 1

        self.stdout.write(self.style.SUCCESS(
            f"Cargado para {dueno.email}: {len(asignaturas)} asignaturas, {len(laboratorios)} laboratorios, "
            f"{len(experiencias)} experiencias, {n_equipos} equipos, {n_componentes} componentes."
        ))
