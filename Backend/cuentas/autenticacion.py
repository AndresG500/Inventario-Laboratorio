"""Decorador para proteger las vistas de la API con la sesión del frontend."""

from functools import wraps

from django.views.decorators.csrf import csrf_exempt

from core.api import error

from .models import Sesion


def clave_de(request) -> str:
    cabecera = request.headers.get("Authorization", "")
    return cabecera[len("Token "):].strip() if cabecera.startswith("Token ") else ""


def requiere_sesion(funcion):
    """Deja en request.usuario al usuario de la sesión o responde 401."""

    @wraps(funcion)
    def envoltura(request, *args, **kwargs):
        usuario = Sesion.usuario_de(clave_de(request))
        if usuario is None:
            return error("Tu sesión terminó. Vuelve a iniciar sesión.", status=401)
        request.usuario = usuario
        return funcion(request, *args, **kwargs)

    # La autenticación va en una cabecera, no en una cookie, así que no aplica CSRF.
    return csrf_exempt(envoltura)
