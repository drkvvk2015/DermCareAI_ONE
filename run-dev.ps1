$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'webapp'
$backendPython = Join-Path $backendDir '.venv\Scripts\python.exe'
$viteCommand = Join-Path $frontendDir 'node_modules\.bin\vite.cmd'

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'Node.js and npm are required. Install Node.js, then run this script again.'
}

$backendReady = Test-Path $backendPython
if ($backendReady) {
    & $backendPython -c 'import uvicorn' *> $null
    $backendReady = $LASTEXITCODE -eq 0
}

if (-not $backendReady -or -not (Test-Path $viteCommand)) {
    Write-Host 'Installing missing app dependencies...'
    & (Join-Path $repoRoot 'setup-dev.ps1')
}

if (-not (Test-Path $backendPython) -or -not (Test-Path $viteCommand)) {
    throw 'App setup did not complete successfully. Check the setup output and try again.'
}

$backendCommand = '& .\.venv\Scripts\python.exe -m uvicorn app:app --reload --host 127.0.0.1 --port 8000'
$frontendCommand = 'npm run dev -- --host 127.0.0.1'

Start-Process -FilePath 'powershell.exe' -WorkingDirectory $backendDir -ArgumentList "-NoExit -Command `"$backendCommand`""
Start-Process -FilePath 'powershell.exe' -WorkingDirectory $frontendDir -ArgumentList "-NoExit -Command `"$frontendCommand`""

Write-Host ''
Write-Host 'DermCareAI is starting.'
Write-Host 'Dashboard: http://localhost:5173'
Write-Host 'API docs:  http://localhost:8000/docs'