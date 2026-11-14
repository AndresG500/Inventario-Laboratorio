"""Validación de los datos que llegan del CRUD del frontend.

Cada formulario recibe el usuario de la sesión y solo le deja elegir laboratorios, experiencias o
equipos que le pertenecen.
"""

from django import forms
from django.db.models import Max

from .models import Asignatura, Componente, Equipo, Experiencia, Laboratorio


def _siguiente(consulta, campo):
    return (consulta.aggregate(m=Max(campo))["m"] or 0) + 1


class FormularioDeUsuario(forms.ModelForm):
    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario


class FormularioLaboratorio(FormularioDeUsuario):
    class Meta:
        model = Laboratorio
        fields = ["nombre"]

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        repetido = Laboratorio.objects.filter(usuario=self.usuario, nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError("Ya tienes un laboratorio con este nombre.")
        return nombre

    def save(self, commit=True):
        self.instance.usuario = self.usuario
        return super().save(commit)


class FormularioAsignatura(FormularioDeUsuario):
    class Meta:
        model = Asignatura
        fields = ["nombre"]

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        repetido = Asignatura.objects.filter(usuario=self.usuario, nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError("Ya tienes una asignatura con este nombre.")
        return nombre

    def save(self, commit=True):
        self.instance.usuario = self.usuario
        if self.instance.pk is None:
            self.instance.orden = _siguiente(Asignatura.objects.filter(usuario=self.usuario), "orden")
        return super().save(commit)


def obtener_o_crear_asignatura(usuario, nombre: str) -> Asignatura:
    nombre = nombre.strip()
    existente = Asignatura.objects.filter(usuario=usuario, nombre__iexact=nombre).first()
    if existente:
        return existente
    orden = _siguiente(Asignatura.objects.filter(usuario=usuario), "orden")
    return Asignatura.objects.create(usuario=usuario, nombre=nombre, orden=orden)


class FormularioExperiencia(FormularioDeUsuario):
    asignatura_nueva = forms.CharField(
        label="nueva asignatura", max_length=150, required=False,
        help_text="Escríbela solo si no está en la lista.",
    )

    class Meta:
        model = Experiencia
        fields = ["laboratorio", "asignatura", "item", "titulo", "temas", "descripcion", "observacion", "kits"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["laboratorio"].queryset = Laboratorio.objects.filter(usuario=self.usuario)
        self.fields["asignatura"].queryset = Asignatura.objects.filter(usuario=self.usuario)
        self.fields["item"].required = False

    def clean(self):
        datos = super().clean()
        laboratorio = datos.get("laboratorio")
        if laboratorio is None:
            return datos
        if datos.get("item") is None and "item" not in self.errors:
            datos["item"] = _siguiente(Experiencia.objects.filter(laboratorio=laboratorio), "item")
        item = datos.get("item")
        if item is not None:
            repetida = Experiencia.objects.filter(laboratorio=laboratorio, item=item).exclude(pk=self.instance.pk)
            if repetida.exists():
                self.add_error("item", f"Ya hay una experiencia con el número {item} en {laboratorio.nombre}.")
        return datos

    def save(self, commit=True):
        nueva = (self.cleaned_data.get("asignatura_nueva") or "").strip()
        if nueva:
            self.instance.asignatura = obtener_o_crear_asignatura(self.usuario, nueva)
        return super().save(commit)


class FormularioEquipo(FormularioDeUsuario):
    class Meta:
        model = Equipo
        fields = ["experiencia", "nombre", "marca", "referencia", "cantidad", "estado", "imagen", "enlace"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["experiencia"].queryset = Experiencia.objects.filter(laboratorio__usuario=self.usuario)
        self.fields["nombre"].required = True

    def save(self, commit=True):
        if self.instance.pk is None:
            self.instance.orden = _siguiente(Equipo.objects.filter(experiencia=self.instance.experiencia), "orden")
        return super().save(commit)


class FormularioComponente(FormularioDeUsuario):
    class Meta:
        model = Componente
        fields = ["equipo", "nombre", "cantidad", "referencia", "enlace", "estado"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipo"].queryset = Equipo.objects.filter(experiencia__laboratorio__usuario=self.usuario)

    def save(self, commit=True):
        if self.instance.pk is None:
            self.instance.orden = _siguiente(Componente.objects.filter(equipo=self.instance.equipo), "orden")
        return super().save(commit)
