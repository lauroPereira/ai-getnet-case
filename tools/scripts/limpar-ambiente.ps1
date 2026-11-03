# Limpa o que os agentes deixam no notebook depois de uma rodada aprovada pelo QA.
# Adaptado do ampeli-sdd em 2026-11-03. Regra em AGENTS.md ("Ritmo").
# Uso:
#   ./tools/scripts/limpar-ambiente.ps1            # só mostra o que faria (padrão)
#   ./tools/scripts/limpar-ambiente.ps1 -Aplicar   # apaga e encerra
# Só apaga coisa que se reconstrói sozinha. Não toca em data/runtime/ (ledger primário, banco e índice do
# desenvolvimento), .pytest_cache/*-qa-control (ledgers das campanhas, que são evidência), _tmp/, .env,
# volumes do docker-compose, arquivos rastreados pelo Git nem processo que não seja de agente.

param([switch]$Aplicar)

$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$scratchSessoes = Join-Path $env:LOCALAPPDATA 'Temp\claude'
$modo = if ($Aplicar) { 'APLICANDO' } else { 'SIMULAÇÃO (use -Aplicar para executar)' }
"== Limpeza do ambiente — $modo =="

function Tamanho($caminho) {
    try { [math]::Round(((Get-ChildItem -LiteralPath $caminho -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum) / 1MB, 0) } catch { 0 }
}

$antes = (Get-PSDrive C).Free
$total = 0

# 1. Runtimes de QA e testes que se recriam (nunca os controles de campanha)
$cache = Join-Path $raiz '.pytest_cache'
if (Test-Path -LiteralPath $cache) {
    Get-ChildItem -LiteralPath $cache -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like '*-runtime' -and $_.Name -notlike '*-qa-control*' } |
        ForEach-Object {
            $mb = Tamanho $_.FullName; $total += $mb
            "  [runtime de QA] $($_.Name)  $mb MB"
            if ($Aplicar) { Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
        }
}

# 2. Caches de Python e de lint
foreach ($a in '.ruff_cache', 'htmlcov', 'build', 'dist') {
    $p = Join-Path $raiz $a
    if (Test-Path -LiteralPath $p) {
        $mb = Tamanho $p; $total += $mb
        "  [cache] $a  $mb MB"
        if ($Aplicar) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue }
    }
}
$pyc = @(Get-ChildItem -LiteralPath $raiz -Recurse -Directory -Filter '__pycache__' -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike '*\.venv*' })
"  [cache] __pycache__ fora do .venv: $($pyc.Count) pastas"
if ($Aplicar) { $pyc | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue }

# 3. Worktrees de revisão no scratchpad e registros órfãos
$lista = git -C $raiz worktree list --porcelain 2>$null | Where-Object { $_ -like 'worktree *' } | ForEach-Object { $_.Substring(9) }
foreach ($w in ($lista | Select-Object -Skip 1)) {
    $wWin = $w -replace '/', '\'
    if ($wWin -like "$scratchSessoes*") {
        $mb = if (Test-Path -LiteralPath $wWin) { Tamanho $wWin } else { 0 }; $total += $mb
        "  [worktree] $wWin  $mb MB"
        if ($Aplicar) {
            git -C $raiz worktree remove --force $w 2>$null
            if (Test-Path -LiteralPath $wWin) { Remove-Item -LiteralPath $wWin -Recurse -Force -ErrorAction SilentlyContinue }
        }
    } else {
        "  [worktree mantida, fora do scratchpad] $wWin"
    }
}
if ($Aplicar) { git -C $raiz worktree prune 2>$null }

# 4. Scratchpads das sessões do Claude deste projeto
foreach ($s in @(Get-ChildItem -LiteralPath $scratchSessoes -Directory -Filter 'C--workspace-ai-getnet-case*' -ErrorAction SilentlyContinue |
        ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Directory -ErrorAction SilentlyContinue | ForEach-Object { Join-Path $_.FullName 'scratchpad' } })) {
    if (Test-Path -LiteralPath $s) {
        $mb = Tamanho $s; $total += $mb
        "  [scratchpad] $s  $mb MB"
        if ($Aplicar) { Get-ChildItem -LiteralPath $s -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

# 5. Docker: só volumes anônimos sem container, imagens soltas e cache de build. Volumes com nome
# (ai-getnet-case_runtime, ai-getnet-case_qdrant_storage) guardam ledger e coleções e ficam.
$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker -and (docker info 2>$null)) {
    $orfaos = @(docker volume ls -q -f dangling=true -f label=com.docker.volume.anonymous 2>$null | Where-Object { $_ })
    "  [docker] volumes anônimos sem container: $($orfaos.Count)"
    if ($Aplicar -and $orfaos.Count) { docker volume rm $orfaos 2>$null | Out-Null }
    if ($Aplicar) { docker image prune -f 2>$null | Out-Null; docker builder prune -f 2>$null | Out-Null }
    docker system df 2>$null | ForEach-Object { "  [docker df] $_" }
} else {
    "  [docker] desligado; nada a limpar"
}

# 6. Processos de agente esquecidos (só lista; encerrar é decisão do Supervisor)
$suspeitos = Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='node.exe' or Name='chrome-headless-shell.exe'" |
    Where-Object { $_.CommandLine -match 'ai-getnet-case' -and $_.CommandLine -match 'uvicorn|streamlit|merchant-assistant|merchant_assistant|pytest|scratchpad' }
foreach ($p in $suspeitos) {
    "  [processo] $($p.ProcessId) $($p.Name): $($p.CommandLine.Substring(0, [Math]::Min(100, $p.CommandLine.Length)))"
}

$depois = (Get-PSDrive C).Free
"Total identificado: $total MB."
if ($Aplicar) { "Disco livre: {0:N1} GB -> {1:N1} GB" -f ($antes / 1GB), ($depois / 1GB) }
else { "Disco livre agora: {0:N1} GB" -f ($antes / 1GB) }
