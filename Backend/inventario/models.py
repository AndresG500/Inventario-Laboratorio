"""Modelos del inventario de laboratorio.

Cada usuario tiene su propio inventario: los laboratorios y las asignaturas pertenecen a un usuario,
y las experiencias, equipos y componentes cuelgan de ellos.
"""

from django.conf import settings
from django.db import models


class Asignatura(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asignaturas")
    nombre = models.CharField("nombre", max_length=150)
    orden = models.PositiveIntegerField(default=0, help_text="Orden en que se muestra en la página.")

    class Meta:
        ordering = ["orden", "nombre"]
        constraints = [models.UniqueConstraint(fields=["usuario", "nombre"], name="asignatura_unica_por_usuario")]

    def __str__(self):
        return self.nombre


class Laboratorio(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="laboratorios")
    nombre = models.CharField("nombre", max_length=150)
    hoja = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Archivo/hoja de Excel de donde provienen los datos.",
    )

    class Meta:
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(fields=["usuario", "nombre"], name="laboratorio_unico_por_usuario")]

    def __str__(self):
        return self.nombre


class Experiencia(models.Model):
    laboratorio = models.ForeignKey(
        Laboratorio, on_delete=models.CASCADE, related_name="experiencias", verbose_name="laboratorio"
    )
    asignatura = models.ForeignKey(
        Asignatura, on_delete=models.SET_NULL, null=True, blank=True, related_name="experiencias",
        verbose_name="asignatura",
    )
    item = models.PositiveIntegerField("número de ítem")
    titulo = models.CharField("título", max_length=255)
    temas = models.TextField("temas", blank=True, null=True)
    descripcion = models.TextField("descripción", blank=True, null=True)
    observacion = models.TextField("observación", blank=True, null=True)
    kits = models.PositiveIntegerField("kits", blank=True, null=True)

    class Meta:
        ordering = ["laboratorio__nombre", "item"]
        constraints = [
            models.UniqueConstraint(fields=["laboratorio", "item"], name="experiencia_unica_por_laboratorio"),
        ]

    def __str__(self):
        return f"{self.item}. {self.titulo}"


class Equipo(models.Model):
    experiencia = models.ForeignKey(
        Experiencia, on_delete=models.CASCADE, related_name="equipos", verbose_name="experiencia"
    )
    nombre = models.CharField("nombre", max_length=255, blank=True, null=True)
    marca = models.CharField("marca", max_length=120, blank=True, null=True)
    referencia = models.CharField("referencia", max_length=255, blank=True, null=True)
    cantidad = models.PositiveIntegerField("cantidad", blank=True, null=True)
    estado = models.CharField("estado", max_length=50, blank=True, null=True)
    imagen = models.URLField("imagen (enlace)", max_length=500, blank=True, null=True)
    enlace = models.URLField("página del producto", max_length=500, blank=True, null=True)
    orden = models.PositiveIntegerField(default=0, help_text="Posición del equipo dentro de la experiencia.")
    fila_excel = models.PositiveIntegerField(blank=True, null=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["experiencia__laboratorio__nombre", "experiencia__item", "orden", "id"]

    def __str__(self):
        return self.nombre or f"Equipo {self.pk}"


class Componente(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="componentes", verbose_name="equipo")
    nombre = models.CharField("nombre", max_length=255)
    cantidad = models.PositiveIntegerField("cantidad", blank=True, null=True)
    referencia = models.CharField("referencia", max_length=120, blank=True, null=True)
    enlace = models.URLField("página del producto", max_length=500, blank=True, null=True)
    estado = models.CharField("estado", max_length=50, blank=True, null=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["equipo_id", "orden", "id"]

    def __str__(self):
        return self.nombre


class Importacion(models.Model):
    """Registro de cada Excel importado desde la página."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="importaciones")
    archivo = models.CharField(max_length=255)
    laboratorio = models.ForeignKey(Laboratorio, on_delete=models.SET_NULL, null=True, related_name="importaciones")
    fecha = models.DateTimeField(auto_now_add=True)
    resumen = models.JSONField(default=dict)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.archivo} ({self.fecha:%Y-%m-%d %H:%M})"
