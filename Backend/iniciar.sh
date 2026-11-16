#!/bin/sh
# Arranque en producción (Render). En local, compose.yaml usa runserver en su lugar.
set -e
python manage.py collectstatic --noinput
python manage.py migrate --noinput
# Render indica el puerto en la variable PORT.
exec gunicorn core.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120
