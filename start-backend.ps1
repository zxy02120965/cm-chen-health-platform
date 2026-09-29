$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$VenvPython = Join-Path $Backend '.venv\Scripts\python.exe'
if (-not (Test-Path $VenvPython)) { throw 'backend/.venv was not found. Run .\setup.ps1 first.' }

function Import-EnvFile([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        $separator = $trimmed.IndexOf('=')
        if ($separator -lt 1) { continue }
        $name = $trimmed.Substring(0, $separator).Trim()
        $value = $trimmed.Substring($separator + 1).Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) { $value = $value.Substring(1, $value.Length - 2) }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

Import-EnvFile (Join-Path $Root '.env')
if (-not $env:DATABASE_URL -and -not $env:DB_HOST) { $env:DATABASE_URL = 'sqlite:///./cm_chen_dev.db' }
$env:PYTHONPATH = $Backend
Set-Location $Backend
Write-Host 'Backend: http://127.0.0.1:8000 (Swagger: /docs)'
& $VenvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
