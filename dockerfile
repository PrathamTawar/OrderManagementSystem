# syntax=docker/dockerfile:1

FROM python:3.14.8-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy dependency files first so this layer is cached when application code changes.
COPY pyproject.toml uv.lock ./

# Use BuildKit cache for uv packages to speed up dependency installation.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --locked \
        --no-install-project \
        --no-dev

# Copy the application source after dependencies.
COPY . .


FROM python:3.14.8-slim-trixie AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app


FROM runtime-base AS runtime-dev

ARG UID=1000
ARG GID=1000

# Create the Django user with the same UID/GID as the host user.
RUN groupadd --gid "$GID" django \
    && useradd \
        --uid "$UID" \
        --gid "$GID" \
        --create-home \
        --shell /bin/bash \
        django

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

# Copy the entrypoint with execute permission.
COPY --chmod=755 entrypoint.sh /entrypoint.sh

USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]


FROM runtime-base AS runtime-prod

# Create a dedicated non-root user for production.
RUN groupadd --system django \
    && useradd \
        --system \
        --gid django \
        --create-home \
        --shell /bin/sh \
        django

COPY --from=builder /opt/venv /opt/venv

# Assign application files to the production user while copying them.
COPY --from=builder --chown=django:django /app /app

# Copy the entrypoint with execute permission.
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Create directories Django may need to write to at runtime.
RUN mkdir -p /app/staticfiles /app/media \
    && chown django:django /app/staticfiles /app/media

USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]