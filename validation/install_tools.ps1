param(
    [string]$Destination = 'C:/hz750tools',
    [string]$Python = 'C:/Users/Urungu/.hz750/Scripts/python.exe'
)
# Host üzerinde açıkça çalıştırılır. PATH/registry/sistem kurulumunu değiştirmez.
$ErrorActionPreference = 'Stop'
$lock = Get-Content -LiteralPath "$PSScriptRoot/tools.lock.json" -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$installRecords = @()
function Fetch-Archive([string]$Url, [string]$Name) {
    $archive = Join-Path $Destination "$Name.zip"
    if (Test-Path -LiteralPath $archive) { throw "Mevcut arşiv üstüne yazılmıyor: $archive" }
    Invoke-WebRequest -Uri $Url -OutFile $archive -UseBasicParsing
    $script:installRecords += [pscustomobject]@{name=$Name; url=$Url; sha256=(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash}
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $Destination $Name)
}
$release = Invoke-RestMethod -Uri $lock.SU2.assets_api
$assets = @($release.assets | Where-Object {
    $_.name -match '(?i)(win64|windows64|win.*64)' -and $_.name -match '\.zip$' -and $_.name -notmatch '(?i)(mpi|(^|[_-])ad([_-]|\.))'
})
if ($assets.Count -ne 1) { throw "Sabit SU2 sürümünde tek serial Windows zip seçilemedi. Resmi release sayfasını inceleyin: $($lock.SU2.release)" }
Fetch-Archive $assets[0].browser_download_url 'SU2'
Fetch-Archive $lock.CalculiX.archive 'CalculiX'
& $Python -m pip install 'gmsh==4.15.2'
if ($LASTEXITCODE -ne 0) { throw 'gmsh kurulamadı' }
$installRecords | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $Destination 'installation.json') -Encoding UTF8
Get-ChildItem -LiteralPath $Destination -Recurse -Filter '*ccx*.exe' | Select-Object FullName
Get-ChildItem -LiteralPath $Destination -Recurse -Filter 'SU2_CFD.exe' | Select-Object FullName
Write-Output 'Tam executable yollarını validation/tools.local.json içine yazın; PATH değişmedi.'
