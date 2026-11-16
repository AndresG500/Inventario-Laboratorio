# Gestion-Laboratorio

Inventario de equipos de laboratorios de Física. Front en **Astro** (modo servidor) + Backend en **Django**,
todo con **Docker Compose**. Todo el código, la interfaz y los mensajes están en **español**.

## Estructura

```
Gestion-Laboratorio/
├── compose.yaml   # postgres, pgadmin, web (Django :8000), frontend (Astro :4321)
├── .env           # credenciales Postgres/pgAdmin y SECRET_KEY (no se sube a git)
├── Front/         # Astro 7 + @astrojs/node, se instala con bun
└── Backend/       # Django 6.1 (proyecto `core`)
    ├── cuentas/      # registro, login por correo, sesiones por token, admin de usuarios
    ├── inventario/   # modelos, API JSON, CRUD genérico, importador de Excel, comando cargar_json
    ├── Laboratorio/  # app ANTIGUA del usuario (registro/login con plantillas). DESCONECTADA de
    │                 # INSTALLED_APPS y urls; la carpeta se conserva. Preguntar antes de borrarla.
    └── datos/inventario.json   # inventario de ejemplo (PASCO y Vernier)
```

## Comandos (desde la raíz Gestion-Laboratorio/)

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py cargar_json datos/inventario.json --usuario correo@ejemplo.com [--limpiar]
docker compose logs -f frontend   # o web
```
- Los volúmenes tienen nombres fijos (`inventario_postgres_data`, `inventario_pgadmin_data`) para conservar la base de datos anterior.
- `./Backend` y `./Front` están montados en los contenedores: Django y Astro recargan solos al editar.
- Los archivos que crea el contenedor de Astro (`Front/.astro/`) pertenecen a root.

## Arquitectura y decisiones

- **El navegador solo habla con Astro.** Astro llama a Django desde el servidor (`DJANGO_API_URL=http://web:8000`;
  por eso `"web"` está en `ALLOWED_HOSTS`).
- **Sesión:** `POST /api/auth/login/` devuelve un token (en BD solo se guarda su sha256, modelo `cuentas.Sesion`,
  dura 7 días). Astro lo guarda en la cookie httpOnly `sesion` y lo envía como `Authorization: Token <clave>`.
  Decorador `cuentas.autenticacion.requiere_sesion` en todas las vistas de la API.
- **Usuarios:** se registran solos en `/registro` (Astro) → `POST /api/auth/registro/` con nombre, correo,
  contraseña y confirmación (`cuentas/formularios.py::FormularioRegistro`; username = correo, nombre en
  `first_name`, no son staff). Al registrarse quedan con la sesión iniciada. Solo se aceptan los dominios de
  `settings.DOMINIOS_REGISTRO` (variable de entorno `DOMINIOS_REGISTRO`, por defecto `unimagdalena.edu.co`;
  vacía = cualquier correo). Ya NO hay contraseñas temporales (se eliminó el modelo `Perfil`, migración
  `cuentas.0002`). Sin SMTP, si alguien olvida la contraseña el admin le pone una nueva en `/admin/` (se
  cierran sus sesiones). Login con `cuentas.backends.EmailBackend`. 5 intentos fallidos → bloqueo de 15 min.
  Contraseñas: solo se exige un mínimo de 6 caracteres (decisión del usuario: se aceptan "123456", solo
  números, etc.; se quitaron los validadores de claves comunes, numéricas y parecidas al correo).
- **Datos por usuario:** `Laboratorio`, `Asignatura` e `Importacion` tienen FK `usuario`; `Experiencia` →
  `Laboratorio`, `Equipo` → `Experiencia`, `Componente` → `Equipo`. Los ID son enteros autoincrementales.
- **CRUD:** `inventario/views.py` tiene un diccionario `RECURSOS` (laboratorios, asignaturas, experiencias,
  equipos, componentes) con rutas genéricas `/api/<recurso>/` y `/api/<recurso>/<id>/` (GET/POST/PATCH/DELETE).
  La validación se hace con los ModelForms de `inventario/formularios.py`, que limitan las opciones al usuario.
  Los errores llegan como `{"error": "...", "campos": {...}}`.
- **Front:**
  - `src/middleware.js` comprueba la sesión, deja `locals.usuario`, `locals.api` (cliente de `lib/api.js`)
    y `locals.inv` (`data/inventario.js`; los ID se comparan como texto).
  - Los formularios usan el patrón POST → redirección, con mensajes de un solo uso
    (`lib/sesion.js` → `avisar`, cookie `aviso`).
  - Antes de borrar algo siempre se pasa por `/eliminar?tipo=&id=&volver=`.
  - Componentes reutilizables: `Campo.astro`, `FormularioExperiencia/Equipo/Componente/Importar.astro`.
