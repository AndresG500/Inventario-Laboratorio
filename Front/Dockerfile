FROM oven/bun:1-slim

WORKDIR /app

# Dependencias primero para aprovechar la caché de Docker
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .

EXPOSE 4321

# --host 0.0.0.0 para que el servidor sea accesible desde fuera del contenedor
CMD ["bun", "run", "dev", "--host", "0.0.0.0", "--port", "4321"]
