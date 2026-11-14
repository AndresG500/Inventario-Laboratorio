from django.contrib import admin

from .models import Asignatura, Componente, Equipo, Experiencia, Importacion, Laboratorio


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "usuario", "orden")
    list_filter = ("usuario",)


@admin.register(Laboratorio)
class LaboratorioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "usuario", "hoja")
    list_filter = ("usuario",)


class EquipoInline(admin.TabularInline):
    model = Equipo
    fields = ("orden", "nombre", "marca", "referencia", "cantidad", "estado")
    extra = 0
    show_change_link = True


@admin.register(Experiencia)
class ExperienciaAdmin(admin.ModelAdmin):
    list_display = ("item", "titulo", "laboratorio", "asignatura", "kits")
    list_filter = ("laboratorio__usuario", "laboratorio", "asignatura")
    search_fields = ("titulo", "temas")
    inlines = [EquipoInline]


class ComponenteInline(admin.TabularInline):
    model = Componente
    extra = 0


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "referencia", "marca", "cantidad", "estado", "experiencia")
    list_filter = ("experiencia__laboratorio__usuario", "estado")
    list_editable = ("estado",)
    search_fields = ("nombre", "referencia", "marca")
    inlines = [ComponenteInline]


@admin.register(Importacion)
class ImportacionAdmin(admin.ModelAdmin):
    list_display = ("archivo", "usuario", "laboratorio", "fecha")
    readonly_fields = ("usuario", "archivo", "laboratorio", "fecha", "resumen")
