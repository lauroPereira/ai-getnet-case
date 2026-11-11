"""v1.0.0 task 106 (spec leitura-acesso-v100, D1 to D4, CA-73): the CI checks uv.lock and publishes the image on version
tags only; dependencies pinned in uv.lock and installed from it by the Dockerfile; compose runs the published image
and builds it when absent; a `test` target runs the strict suite inside the image with no network. Configuration
only: nothing is built or pulled here (the local build is in the task's validation; the publication by tag is checked
by the CI)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tomllib
from fnmatch import fnmatchcase
from pathlib import Path

import pytest
import yaml

from merchant_assistant.config import PROJECT_ROOT

IMAGE = "ghcr.io/lauropereira/ai-getnet-case:${APP_VERSION:-latest}"
APP_SERVICES = ("api", "mocks", "ticketing", "telegram")  # every service run from this repository's Dockerfile


def _pyproject() -> dict:
    return tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _lock() -> dict:
    return tomllib.loads((PROJECT_ROOT / "uv.lock").read_text(encoding="utf-8"))


def _dockerfile() -> str:
    return (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")


def _stages(dockerfile: str) -> list[tuple[str, str]]:
    """(base, name) of each `FROM ... AS name`, in order."""
    return re.findall(r"^FROM\s+(\S+)\s+AS\s+(\S+)\s*$", dockerfile, re.M)


def _stage_body(dockerfile: str, name: str) -> str:
    match = re.search(rf"^FROM\s+\S+\s+AS\s+{re.escape(name)}\s*$(.*?)(?=^FROM\s|\Z)", dockerfile, re.M | re.S)
    assert match, name
    return match.group(1)


def _requirement(text: str, extra: str | None) -> tuple[str, str, tuple[str, ...], str | None]:
    match = re.fullmatch(r"([A-Za-z0-9_.-]+)(?:\[([^\]]+)\])?\s*(.*)", text.strip())
    assert match, text
    name, extras, specifier = match.groups()
    names = tuple(sorted(item.strip() for item in extras.split(","))) if extras else ()
    return name.lower(), specifier.replace(" ", ""), names, extra


# --- D1: the CI publishes the image on tags only ------------------------------------------------------------------


def _workflow() -> dict:
    return yaml.safe_load((PROJECT_ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8"))


def _step(job: dict, uses: str) -> dict:
    matches = [step for step in job["steps"] if step.get("uses", "").startswith(uses)]
    assert len(matches) == 1, uses
    return matches[0]


def test_ci_checks_the_lockfile_before_the_strict_suite_with_the_uv_of_the_image():
    steps = _workflow()["jobs"]["validate"]["steps"]
    runs = [step.get("run", "") for step in steps]
    check = runs.index("uv lock --check")
    strict = next(i for i, run in enumerate(runs) if "tools/scripts/lint_and_tests.py --strict" in run)
    assert check < strict
    pinned = re.search(r'"uv==(\d+\.\d+\.\d+)"', "\n".join(runs[:check]))
    image = re.search(r"^FROM ghcr\.io/astral-sh/uv:(\S+) AS uv$", _dockerfile(), re.M)
    assert pinned and image and pinned.group(1) == image.group(1)


def test_ci_runs_the_strict_suite_on_the_dependencies_of_the_lockfile():
    """The suite in the CI tests the same pinned dependencies the image installs: `uv sync --frozen` with the extras of
    the image's test target, and the strict run uses that environment, not a fresh resolution by pip."""
    job = _workflow()["jobs"]["validate"]
    runs = [step.get("run", "") for step in job["steps"]]
    sync = runs.index("uv sync --frozen --extra ingest --extra otel --extra dev")
    strict = next(i for i, run in enumerate(runs) if "tools/scripts/lint_and_tests.py --strict" in run)
    assert runs.index("uv lock --check") < sync < strict
    assert runs[strict] == ".venv/bin/python tools/scripts/lint_and_tests.py --strict"
    assert not any("pip install -e" in run for run in runs)
    assert job["env"]["UV_PYTHON_DOWNLOADS"] == "never"  # the interpreter of setup-python, not a downloaded one
    test_stage = _stage_body(_dockerfile(), "test")
    assert "RUN uv sync --frozen --extra ingest --extra otel --extra dev" in test_stage


