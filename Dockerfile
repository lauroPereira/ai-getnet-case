# syntax=docker/dockerfile:1
FROM python:3.13.13-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m venv /venv && /venv/bin/pip install .

FROM python:3.13.13-slim
ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    PROMPTS_DIR=/app/prompts \
    RUNTIME_DIR=/app/runtime
WORKDIR /app
RUN useradd --create-home --uid 10001 app
COPY --from=builder /venv /venv
COPY prompts ./prompts
COPY data/sources ./data/sources
COPY data/snapshots ./data/snapshots
COPY data/knowledge-demo ./data/knowledge-demo
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh && mkdir -p /app/runtime && chown -R app:app /app/runtime
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=40s --retries=6 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"
ENTRYPOINT ["/entrypoint.sh"]
