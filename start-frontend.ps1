$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Frontend = Join-Path $Root 'frontend'
if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) { throw 'frontend/node_modules was not found. Run .\setup.ps1 first.' }

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
Set-Location $Frontend
Write-Host 'Frontend: Vite normally uses http://localhost:5173.'
& npm run dev
