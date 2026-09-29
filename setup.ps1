$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'

function Require-Command([string]$Name, [string]$Hint) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) { throw "$Name was not found. $Hint" }
    return $command.Source
}

$Python = Require-Command 'python' 'Install Python 3.11 or newer and retry.'
$Node = Require-Command 'node' 'Install Node.js 20 LTS or newer and retry.'
$Npm = Require-Command 'npm' 'Install npm with Node.js and retry.'
$pyVersion = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pyVersion -lt [version]'3.11') { throw "Python version $pyVersion is too old; Python 3.11 or newer is required." }
Write-Host "Python: $pyVersion"
Write-Host "Node: $(& $Node --version)"
Write-Host "npm: $(& $Npm --version)"

$Venv = Join-Path $Backend '.venv'
if (-not (Test-Path (Join-Path $Venv 'Scripts\python.exe'))) {
    Write-Host 'Creating backend/.venv ...'
    & $Python -m venv $Venv
}
$VenvPython = Join-Path $Venv 'Scripts\python.exe'
Write-Host 'Installing backend dependencies ...'
& $VenvPython -m pip install -r (Join-Path $Backend 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }

Push-Location $Frontend
try {
    Write-Host 'Installing locked frontend dependencies (npm ci) ...'
    & $Npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    Write-Host 'Building frontend ...'
    & $Npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
}
finally { Pop-Location }

if (-not (Test-Path (Join-Path $Root '.env'))) {
    Write-Warning 'No .env found. Copy env.example to .env and fill database settings if needed; this script never writes real passwords.'
}
Write-Host 'Setup complete. Run .\verify-installation.ps1.'
