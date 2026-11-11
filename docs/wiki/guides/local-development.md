# Local development

Outside Docker, one `uv` command installs the environment from `uv.lock`, the index is built in an embedded
Qdrant, and a message runs in process with its trace. This guide has the commands, the uv version and the
lockfile upkeep; the Docker start is in the [README](../../../README.md#run-it).

## Environment and first run

Use uv 0.13.7, the version used by the Dockerfile, for the commands below and for maintaining `uv.lock`.

```bash
uv sync --frozen --extra ingest --extra dev
source .venv/bin/activate                                    # PowerShell: .\.venv\Scripts\Activate.ps1
merchant-assistant bootstrap                                  # seed data + build the index (embedded Qdrant)
uvicorn --factory merchant_assistant.main:create_application --reload
merchant-assistant ask "Qual a cotação do euro hoje?" --trace  # one message, in process, with its trace
```

## Lockfile

After changing the dependencies or the version in `pyproject.toml`, regenerate `uv.lock` with `uv lock` and include
it with the change. `uv lock --check` verifies that the lockfile is current.

## Related

- [Test and evaluation commands](evaluation-commands.md): tests, offline and paid evaluation, judge calibration
  and retrieval measurement, all from this environment.
- [Run the tests inside the image](../../../README.md#run-the-tests-inside-the-image): the strict suite with no
  network.
- [Operations](../../../README.md#operations): the embedded vector store with one process, and the seed dates.
- [Configuration reference](configuration.md): every environment variable with its default.
