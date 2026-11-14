FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY requirements.txt .

RUN  python3 -m pip install --no-cache-dir -r requirements.txt 

COPY . .

EXPOSE 8000

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
