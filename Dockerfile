# Reproducible runtime image for the CLI and library.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Install locked runtime dependencies before copying source so dependency
# layers remain reusable when application code changes.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-dev --no-install-project

COPY geoparser ./geoparser
RUN uv sync --locked --no-dev

CMD ["python", "-m", "geoparser", "--help"]
