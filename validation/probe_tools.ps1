# Python başlayamasa bile çalışabilen, salt-okuma araç yoklaması. Kurulum yapmaz.
param([string]$Python = 'C:/Users/Urungu/.hz750/Scripts/python.exe')
$ErrorActionPreference = 'Continue'
$record = [ordered]@{ utc=[DateTime]::UtcNow.ToString('o'); status='PROBE_ONLY'; tools=[ordered]@{} }
foreach ($name in @('SU2_CFD', 'ccx', 'gmsh')) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    $record.tools[$name] = if ($command) { $command.Source } else { $null }
}
$record['python_path'] = $Python
$record['python_exists'] = Test-Path -LiteralPath $Python
try {
    $record['python_output'] = (& $Python --version 2>&1 | Out-String).Trim()
    $record['python_exit'] = $LASTEXITCODE
} catch { $record['python_output'] = $_.Exception.Message; $record['python_exit'] = $null }
try {
    $record['wsl_output'] = ((& wsl --list --quiet 2>&1 | Out-String) -replace "`0", '').Trim()
    $record['wsl_exit'] = $LASTEXITCODE
} catch { $record['wsl_output'] = $_.Exception.Message; $record['wsl_exit'] = $null }
$target = Join-Path $PSScriptRoot 'results'
New-Item -ItemType Directory -Path $target -Force | Out-Null
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $target 'machine_probe.json') -Encoding UTF8
$record | ConvertTo-Json -Depth 5
