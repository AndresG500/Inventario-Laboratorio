"""Sesiones de los usuarios del frontend.

Los usuarios se registran solos desde la página /registro del frontend (ver formularios.py).

El frontend de Astro no usa la cookie de sesión de Django: al iniciar sesión recibe una clave
(Sesion) que guarda en una cookie propia y envía en cada petición como "Authorization: Token <clave>".
En la base de datos solo se guarda el hash de la clave.
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

DURACION_SESION = timedelta(days=7)


def hash_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode()).hexdigest()


class Sesion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sesiones")
    clave_hash = models.CharField(max_length=64, unique=True)
    creada = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField()

    class Meta:
        verbose_name = "sesión"
        verbose_name_plural = "sesiones"

    @classmethod
    def crear(cls, usuario) -> str:
        """Abre una sesión y devuelve la clave en claro (solo se conoce en este momento)."""
        cls.objects.filter(expira__lte=timezone.now()).delete()
        clave = secrets.token_urlsafe(32)
        cls.objects.create(usuario=usuario, clave_hash=hash_clave(clave), expira=timezone.now() + DURACION_SESION)
        return clave

    @classmethod
    def usuario_de(cls, clave: str):
        if not clave:
            return None
        sesion = (
            cls.objects.select_related("usuario")
            .filter(clave_hash=hash_clave(clave), expira__gt=timezone.now())
            .first()
        )
        return sesion.usuario if sesion and sesion.usuario.is_active else None

    @classmethod
    def cerrar(cls, clave: str):
        cls.objects.filter(clave_hash=hash_clave(clave)).delete()
