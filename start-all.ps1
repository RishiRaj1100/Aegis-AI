# AegisAI - All-in-One Startup Script
# Starts Redis, Backend (FastAPI), and Frontend (Vite)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "Starting AegisAI Full Stack..." -ForegroundColor Cyan

# 1. Start Dependencies (MongoDB & Redis) via Docker Compose
Write-Host "[1/3] Starting Dependencies (MongoDB & Redis)..." -ForegroundColor Green
docker-compose up -d

# Wait for MongoDB to be ready (brief pause)
Write-Host "Waiting for services to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# 2. Start Backend (FastAPI)
Write-Host "[2/3] Starting Backend (FastAPI)..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", ".\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Normal

# 3. Start Frontend (Vite)
Write-Host "[3/3] Starting Frontend (Vite)..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "Services are launching in separate windows." -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000"
Write-Host "Frontend: http://localhost:8080"
Write-Host "Docs:     http://localhost:8000/docs"
Write-Host ""