- **Diseño:** sobrio institucional, pensado para usuarios de 50–60 años (y de 30). Letra base de 18 px,
  títulos en serif (Georgia), azul oscuro `#15325c`, contraste alto, botones de 48 px siempre con texto
  (sin iconos sueltos), enlaces subrayados, foco amarillo. Solo modo claro. Estilos en
  `src/css/base.css` y `componentes.css`. Mantener este criterio en cualquier pantalla nueva.
- Estados de equipo: OK, EN REPARACION, DAÑADO, DADO DE BAJA (o vacío). Los textos libres que vienen del
  Excel se muestran tal cual.

## Despliegue (preparado el 2026-11-16)

- **Backend → Render (plan gratis, Docker)** con `render.yaml` (Blueprint). Imagen: `Backend/Dockerfile` →
  `iniciar.sh` (collectstatic + migrate + gunicorn en `$PORT`). En local, `compose.yaml` sobrescribe el
  comando con `runserver`. Variables: `SECRET_KEY` (generada), `DATABASE_URL` (Neon), `DOMINIOS_REGISTRO`.
  `RENDER_EXTERNAL_HOSTNAME` (la pone Render) entra en `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.
  `DEBUG` sale de la variable de entorno (apagado si no existe). Estáticos del admin con whitenoise.
  El plan gratis se duerme a los 15 min (~1 min en despertar) y no tiene shell: `createsuperuser` se ejecuta
  desde local con `docker compose run --rm -e DATABASE_URL='<neon>' web python manage.py createsuperuser`.
- **Base de datos → Neon** (Postgres gratis, sin vencimiento). Si existe `DATABASE_URL` se usa en lugar de `POSTGRES_*`.
- **Front → Vercel**, directorio raíz `Front/`, variable `DJANGO_API_URL` = URL de Render. `astro.config.mjs`
  usa `@astrojs/vercel` si existe la variable `VERCEL`; si no, `@astrojs/node`. Límite de Vercel: 4,5 MB
  por petición (afecta a los Excel que se suban).
- Al cambiar dependencias del Front: `docker compose up -d --build --renew-anon-volumes frontend`
  (el volumen anónimo de `node_modules` guarda las viejas). `Front/node_modules` del host es de root:
  `bun add` hay que hacerlo en una copia aparte y traer `package.json` y `bun.lock`.

## Estado al 2026-11-14

Hecho y probado de punta a punta (con curl y capturas en Firefox headless):
- reorganización en Front/ y Backend/;
- login por correo;
- datos separados por usuario;
- CRUD completo;
- pantalla de bienvenida con carga de Excel;
- rediseño;
- registro de usuarios con dominio @unimagdalena.edu.co (2026-11-14, sin contraseña temporal).

Pendiente o por decidir con el usuario:
1. No existe ningún usuario (los antiguos se borraron): hay que ejecutar `createsuperuser`.
2. **Importación flexible (Opción B, elegida por el usuario) — EN PAUSA desde 2026-11-14:** el usuario no
   tiene Excel de otros profesores, así que el importador se deja como está por ahora. Retomar cuando los consiga. cada profesor guarda
   su Excel de forma distinta; el de PASCO/Vernier es solo un ejemplo (del papá del usuario, profesor de la
   U. del Magdalena). Plan: núcleo fijo de campos (nombre, cantidad, estado, referencia, marca) + campo JSON
   `extras` para cualquier otra columna con su nombre original; paso de mapeo al importar (vista previa,
   el usuario asigna cada columna a un campo / "dato adicional" / "ignorar", con sugerencia automática);
   experiencias opcionales (equipo puede colgar directo del laboratorio, para listas planas); guardar el
   mapeo por usuario para reutilizarlo. Pedir Excel de otros profesores para probar. No cargar los datos de
   PASCO/Vernier a nadie (el usuario no lo ve relevante).
3. El proyecto es una demostración para la U. del Magdalena; si no se adopta, lo usará sobre todo ese profesor.
4. Restos de la carpeta antigua `~/Documentos/Proyectos/Inventario` (archivos de root): se borran con
   `sudo rm -rf`.
5. Todo está subido a GitHub en `main` (remoto `origin` = AndresG500/Inventario-Laboratorio), desde 2026-11-14.
6. Ideas no implementadas: recuperar la contraseña por correo (requiere SMTP), modo producción
   (DEBUG, build de Astro, gunicorn).
