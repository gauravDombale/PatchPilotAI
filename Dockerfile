FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv
WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

FROM python:3.12-slim AS runtime

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src

EXPOSE 8000
CMD ["uvicorn", "resolver.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
