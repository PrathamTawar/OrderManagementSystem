# syntax=docker/dockerfile:1

FROM python:3.14.8-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy dependency files first to maximize Docker layer caching.
COPY pyproject.toml uv.lock ./

# Cache uv packages between builds.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --locked \
        --no-install-project \
        --no-dev

# Copy application source after dependencies.
COPY . .


FROM python:3.14.8-slim-trixie AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app


FROM runtime-base AS runtime-dev

ARG UID=1000
ARG GID=1000

# Copy the environment and source code for development.
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

# The script is required to use LF line endings in the repository.
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Use the host user's numeric UID/GID for bind-mounted files.
USER ${UID}:${GID}

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

# Keep the virtual environment root-owned and copy application files
# directly with the correct ownership.
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=django:django /app /app

# The script is required to use LF line endings in the repository.
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Only directories that need runtime write access are writable by Django.
RUN mkdir -p /app/staticfiles /app/media \
    && chown django:django /app/staticfiles /app/media

USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]