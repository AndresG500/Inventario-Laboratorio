from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Permite iniciar sesión con el correo (sin distinguir mayúsculas) en lugar del nombre de usuario."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None
        usuario = get_user_model().objects.filter(email__iexact=email.strip()).first()
        if usuario is None:
            # Se calcula un hash igualmente para que el tiempo de respuesta no revele si el correo existe.
            get_user_model()().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
