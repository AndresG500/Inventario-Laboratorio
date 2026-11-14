# Gestion-Laboratorio

Inventario de laboratorio: frontend en Astro + backend en Django, levantados con Docker Compose.

## Estructura

```
Gestion-Laboratorio/
├── compose.yaml      # Orquesta todos los servicios
├── .env              # Variables de entorno (no se sube a git)
├── Front/            # Proyecto Astro (modo servidor)
└── Backend/          # Proyecto Django
    ├── core/         # Configuración del proyecto
    ├── cuentas/      # Registro, inicio de sesión y sesiones de los usuarios
    ├── inventario/   # API del inventario, CRUD e importador de Excel (ver inventario/LEEME.md)
    └── datos/        # inventario.json para la carga inicial
```

## Servicios

| Servicio | URL | Descripción |
|---|---|---|
| `frontend` | http://localhost:4321 | Astro. Llama a Django en `http://web:8000` dentro de la red de Docker |
| `web` | http://localhost:8000 | Django. API en `/api/`, admin en `/admin/` |
| `postgres` | localhost:5432 | Base de datos |
| `pgadmin` | http://localhost:`PGADMIN_LISTEN_PORT` | Administración de PostgreSQL |

## Primer arranque

Desde la carpeta raíz (`Gestion-Laboratorio/`):

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
# Tu usuario administrador (para entrar a http://localhost:8000/admin/)
docker compose exec web python manage.py createsuperuser
```

## Usuarios

Cada usuario ve y edita solo su propio inventario.

1. Cada persona crea su cuenta en http://localhost:4321/registro con su nombre, correo y contraseña.
2. Solo se aceptan correos de los dominios de la variable `DOMINIOS_REGISTRO` del `.env`
   (separados por comas). Si no existe, se usa `unimagdalena.edu.co`; si existe pero está vacía
   (`DOMINIOS_REGISTRO=`), se acepta cualquier correo. Tras cambiarla: `docker compose up -d web`.
3. Si alguien olvida su contraseña, el administrador le asigna una nueva desde
   http://localhost:8000/admin/ → **Usuarios** → su ficha → enlace de la contraseña. Se cierran sus
   sesiones abiertas y luego la persona puede cambiarla en «Cambiar contraseña».
4. El administrador también puede crear usuarios a mano desde **Añadir usuario**.

Si un usuario entra y no tiene datos, la página de inicio le ofrece cargar un Excel o empezar desde cero.

Para cargar el inventario de ejemplo (PASCO y Vernier) en la cuenta de un usuario:

```bash
docker compose exec web python manage.py cargar_json datos/inventario.json --usuario correo@ejemplo.com
```

