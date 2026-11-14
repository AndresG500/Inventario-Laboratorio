from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("inventario/", views.inventario, name="inventario"),
    path("importaciones/", views.importaciones, name="importaciones"),
    path("importar/", views.importar, name="importar"),
]

for recurso in views.RECURSOS:
    urlpatterns += [
        path(f"{recurso}/", views.coleccion, {"recurso": recurso}, name=recurso),
        path(f"{recurso}/<int:pk>/", views.elemento, {"recurso": recurso}, name=f"{recurso}-detalle"),
    ]
