# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.12.21 AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-install-project

COPY . .

RUN uv sync --locked --no-install-project


FROM python:3.14.8-slim-trixie AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN groupadd --system django \
    && useradd --system --gid django --create-home django

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN mkdir -p /app/staticfiles /app/media \
    && chown -R django:django /app

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && chown django:django /entrypoint.sh

USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]