def test_image_job_runs_only_on_version_tags_with_minimal_permissions():
    workflow = _workflow()
    triggers = workflow.get("on", workflow.get(True))  # PyYAML reads the bare key `on` as a boolean
    assert triggers["push"]["tags"] == ["v*"]
    assert workflow["permissions"] == {"contents": "read"}  # every other job keeps read-only access
    jobs = workflow["jobs"]
    assert "permissions" not in jobs["validate"]
    image = jobs["image"]
    assert image["if"] == "github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')"
    assert image["needs"] == "validate"
    assert image["permissions"] == {"contents": "read", "packages": "write"}
    login = _step(image, "docker/login-action@")["with"]
    assert login["registry"] == "ghcr.io" and login["password"] == "${{ secrets.GITHUB_TOKEN }}"
    secrets = set(re.findall(r"secrets\.(\w+)", (PROJECT_ROOT / ".github/workflows/validate.yml").read_text("utf-8")))
    assert secrets == {"GITHUB_TOKEN"}  # no new secret
    meta = _step(image, "docker/metadata-action@")["with"]
    assert meta["flavor"] == "latest=false"  # otherwise metadata-action moves latest on every tag (latest=auto)
    assert meta["tags"].strip().splitlines() == [
        "type=ref,event=tag",
        "type=raw,value=latest,enable=${{ steps.version.outputs.final == 'true' }}",
    ]
    assert "org.opencontainers.image.source=" in meta["labels"]
    assert "org.opencontainers.image.version=${{ github.ref_name }}" in meta["labels"]
    build = _step(image, "docker/build-push-action@")["with"]
    assert build["target"] == "runtime" and build["push"] is True and build["context"] == "."
    assert build["tags"] == "${{ steps.meta.outputs.tags }}" and build["labels"] == "${{ steps.meta.outputs.labels }}"


def _version_step() -> tuple[int, dict, list[dict]]:
    steps = _workflow()["jobs"]["image"]["steps"]
    matches = [i for i, step in enumerate(steps) if step.get("id") == "version"]
    assert len(matches) == 1
    return matches[0], steps[matches[0]], steps


def test_image_job_checks_the_tag_against_the_package_version_before_building():
    index, step, steps = _version_step()
    build = next(i for i, s in enumerate(steps) if s.get("uses", "").startswith("docker/build-push-action@"))
    login = next(i for i, s in enumerate(steps) if s.get("uses", "").startswith("docker/login-action@"))
    assert index < login < build  # nothing is pushed, nor the registry touched, for a tag that is not the version
    assert step["shell"] == "bash" and "pyproject.toml" in step["run"] and "exit 1" in step["run"]


