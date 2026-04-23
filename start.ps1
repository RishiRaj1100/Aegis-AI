# =
#  AegisAI -- Build & Deploy Script
#  Installs dependencies, validates environment, runs tests, starts services.
#
#  Usage:
#    .\start.ps1                     # build + start (dev, hot-reload)
#    .\start.ps1 -SkipBuild          # skip pip install (already up-to-date)
#    .\start.ps1 -SkipTests          # skip pytest before starting
#    .\start.ps1 -Prod               # production mode (no reload, workers=4)
#    .\start.ps1 -Port 9000          # custom port
#    .\start.ps1 -Prod -Workers 8    # production with explicit worker count
# =

param(
  [int]$Port = 8000,
  [int]$Workers = 4,
  [switch]$SkipBuild,
  [switch]$SkipTests,
  [switch]$Prod,
  # Legacy alias kept for backwards-compatibility
  [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RedisExe = "C:\Users\HP\redis\redis-server.exe"
$RedisPort = 6379
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $PythonExe = $VenvPython
}
else {
  $PythonExe = "python"
}

# Production mode can be set via -Prod or the legacy -NoReload flag
$IsProd = $Prod -or $NoReload

Set-Location $ProjectRoot

# -- Banner ---------------------------------------------------------------------

Write-Host ""
Write-Host "  +=======================================+" -ForegroundColor Cyan
Write-Host "  |      AegisAI  -  Build & Deploy       |" -ForegroundColor Cyan
Write-Host "  +=======================================+" -ForegroundColor Cyan
Write-Host "  Mode : $(if ($IsProd) { 'PRODUCTION' } else { 'DEVELOPMENT' })" -ForegroundColor $(if ($IsProd) { 'Yellow' } else { 'Green' })
Write-Host "  Port : $Port"
Write-Host ""

# =
# STEP 1 -- Python version check
# =

Write-Host "  [1/5] Checking Python version ..." -ForegroundColor Cyan
try {
  $pyVer = & $PythonExe --version 2>&1
  Write-Host "        $pyVer" -ForegroundColor Green
  # Require Python 3.10+
  $verNum = ($pyVer -replace 'Python ', '').Trim()
  $major, $minor = $verNum.Split('.')[0..1] | ForEach-Object { [int]$_ }
  if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
    Write-Host "  [ERROR] Python 3.10+ is required (found $verNum)." -ForegroundColor Red
    exit 1
  }
}
catch {
  Write-Host "  [ERROR] 'python' not found on PATH. Install Python 3.10+ and retry." -ForegroundColor Red
  exit 1
}

# =
# STEP 2 -- Install / upgrade Python dependencies
# =

if ($SkipBuild) {
  Write-Host "  [2/5] Skipping dependency install (-SkipBuild)." -ForegroundColor DarkGray
}
else {
  Write-Host "  [2/5] Installing dependencies from requirements.txt ..." -ForegroundColor Cyan
  if (-not (Test-Path "$ProjectRoot\requirements.txt")) {
    Write-Host "  [ERROR] requirements.txt not found in $ProjectRoot" -ForegroundColor Red
    exit 1
  }
  & $PythonExe -m pip install --upgrade pip --quiet
  & $PythonExe -m pip install -r "$ProjectRoot\requirements.txt" --quiet
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] pip install failed. Check requirements.txt and your network." -ForegroundColor Red
    exit 1
  }
  Write-Host "        Dependencies installed successfully." -ForegroundColor Green
}

# =
# STEP 3 -- Environment (.env) validation
# =

Write-Host "  [3/5] Validating environment ..." -ForegroundColor Cyan

