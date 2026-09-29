$ErrorActionPreference = 'Continue'
$Root = $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$script:pass = $true
function Check([string]$Label, [bool]$Ok, [string]$Detail = '') {
    if ($Ok) { Write-Host "$Label`: PASS $Detail" -ForegroundColor Green }
    else { Write-Host "$Label`: FAIL $Detail" -ForegroundColor Red; $script:pass = $false }
}

$python = Get-Command python -ErrorAction SilentlyContinue
$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm -ErrorAction SilentlyContinue
Check 'Python' ([bool]$python)
Check 'Node' ([bool]$node)
Check 'npm' ([bool]$npm)
if ($python) { $pv = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"; Check 'Python version' ([version]$pv -ge [version]'3.11') $pv }

$venvPython = Join-Path $Backend '.venv\Scripts\python.exe'
Check 'Backend virtualenv' (Test-Path $venvPython)
if (Test-Path $venvPython) {
    $env:PYTHONPATH = $Backend
    & $venvPython -c "import fastapi, sqlalchemy, pymysql, app.main" *> $null
    Check 'Backend dependencies' ($LASTEXITCODE -eq 0)
}
Check 'Frontend dependencies' (Test-Path (Join-Path $Frontend 'node_modules'))
Check 'Frontend build' (Test-Path (Join-Path $Frontend 'dist\index.html'))
Check 'Backend app' (Test-Path (Join-Path $Backend 'app\main.py'))
Check 'Knowledge assets' (Test-Path (Join-Path $Backend 'knowledge\zxy_week1'))
$manifestPath = Join-Path $Backend 'knowledge\zxy_week1\manifest.json'
Check 'Manifest' (Test-Path $manifestPath)

if (Test-Path $manifestPath) {
    try {
        $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($role in @('FOOD_SELECTION_METADATA','MDT_STANDARD_COMPONENT_EXECUTION','MDT_INGREDIENT_MASTER','MDT_NUTRITION_SOURCE_PROVENANCE')) {
            $asset = @($manifest.assets | Where-Object { $_.role -eq $role -and $_.active -eq $true }) | Select-Object -First 1
            $assetOk = $null -ne $asset
            if ($assetOk) {
                $assetPath = Join-Path (Join-Path $Backend 'knowledge\zxy_week1') $asset.relative_path
                $assetOk = Test-Path $assetPath
                if ($assetOk -and $asset.sha256) { $assetOk = ((Get-FileHash -LiteralPath $assetPath -Algorithm SHA256).Hash -ieq $asset.sha256) }
            }
            Check "Asset $role" $assetOk
        }
    } catch { Check 'Manifest asset validation' $false $_.Exception.Message }
}
Write-Host 'Legacy V1.7 runtime dependency: NOT REQUIRED' -ForegroundColor Green

$envPath = Join-Path $Root '.env'
if (-not (Test-Path $envPath)) {
    Write-Host 'DATABASE = NOT_CONFIGURED' -ForegroundColor Yellow
} else {
    $envLines = Get-Content -LiteralPath $envPath -Encoding UTF8
    $dbUrl = ($envLines | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | Select-Object -First 1) -replace '^\s*DATABASE_URL\s*=\s*',''
    $dbHost = ($envLines | Where-Object { $_ -match '^\s*DB_HOST\s*=' } | Select-Object -First 1) -replace '^\s*DB_HOST\s*=\s*',''
    if ($dbUrl -match '^mysql' -or ($dbHost -and $dbHost -notmatch '^your-')) {
        Write-Host 'DATABASE = MYSQL_CONFIGURED (read-only connectivity check only)' -ForegroundColor Yellow
    } else { Write-Host 'DATABASE = SQLITE_OR_PLACEHOLDER' -ForegroundColor Yellow }
}
if (-not $script:pass) { exit 1 }
Write-Host 'Environment verification complete.' -ForegroundColor Green