@pytest.mark.parametrize(
    ("version", "tag", "fails", "final"),
    [
        ("1.0.0", "v1.0.0", False, "true"),
        ("1.0.0", "v1.0.1", True, None),
        ("1.0.0", "1.0.0", True, None),
        ("1.0.0rc1", "v1.0.0rc1", False, "false"),
    ],
)
def test_the_version_step_fails_on_a_mismatch_and_moves_latest_only_on_a_final_version(
    tmp_path, version, tag, fails, final
):
    bash = shutil.which("bash")
    if bash is None or "system32" in bash.lower():  # the WSL stub runs Linux, where this interpreter path is absent
        pytest.skip("a native bash is not installed")
    _, step, _ = _version_step()
    (tmp_path / "pyproject.toml").write_text(f'[project]\nname = "x"\nversion = "{version}"\n', encoding="utf-8")
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    script = tmp_path / "step.sh"
    script.write_text(step["run"].replace("python3 ", f'"{Path(sys.executable).as_posix()}" '), encoding="utf-8")
    env = {**os.environ, "GITHUB_REF_NAME": tag, "GITHUB_OUTPUT": output.as_posix()}
    result = subprocess.run([bash, script.as_posix()], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert (result.returncode != 0) is fails, result.stderr
    if not fails:
        assert output.read_text(encoding="utf-8").strip() == f"final={final}"


# --- D2: the lockfile ---------------------------------------------------------------------------------------------


def test_lockfile_records_exactly_the_requirements_of_pyproject():
    """A static copy of what `uv lock --check` verifies in the CI: the root package of uv.lock lists the same
    dependencies, extras and version as pyproject.toml, so a change to one without `uv lock` fails here first."""
    project, lock = _pyproject()["project"], _lock()
    root = next(package for package in lock["package"] if package["name"] == project["name"])
    assert root["version"] == project["version"]
    assert root["source"] == {"editable": "."}
    assert lock["requires-python"] == project["requires-python"]
    expected = {_requirement(text, None) for text in project["dependencies"]}
    for extra, requirements in project["optional-dependencies"].items():
        expected |= {_requirement(text, extra) for text in requirements}
    recorded = set()
    for item in root["metadata"]["requires-dist"]:
        marker = item.get("marker")
        extra = re.fullmatch(r"extra == '([^']+)'", marker).group(1) if marker else None
        recorded.add((item["name"].lower(), item.get("specifier", ""), tuple(sorted(item.get("extras", []))), extra))
    assert recorded == expected
    assert root["metadata"]["provides-extras"] == list(project["optional-dependencies"])


def test_lockfile_pins_every_package_with_hashes_from_pypi():
    packages = [package for package in _lock()["package"] if package["name"] != _pyproject()["project"]["name"]]
    assert len(packages) > 50
    for package in packages:
        assert package["source"] == {"registry": "https://pypi.org/simple"}, package["name"]
        artefacts = package.get("wheels", []) + ([package["sdist"]] if "sdist" in package else [])
        assert artefacts and all(item["hash"].startswith("sha256:") for item in artefacts), package["name"]
    names = {package["name"] for package in packages}
    assert {"fastapi", "langgraph", "trafilatura", "opentelemetry-sdk", "pytest", "ruff"} <= names


# --- D2: the Dockerfile installs from the lockfile ----------------------------------------------------------------


def test_image_installs_the_application_dependencies_from_the_lockfile():
    dockerfile = _dockerfile()
    stages = _stages(dockerfile)
    assert re.fullmatch(r"ghcr\.io/astral-sh/uv:\d+\.\d+\.\d+", stages[0][0]) and stages[0][1] == "uv"
    builder = _stage_body(dockerfile, "builder")
    assert "COPY pyproject.toml uv.lock README.md ./" in builder
    assert "UV_PYTHON_DOWNLOADS=never" in builder  # the venv uses the image's Python, the same one the runtime has
    installs = [line for line in builder.splitlines() if line.startswith("RUN ")]
    assert installs == ["RUN uv sync --frozen --no-editable --extra ingest --extra otel"]
    assert "pip install" not in dockerfile
    runtime = _stage_body(dockerfile, "runtime-base")
    assert "COPY --from=builder /venv /venv" in runtime
    assert "uv " not in runtime and "apt-get" not in runtime  # nothing is installed in the published image itself


def test_the_published_image_is_the_default_target_and_the_test_target_is_built_on_demand():
    dockerfile = _dockerfile()
    stages = _stages(dockerfile)
    assert stages[-1] == ("runtime-base", "runtime")  # `docker build .` and compose `build: .` give the API image
    assert ("runtime-base", "test") in stages
    test = _stage_body(dockerfile, "test")
    assert "RUN uv sync --frozen --extra ingest --extra otel --extra dev" in test  # the same lockfile, plus pytest/Ruff
    assert "COPY --chown=app:app . /app/repo" in test and "HEALTHCHECK NONE" in test
    assert re.search(r"^USER app$", test, re.M)
    assert '"python", "tools/scripts/lint_and_tests.py", "--strict"]' in test
    assert 'CMD ["--basetemp=/tmp/pytest-image"]' in test
    for name in ("DATA_DIR", "PROMPTS_DIR", "RUNTIME_DIR", "BUDGET_RUNTIME_DIR"):  # settings resolve from the repo
        assert f'"-u", "{name}"' in test


def test_build_context_keeps_what_the_test_target_needs_and_drops_secrets_and_runtime_data():
    ignored = {
        line.strip()
        for line in (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert {
        ".env", ".env.*", "**/.env", "**/.env.*", "!.env.example", "**/*.key", "**/*.pem", "**/*.p12", "**/*.secret",
        "discovery", "docs/raw", "docs/relatorios", "docs/apresentacao", "data/runtime", ".git", ".venv", ".codex",
    } <= ignored
    assert not ignored & {"docs", "tests", "tools", "uv.lock"}
    # no word-wide rule that would drop a future module (`private.py`, `credentials.py`, a package `env`) in silence
    assert not ignored & {"**/private*", "**/credential*", "**/credentials*", "env", "**/env"}


def _matches_dockerignore_parts(pattern: tuple[str, ...], path: tuple[str, ...]) -> bool:
    """Match the component globs used here, including Docker's zero-or-more-directory **."""
    if not pattern:
        return not path
    if pattern[0] == "**":
        return _matches_dockerignore_parts(pattern[1:], path) or (
            bool(path) and _matches_dockerignore_parts(pattern, path[1:])
        )
    return bool(path) and fnmatchcase(path[0], pattern[0]) and _matches_dockerignore_parts(pattern[1:], path[1:])


def _in_build_context(relative: Path, patterns: list[str]) -> bool:
    # Docker applies rules in order and excludes descendants of a matched directory too.
    included = True
    for rule in patterns:
        negated = rule.startswith("!")
        parts = tuple(rule.lstrip("!").strip("/").split("/"))
        if any(_matches_dockerignore_parts(parts, relative.parts[:n]) for n in range(1, len(relative.parts) + 1)):
            included = negated
    return included


def test_build_context_filters_nested_worktrees_and_preserves_required_files(tmp_path):
    retained = {
        ".env.example", "Dockerfile", "README.md", "pyproject.toml", "uv.lock", "src/app.py",
        "prompts/router.md", "data/snapshots/source.json", "data/sources/list.json", "data/knowledge-demo/a.json",
        "data/mock-services/a.json", "data/scenarios/a.json", "docker/entrypoint.sh", "tests/test_app.py",
        "tools/scripts/check.py", "docs/specs/spec.md",
        "docs/images/screen.png",  # the README screenshots: the link check of the test target needs them
        ".gitattributes", ".gitignore", ".dockerignore",
        "CHANGELOG.md", "docker-compose.yml", ".github/workflows/validate.yml", "alerts/rules.yml",
        "observability/grafana/dashboard.json",
        # modules whose names only resemble secrets stay in: the rules name secret files, not words
        "src/merchant_assistant/private.py", "src/merchant_assistant/credentials.py",
        "src/merchant_assistant/env/settings.py", "tests/unit/test_private_notes.py",
    }
    # Neutral file names, so each directory rule is the only one that drops its files.
    excluded = {
        ".git/config", "nested/.git", "nested/repo/.git/config", "discovery/notes.md",
        "nested/repo/discovery/notes.md", ".worktrees/repo/src/app.py", "nested/.worktrees/repo/a",
        "worktrees/repo/a", "nested/worktrees/repo/a", "data/runtime/db.sqlite",
        "nested/data/runtime/db.sqlite", "nested/qdrant_storage/a", ".env", "nested/.env",
        "nested/.env.example", "nested/token.pem", "nested/token.key", "nested/token.p12", "nested/token.secret",
        "nested/docs/raw/notes.md", "nested/.venv/notes.md",
        ".claude/notes.md", "nested/.claude/notes.md", ".agents/notes.md", "nested/.agents/notes.md",
        ".codex/notes.md", "nested/.codex/notes.md", ".aws/config", "nested/.aws/config",
        ".ssh/config", "nested/.ssh/config", "_tmp/notes.md", "nested/_tmp/notes.md",
        "Claude outputs/notes.md", "nested/Claude outputs/notes.md",
        ".obsidian/workspace.json", "docs/.obsidian/workspace.json", "application.log", "src/application.log",
        "venv/notes.md", "src/venv/notes.md", "notes/notes.md",
        "src/config/credentials.json", ".git-credentials", "nested/.netrc", "docs/notes/notes.md",
        "docs/relatorios/notes.md", "docs/apresentacao/notes.md", "docs/drafts/notes.md", "data/cache/notes.md",
        "tests/__pycache__/notes.pyc",
        "data/sources/list.bak", "data/sources/cache.tmp", "src/config/example.bak", "application.tmp",
        # local development tooling, outside version control: only the allowlist keeps a root entry in
        "AGENTS.md", "CLAUDE.md", ".agent-template.json", "skills/example/SKILL.md", "evals/cases.json",
    }
    # Exercise recursive exclusions inside an allowed tree, not just at the blocked top level.
    # (`*`, `data/*` and `docs/*` hold at the root only)
    root_only = {
        "notes/notes.md", "docs/drafts/notes.md", "data/cache/notes.md",
        "AGENTS.md", "CLAUDE.md", ".agent-template.json", "skills/example/SKILL.md", "evals/cases.json",
    }
    excluded |= {f"src/{name}" for name in excluded if not name.startswith("src/") and name not in root_only}
    for name in retained | excluded:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic", encoding="utf-8")
    patterns = [
        line.strip() for line in (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    actual = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()
              and _in_build_context(path.relative_to(tmp_path), patterns)}
    assert actual == retained


# --- D3: compose ----------------------------------------------------------------------------------------------------


def test_compose_runs_the_published_image_and_builds_it_when_absent():
    services = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]
    for name in APP_SERVICES:
        service = services[name]
        assert service["image"] == IMAGE, name
        assert service["build"] == ".", name
        assert service["pull_policy"] == "missing", name
    owner = IMAGE.split("/")[1]
    assert owner == owner.lower()  # registry paths are lower case
    assert {name for name, service in services.items() if "build" in service} == set(APP_SERVICES)


def test_env_example_documents_the_image_tag_without_setting_it():
    lines = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "# APP_VERSION=latest" in lines
    assert not any(line.startswith("APP_VERSION=") for line in lines)


# --- D4: README -----------------------------------------------------------------------------------------------------


def test_readme_shows_how_to_run_the_strict_suite_inside_the_image_without_network():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("### Run the tests inside the image", 1)[1].split("\n## ", 1)[0]
    assert "docker build --target test -t ai-getnet-case:test ." in section
    assert "docker run --rm --network none ai-getnet-case:test" in section
    assert "--basetemp=/tmp/" in section
    assert "uv lock --check" in readme and "APP_VERSION" in readme
    assert "docker compose pull --policy always" in readme
