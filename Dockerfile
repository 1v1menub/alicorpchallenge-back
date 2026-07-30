# syntax=docker/dockerfile:1
FROM python:3.13-slim

# uv (pinned) — copy just the binary from the official image
COPY --from=ghcr.io/astral-sh/uv:0.9.2 /uv /bin/uv

WORKDIR /app

# Install dependencies first for layer caching (needs only the manifests).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the application code.
COPY . .

# Run using the project's virtualenv.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# $PORT is set by hosts like Render; defaults to 8000 locally.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
