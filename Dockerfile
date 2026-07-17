# syntax=docker/dockerfile:1

# Notary Platform — API server image
# Python 3.12-slim base, editable install from pyproject (hatchling).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install build dependencies then the project (editable runtime install).
# The "[dev]" extra is excluded in production to keep the image lean.
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY packages ./packages

RUN pip install --no-cache-dir -e "."

# Run as a non-root user for least privilege.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)" || exit 1

CMD ["uvicorn", "notary_platform.api_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
