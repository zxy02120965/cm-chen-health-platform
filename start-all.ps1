$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$BackendScript = Join-Path $Root 'start-backend.ps1'
$FrontendScript = Join-Path $Root 'start-frontend.ps1'
if (-not (Test-Path $BackendScript) -or -not (Test-Path $FrontendScript)) { throw 'Deployment scripts are incomplete.' }
Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $BackendScript)
Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $FrontendScript)
Write-Host 'Backend and frontend PowerShell windows were started.'
