"""Usuarios en /admin/.

Los usuarios normalmente se registran solos desde /registro. El administrador puede:
- crear un usuario a mano (correo, nombre y contraseña);
- asignarle una contraseña nueva si la olvidó (no hay recuperación por correo). Al hacerlo se
  cierran sus sesiones abiertas; el usuario puede cambiarla luego desde "Cambiar contraseña".
"""

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.password_validation import validate_password

from .models import Sesion

Usuario = get_user_model()


class FormularioNuevoUsuario(forms.ModelForm):
    contrasena1 = forms.CharField(
        label="Contraseña", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    contrasena2 = forms.CharField(
        label="Repite la contraseña", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Usuario
        fields = ("email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["email"].help_text = "El usuario iniciará sesión con este correo."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists() or Usuario.objects.filter(username=email).exists():
            raise forms.ValidationError("Ya existe un usuario con este correo.")
        return email

    def clean(self):
        datos = super().clean()
        c1, c2 = datos.get("contrasena1"), datos.get("contrasena2")
        if c1 and c2 and c1 != c2:
            self.add_error("contrasena2", "Las contraseñas no coinciden.")
        elif c1:
            usuario = Usuario(email=datos.get("email"), first_name=datos.get("first_name", ""))
            try:
                validate_password(c1, usuario)
            except forms.ValidationError as exc:
                self.add_error("contrasena1", exc)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.username = usuario.email
        usuario.is_staff = False
        usuario.is_superuser = False
        usuario.set_password(self.cleaned_data["contrasena1"])
        if commit:
            usuario.save()
        return usuario


admin.site.unregister(Usuario)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    add_form = FormularioNuevoUsuario
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "contrasena1", "contrasena2")}),
    )
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff", "date_joined", "last_login")
    search_fields = ("email", "first_name", "last_name", "username")
    ordering = ("email",)

    def user_change_password(self, request, id, form_url=""):
        """Al asignarle una contraseña nueva se cierran sus sesiones abiertas."""
        respuesta = super().user_change_password(request, id, form_url)
        if request.method == "POST" and respuesta.status_code == 302:
            Sesion.objects.filter(usuario_id=id).delete()
        return respuesta
