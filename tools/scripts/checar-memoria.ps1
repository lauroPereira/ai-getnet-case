# Confere se o notebook comporta mais um agente pesado.
# Uso: ./tools/scripts/checar-memoria.ps1
# Adaptado do ampeli-sdd em 2026-11-03. Regra em AGENTS.md ("Ritmo").

$os = Get-CimInstance Win32_OperatingSystem
$livreGB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$commitLivreGB = [math]::Round($os.FreeVirtualMemory / 1MB, 2)
# Paginação automática do Windows começa menor depois de reiniciar e cresce até ~3x a RAM.
# Conta a folga de crescimento, para o veredito não travar só porque a máquina acabou de reiniciar.
$folgaGB = 0
if ((Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile) {
    $alocadoGB = ((Get-CimInstance Win32_PageFileUsage | Measure-Object AllocatedBaseSize -Sum).Sum) / 1KB
    $maxGB = [math]::Min(3 * ($os.TotalVisibleMemorySize / 1MB), 24)
    $folgaGB = [math]::Max(0, [math]::Round($maxGB - $alocadoGB, 2))
}
$commitLivreGB = [math]::Round($commitLivreGB + $folgaGB, 2)

$alertas = @(Get-WinEvent -FilterHashtable @{
    LogName = 'System'
    ProviderName = 'Microsoft-Windows-Resource-Exhaustion-Detector'
    StartTime = (Get-Date).AddMinutes(-30)
} -ErrorAction SilentlyContinue).Count

$pesados = Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='node.exe' or Name='qdrant.exe' or Name='vmmemWSL' or Name='chrome-headless-shell.exe'" |
    ForEach-Object {
        $p = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
        $cmd = if ($_.CommandLine) { $_.CommandLine.Substring(0, [Math]::Min(90, $_.CommandLine.Length)) } else { '' }
        [pscustomobject]@{
            Id = $_.ProcessId
            Nome = $_.Name
            CommitMB = if ($p) { [int]($p.PrivateMemorySize64 / 1MB) } else { 0 }
            Inicio = if ($p -and $p.StartTime) { $p.StartTime.ToString('dd/MM HH:mm') } else { '' }
            Cmd = $cmd
        }
    } | Where-Object { $_.CommitMB -ge 200 } | Sort-Object CommitMB -Descending

$fsmonitor = @(Get-CimInstance Win32_Process -Filter "Name='git.exe'" | Where-Object { $_.CommandLine -like '*fsmonitor--daemon*' }).Count

"RAM livre: $livreGB GB | memória virtual livre: $commitLivreGB GB (inclui $folgaGB GB de crescimento da paginação) | alertas de memória nos últimos 30 min: $alertas | git fsmonitor: $fsmonitor"
if ($pesados) { $pesados | Format-Table -AutoSize | Out-String -Width 200 }

if ($alertas -gt 0 -or $livreGB -lt 0.7 -or $commitLivreGB -lt 6) {
    "VEREDITO: não despachar agente pesado. Encerre processos órfãos ou espere o atual terminar."
    exit 1
}
"VEREDITO: cabe um agente pesado."
exit 0
