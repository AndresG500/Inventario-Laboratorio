"""API de cuentas.

GET  /api/auth/registro/             Dominios de correo permitidos para registrarse.
POST /api/auth/registro/             {nombre, email, password, repetir} -> {token, usuario}
POST /api/auth/login/                {email, password} -> {token, usuario}
POST /api/auth/logout/               Cierra la sesión actual.
GET  /api/auth/yo/                   Datos del usuario de la sesión.
POST /api/auth/cambiar-contrasena/   {actual, nueva, repetir}
"""

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.core.cache import cache
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.api import error, leer_json, ok

from .autenticacion import clave_de, requiere_sesion
from .formularios import FormularioRegistro
from .models import Sesion, hash_clave

MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 15 * 60


def datos_usuario(usuario):
    return {
        "email": usuario.email,
        "nombre": usuario.get_full_name() or usuario.email,
    }


def errores_de(formulario):
    return {campo: [m for e in errores for m in e.messages] for campo, errores in formulario.errors.as_data().items()}


@csrf_exempt
@require_http_methods(["GET", "POST"])
def registro(request):
    if request.method == "GET":
        return ok({"dominios": settings.DOMINIOS_REGISTRO})

    datos = leer_json(request)
    formulario = FormularioRegistro(data={c: str(datos.get(c) or "") for c in ("nombre", "email", "password", "repetir")})
    if not formulario.is_valid():
        return error("Revisa los campos marcados.", campos=errores_de(formulario))
    try:
        usuario = formulario.save()
    except IntegrityError:  # dos registros simultáneos con el mismo correo
        return error("Revisa los campos marcados.", campos={"email": ["Ya existe una cuenta con este correo."]})
    return ok({"token": Sesion.crear(usuario), "usuario": datos_usuario(usuario)}, status=201)


@csrf_exempt
@require_POST
def iniciar_sesion(request):
    datos = leer_json(request)
    email = str(datos.get("email") or "").strip().lower()
    password = str(datos.get("password") or "")
    if not email or not password:
        return error("Escribe tu correo y tu contraseña.")

    clave_intentos = f"intentos-login:{email}"
    intentos = cache.get(clave_intentos, 0)
    if intentos >= MAX_INTENTOS:
        return error("Hubo demasiados intentos fallidos. Espera 15 minutos y vuelve a intentarlo.", status=429)

    usuario = authenticate(request, email=email, password=password)
    if usuario is None:
        cache.set(clave_intentos, intentos + 1, BLOQUEO_SEGUNDOS)
        return error("El correo o la contraseña no son correctos.")

    cache.delete(clave_intentos)
    return ok({"token": Sesion.crear(usuario), "usuario": datos_usuario(usuario)})


@requiere_sesion
@require_POST
def cerrar_sesion(request):
    Sesion.cerrar(clave_de(request))
    return ok({"ok": True})


@requiere_sesion
@require_GET
def yo(request):
    return ok({"usuario": datos_usuario(request.usuario)})


@requiere_sesion
@require_POST
def cambiar_contrasena(request):
    datos = leer_json(request)
    formulario = PasswordChangeForm(request.usuario, data={
        "old_password": datos.get("actual") or "",
        "new_password1": datos.get("nueva") or "",
        "new_password2": datos.get("repetir") or "",
    })
    if not formulario.is_valid():
        # Django deja en new_password2 tanto "no coinciden" como "es muy corta"; la segunda se muestra en "nueva".
        nombres = {"old_password": "actual", "new_password1": "nueva", "new_password2": "repetir"}
        campos = {}
        for campo, errores in formulario.errors.as_data().items():
            for e in errores:
                destino = nombres.get(campo, campo)
                if campo == "new_password2" and e.code != "password_mismatch":
                    destino = "nueva"
                campos.setdefault(destino, []).extend(e.messages)
        return error("Revisa los campos marcados.", campos=campos)

    usuario = formulario.save()
    # Por seguridad se cierran las demás sesiones abiertas con la contraseña anterior.
    Sesion.objects.filter(usuario=usuario).exclude(clave_hash=hash_clave(clave_de(request))).delete()
    return ok({"usuario": datos_usuario(usuario)})
