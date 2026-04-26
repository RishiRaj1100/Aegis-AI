# AegisAI - All-in-One Startup Script
# Starts Redis, Backend (FastAPI), and Frontend (Vite)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "Starting AegisAI Full Stack..." -ForegroundColor Cyan

# 1. Start Redis
$RedisExe = "C:\Users\HP\redis\redis-server.exe"
if (Test-Path $RedisExe) {
    Write-Host "[1/3] Starting Redis..." -ForegroundColor Green
    Start-Process -FilePath $RedisExe -ArgumentList "--port 6379" -WindowStyle Minimized
} else {
    Write-Host "[WARN] Redis not found at $RedisExe. Skipping..." -ForegroundColor Yellow
}

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
