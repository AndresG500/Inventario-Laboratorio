"""Respuestas JSON comunes para la API que consume el frontend de Astro."""

import json

from django.http import JsonResponse

_JSON = {"ensure_ascii": False}


def ok(datos, status=200):
    return JsonResponse(datos, status=status, safe=False, json_dumps_params=_JSON)


def error(mensaje, status=400, campos=None):
    """Error para mostrar al usuario. `campos` son los errores de cada campo de un formulario."""
    cuerpo = {"error": mensaje}
    if campos:
        cuerpo["campos"] = {campo: [str(m) for m in mensajes] for campo, mensajes in campos.items()}
    return JsonResponse(cuerpo, status=status, json_dumps_params=_JSON)


def leer_json(request) -> dict:
    try:
        datos = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        return {}
    return datos if isinstance(datos, dict) else {}
