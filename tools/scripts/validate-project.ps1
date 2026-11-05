$ErrorActionPreference = "Stop"

Write-Host "Validando estrutura do projeto..."

$required = @(
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "docs",
    "evals",
    "skills",
    "tools"
)

foreach ($item in $required) {
    if (-not (Test-Path $item)) {
        throw "Item obrigatório ausente: $item"
    }
}

if (Test-Path "ai-dev-template") {
    Write-Warning "Atenção: existe uma subpasta ai-dev-template dentro da raiz."
}

python -I tools/scripts/checar-caminhos-pessoais.py
if ($LASTEXITCODE -ne 0) { throw "Caminho pessoal em arquivo versionado (AGENTS.md, Caminhos pessoais)." }

Write-Host "Estrutura básica válida."