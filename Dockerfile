# syntax=docker/dockerfile:1
# uv installs the application dependencies pinned in uv.lock.
FROM ghcr.io/astral-sh/uv:0.13.7 AS uv

FROM python:3.13.13-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# `--frozen` uses the application dependencies in uv.lock; `--no-editable` installs the package into /venv.
# the `ingest` extra brings the HTML extractor (`rag.collect.extract_text`) the web evidence of `eval` uses (task 91);
# the `otel` extra brings the OTLP span exporter, idle until OTEL_EXPORTER_OTLP_ENDPOINT is set (task 101)
RUN uv sync --frozen --no-editable --extra ingest --extra otel

FROM python:3.13.13-slim AS runtime-base
ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    PROMPTS_DIR=/app/prompts \
    RUNTIME_DIR=/app/runtime \
    BUDGET_RUNTIME_DIR=/app/runtime
WORKDIR /app
RUN useradd --create-home --uid 10001 app
COPY --from=builder /venv /venv
COPY prompts ./prompts
COPY data/sources ./data/sources
COPY data/snapshots ./data/snapshots
COPY data/knowledge-demo ./data/knowledge-demo
COPY data/mock-services ./data/mock-services
COPY data/scenarios ./data/scenarios
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh && mkdir -p /app/runtime && chown -R app:app /app/runtime
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=40s --retries=6 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"
ENTRYPOINT ["/entrypoint.sh"]

# The strict suite inside the image (README, "Run the tests inside the image"): the runtime image plus the `dev` extra
# from the same uv.lock and the repository files. Built on demand with `--target test`, never published; it runs with
# `--network none`, so nothing comes from PyPI or a provider at test time.
FROM runtime-base AS test
USER root
COPY --from=uv /uv /usr/local/bin/uv
# git lists the files the path and link checks read (`git ls-files`); here they are the build context
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY --chown=app:app . /app/repo
WORKDIR /app/repo
ENV UV_PROJECT_ENVIRONMENT=/venv UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_NO_CACHE=1
RUN uv sync --frozen --extra ingest --extra otel --extra dev
USER app
RUN git init -q && git add -A
HEALTHCHECK NONE
# the runtime paths of the API are dropped so the settings resolve from the repository, as on a developer machine
ENTRYPOINT ["env", "-u", "DATA_DIR", "-u", "PROMPTS_DIR", "-u", "RUNTIME_DIR", "-u", "BUDGET_RUNTIME_DIR", \
            "python", "tools/scripts/lint_and_tests.py", "--strict"]
CMD ["--basetemp=/tmp/pytest-image"]

# The published image (default target): the API with the dependencies of uv.lock.
FROM runtime-base AS runtime
