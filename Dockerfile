# Stage 1 — build the React bundle
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Override outDir: in this stage there is no ../backend to write into.
RUN npm run build -- --outDir dist --emptyOutDir

# Stage 2 — Python runtime serving API + static bundle
FROM python:3.12-slim AS runtime

# Set by the release pipeline (--build-arg DOSSIER_VERSION=<tag>) so the running
# container can report which build it is. Local/dev builds keep saying "dev".
ARG DOSSIER_VERSION=dev

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./
COPY --from=web /web/dist ./app/static

ENV DOSSIER_DATA_DIR=/data
ENV DOSSIER_VERSION=$DOSSIER_VERSION
VOLUME /data
EXPOSE 8080

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
