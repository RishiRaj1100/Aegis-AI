# =
#  AegisAI -- Build & Deploy Script (Docker Version)
#  Starts Docker services, cleans up environment, and launches the system.
# =

param(
  [switch]$SkipFrontend,
  [switch]$SkipDocker,
  [switch]$Rebuild,
  [switch]$Fast
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# -- Banner ---------------------------------------------------------------------
Write-Host ""
Write-Host "  +=======================================+" -ForegroundColor Cyan
Write-Host "  |      AegisAI  -  Turbo Launcher       |" -ForegroundColor Cyan
Write-Host "  +=======================================+" -ForegroundColor Cyan
Write-Host ""

# =
# STEP 1 -- Cleanup Corrupted Venv (Only if not -Fast)
# =
if (-not $Fast) {
    Write-Host "  [1/4] Cleaning corrupted venv folders ..." -ForegroundColor Cyan
    $venvPath = Join-Path $ProjectRoot ".venv\Lib\site-packages"
    if (Test-Path $venvPath) {
        Get-ChildItem -Path $venvPath -Filter "~*" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "        Done." -ForegroundColor Green
}

# =
# STEP 2 -- Docker Orchestration
# =
if ($SkipDocker) {
    Write-Host "  [2/4] Skipping Docker check (-SkipDocker)." -ForegroundColor DarkGray
} else {
    Write-Host "  [2/4] Orchestrating Docker containers ..." -ForegroundColor Cyan
    $dockerCheck = docker info 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Docker Desktop is not running." -ForegroundColor Red
        exit 1
    }
    
    if ($Rebuild) {
        docker-compose up -d --build
    } else {
        docker-compose up -d
    }
    Write-Host "        Docker services are UP." -ForegroundColor Green
}

# =
# STEP 3 -- Model Registration (Async)
# =
if (-not $SkipDocker) {
    Write-Host "  [3/4] Ensuring Llama Model is ready ..." -ForegroundColor Cyan
    # Run this in background to not block frontend
    Start-Job -ScriptBlock {
        $models = docker exec aegis-ollama ollama list
        if ($models -notmatch "aegis-llama-1b") {
            docker exec aegis-ollama ollama create aegis-llama-1b -f /root/.ollama/models/llama-fine_tuned/Modelfile
        }
    } | Out-Null
    Write-Host "        Model check running in background." -ForegroundColor Green
}

# =
# STEP 4 -- Launch Frontend
# =
if ($SkipFrontend) {
    Write-Host "  [4/4] Skipping Frontend launch." -ForegroundColor DarkGray
} else {
    Write-Host "  [4/4] Starting Frontend (Vite) ..." -ForegroundColor Cyan
    Write-Host "        Opening browser at http://localhost:8080" -ForegroundColor Gray
    Start-Process "http://localhost:8080"
    npm run dev
}

Write-Host ""
Write-Host "  AegisAI is running!" -ForegroundColor Green
Write-Host "  Backend API: http://localhost:8000"
Write-Host "  Frontend:    http://localhost:8080"
Write-Host ""
