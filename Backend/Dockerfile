FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY requirements.txt .

RUN  python3 -m pip install --no-cache-dir -r requirements.txt 

COPY . .

EXPOSE 8000

# Producción: gunicorn (ver iniciar.sh). En local, compose.yaml lo cambia por runserver.
CMD ["sh", "iniciar.sh"]
