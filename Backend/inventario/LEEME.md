# App `inventario` (Django)

## 1. Copiar la app
Copia la carpeta `inventario/` en la raíz de tu proyecto de Django (al lado de `manage.py`).

## 2. Dependencia
Agrega `openpyxl` a tu `requirements.txt` (lee los .xlsx) y reconstruye el contenedor:
```
openpyxl>=3.1
```

## 3. settings.py
```python
INSTALLED_APPS = [
    # ...
    "inventario",
]


# Para subir Excel grandes (por defecto Django acepta 2.5 MB en memoria; más se guarda en disco temporal, está bien así).
```
Revisa que `ALLOWED_HOSTS` incluya el host con el que Astro llama a Django (`localhost`, o el nombre del servicio si Astro también corre en Docker).

## 4. urls.py del proyecto
```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("api/", include("inventario.urls")),
]
```

## 5. Migraciones y carga inicial
```bash
docker compose exec <servicio_django> python manage.py makemigrations inventario
docker compose exec <servicio_django> python manage.py migrate
# Copia inventario.json dentro del contenedor (o a una carpeta montada) y cárgalo:
docker compose exec web python manage.py cargar_json datos/inventario.json --usuario correo@ejemplo.com
```
`cargar_json` se puede repetir sin duplicar datos. Con `--limpiar` borra antes el inventario de ese usuario.

## Endpoints

Todos exigen la cabecera `Authorization: Token <clave>` (la clave se obtiene en `POST /api/auth/login/`)
y solo devuelven o modifican datos del usuario de la sesión.

| Método | URL | Uso |
|---|---|---|
| POST | `/api/auth/login/` | `{email, password}` → `{token, usuario}` |
| POST | `/api/auth/logout/` | Cierra la sesión |
| GET | `/api/auth/yo/` | Datos del usuario |
| POST | `/api/auth/cambiar-contrasena/` | `{actual, nueva, repetir}` |
| GET | `/api/inventario/` | Todo el inventario del usuario |
| GET | `/api/importaciones/` | Últimas 10 importaciones |
| POST | `/api/importar/` | multipart: `archivo`, `laboratorio` (id) o `laboratorio_nuevo` (nombre), `sincronizar` ("1") |
| GET, POST | `/api/<recurso>/` | Listar o crear |
| GET, PATCH, DELETE | `/api/<recurso>/<id>/` | Ver, modificar o eliminar (en cascada) |

`<recurso>` es `laboratorios`, `asignaturas`, `experiencias`, `equipos` o `componentes`. Los errores de
validación vuelven como `{"error": "...", "campos": {"nombre": ["Este campo es obligatorio."]}}`.

## Reglas de la importación
- Las columnas se ubican por el encabezado (ÍTEM, EXPERIENCIA, ASIGNATURA, PRODUCTO, DENOMINACIÓN, CANTIDAD, REFERENCIA, OBSERVACIÓN; opcionales MARCA y ESTADO), no por su posición.
- Experiencia = (laboratorio, ítem). Equipo = nombre del producto dentro de la experiencia.
- Las celdas vacías no borran datos existentes (imagen, estado, enlace, referencias a mano).
- `sincronizar=1` elimina del laboratorio lo que no esté en el archivo.
- Todo corre en una transacción: si algo falla, no se guarda nada.
- Las imágenes, los estados y los componentes se pueden editar desde la página o desde el admin de Django.