if (-not (Test-Path "$ProjectRoot\.env")) {
  # Auto-create from .env.example if it exists
  if (Test-Path "$ProjectRoot\.env.example") {
    Copy-Item "$ProjectRoot\.env.example" "$ProjectRoot\.env"
    Write-Host "        .env created from .env.example -- FILL IN your API keys before using." -ForegroundColor Yellow
  }
  else {
    Write-Host "  [ERROR] .env file not found. Copy .env.example to .env and fill in your API keys." -ForegroundColor Red
    exit 1
  }
}
else {
  Write-Host "        .env found." -ForegroundColor Green
}

# Check that the most critical variables are not still placeholders
$envContent = Get-Content "$ProjectRoot\.env" -Raw
$missingKeys = @()
foreach ($key in @("GROQ_API_KEY", "SARVAM_API_KEY", "MONGODB_URI")) {
  if ($envContent -notmatch "$key\s*=\s*[^\s#]+") {
    $missingKeys += $key
  }
}
if ($missingKeys.Count -gt 0) {
  Write-Host "  [WARN]  The following keys appear unset in .env: $($missingKeys -join ', ')" -ForegroundColor Yellow
  Write-Host "          The server will start but some features may not work." -ForegroundColor DarkYellow
}
else {
  Write-Host "        All required keys present." -ForegroundColor Green
}

# =
# STEP 4 -- Run tests (pytest)
# =

if ($SkipTests) {
  Write-Host "  [4/5] Skipping tests (-SkipTests)." -ForegroundColor DarkGray
}
else {
  Write-Host "  [4/5] Running test suite ..." -ForegroundColor Cyan
  & $PythonExe -m pytest tests/ -q --tb=short 2>&1 | ForEach-Object { Write-Host "        $_" }
  if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  [ERROR] Tests failed. Fix the failures above or use -SkipTests to bypass." -ForegroundColor Red
    exit 1
  }
  Write-Host "        All tests passed." -ForegroundColor Green
}

# =
# STEP 5 -- Start Redis
# =

Write-Host "  [5/5] Starting services ..." -ForegroundColor Cyan

$redisRunning = $false
try {
  $tcp = New-Object System.Net.Sockets.TcpClient
  $tcp.Connect("127.0.0.1", $RedisPort)
  $tcp.Close()
  $redisRunning = $true
}
catch {
  $redisRunning = $false
}

if ($redisRunning) {
  Write-Host "        [Redis] Already running on port $RedisPort." -ForegroundColor Green
}
elseif (Test-Path $RedisExe) {
  Write-Host "        [Redis] Starting portable Redis on port $RedisPort ..." -ForegroundColor Yellow
  Start-Process -FilePath $RedisExe -ArgumentList "--port $RedisPort" -WindowStyle Minimized
  Start-Sleep -Seconds 2
  try {
    $tcp2 = New-Object System.Net.Sockets.TcpClient
    $tcp2.Connect("127.0.0.1", $RedisPort)
    $tcp2.Close()
    Write-Host "        [Redis] Started successfully." -ForegroundColor Green
  }
  catch {
    Write-Host "        [Redis] WARNING: Could not verify Redis start. Running without short-term cache." -ForegroundColor DarkYellow
  }
}
else {
  Write-Host "        [Redis] Not found at $RedisExe -- running without short-term cache." -ForegroundColor DarkYellow
}

# =
# LAUNCH -- FastAPI via Uvicorn
# =

Write-Host ""
Write-Host "  +-------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |  AegisAI is starting...                         |" -ForegroundColor Cyan
Write-Host "  +-------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dashboard  ->  http://localhost:$Port/ui"     -ForegroundColor White
Write-Host "  API Docs   ->  http://localhost:$Port/docs"   -ForegroundColor White
Write-Host "  Health     ->  http://localhost:$Port/health" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

if ($IsProd) {
  # Production: multiple workers, no file watcher
  & $PythonExe -m uvicorn main:app --host 0.0.0.0 --port $Port --workers $Workers
}
else {
  # Development: single worker with hot-reload
  & $PythonExe -m uvicorn main:app --host 0.0.0.0 --port $Port --reload
}
