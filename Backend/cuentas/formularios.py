"""Formulario de registro de usuarios (página /registro del frontend)."""

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

Usuario = get_user_model()


def dominio_permitido(email: str) -> bool:
    dominios = settings.DOMINIOS_REGISTRO
    return not dominios or email.rsplit("@", 1)[-1] in dominios


def texto_dominios() -> str:
    """'@a.edu.co' o '@a.edu.co o @b.edu.co'."""
    return " o ".join(f"@{d}" for d in settings.DOMINIOS_REGISTRO)


class FormularioRegistro(forms.Form):
    nombre = forms.CharField(max_length=150, error_messages={"required": "Escribe tu nombre."})
    email = forms.EmailField(
        max_length=150,
        error_messages={"required": "Escribe tu correo.", "invalid": "Escribe un correo válido, por ejemplo nombre@unimagdalena.edu.co."},
    )
    password = forms.CharField(strip=False, error_messages={"required": "Escribe una contraseña."})
    repetir = forms.CharField(strip=False, error_messages={"required": "Repite la contraseña."})

    def clean_nombre(self):
        return " ".join(self.cleaned_data["nombre"].split())

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not dominio_permitido(email):
            raise forms.ValidationError(f"Solo se pueden registrar correos {texto_dominios()}.")
        if Usuario.objects.filter(email__iexact=email).exists() or Usuario.objects.filter(username=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo. Si es tuya, inicia sesión.")
        return email

    def clean(self):
        datos = super().clean()
        password, repetir = datos.get("password"), datos.get("repetir")
        if password and repetir and password != repetir:
            self.add_error("repetir", "Las contraseñas no coinciden.")
        elif password:
            # Se valida con el nombre y el correo para rechazar contraseñas parecidas a ellos.
            usuario = Usuario(username=datos.get("email") or "", email=datos.get("email") or "",
                              first_name=datos.get("nombre") or "")
            try:
                validate_password(password, usuario)
            except forms.ValidationError as exc:
                self.add_error("password", exc)
        return datos

    def save(self):
        d = self.cleaned_data
        return Usuario.objects.create_user(username=d["email"], email=d["email"], password=d["password"],
                                           first_name=d["nombre"])
