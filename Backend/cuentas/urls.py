from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("login/", views.iniciar_sesion, name="login"),
    path("logout/", views.cerrar_sesion, name="logout"),
    path("yo/", views.yo, name="yo"),
    path("cambiar-contrasena/", views.cambiar_contrasena, name="cambiar_contrasena"),
]
