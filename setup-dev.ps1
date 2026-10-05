param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'webapp'

function Assert-Command($name, $message) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw $message
    }
}

if (-not $SkipBackend) {
    $venvPath = Join-Path $backendDir '.venv'
    if (-not (Test-Path $venvPath)) {
        Write-Host 'Creating backend virtual environment...'
        py -3.12 -m venv $venvPath
        if (-not $?) {
            throw 'Unable to create the Python 3.12 virtual environment in backend/.venv. Install Python 3.12 and try again.'
        }
    }

    $pythonExe = Join-Path $venvPath 'Scripts\python.exe'
    if (-not (Test-Path $pythonExe)) {
        throw "Python virtual environment was not created correctly: $pythonExe"
    }

    Write-Host 'Installing backend requirements...'
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install --require-hashes -r (Join-Path $backendDir 'requirements.lock')
}

if (-not $SkipFrontend) {
    Assert-Command 'npm' 'Node.js and npm are required before installing the frontend dependencies.'

    $frontendEnv = Join-Path $frontendDir '.env'
    if (-not (Test-Path $frontendEnv)) {
        $envExample = Join-Path $frontendDir '.env.example'
        if (Test-Path $envExample) {
            Write-Host 'Creating frontend environment file from .env.example...'
            Copy-Item $envExample $frontendEnv
        }
    }

    Write-Host 'Installing frontend dependencies...'
    Push-Location $frontendDir
    try {
        if (Test-Path (Join-Path $frontendDir 'package-lock.json')) {
            npm ci
        }
        else {
            npm install
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host ''
Write-Host 'Setup complete.'
Write-Host 'Backend: cd backend; .\.venv\Scripts\Activate.ps1; python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000'
Write-Host 'Frontend: cd webapp; npm run dev -- --host 0.0.0.0'
Write-Host 'Optional smoke check: cd webapp; npm run build'
Write-Host ''
Write-Host 'Firebase clinical access setup:'
Write-Host '  1. Configure webapp/.env with the Firebase Web App values.'
Write-Host '  2. Provision organization_id, clinic_id and roles claims using backend/tenant_bootstrap.py.'
Write-Host '  3. Keep FIREBASE_AUTH_REQUIRED=true for clinical API access.'
Write-Host '  4. Read docs/FIREBASE_SETUP.md before using real clinical accounts.'
