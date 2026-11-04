param(
    [int]$Port = 8000,
    [switch]$Reload,
    # Run on a separate, pre-filled demonstration database (backend/demo.db). Your real database is not touched.
    [switch]$Demo,
    # With -Demo: delete demo.db first and create a fresh demonstration dataset.
    [switch]$ResetDemo
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = Join-Path $ProjectRoot "backend"
$EnvironmentFile = Join-Path $ProjectRoot ".env"
$LocalPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $LocalPython) { $LocalPython } else { "python" }

if (-not (Test-Path $EnvironmentFile)) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") $EnvironmentFile
    Write-Host "Created .env from .env.example." -ForegroundColor Yellow
}

Push-Location $BackendRoot
# Python tools (Alembic, uvicorn) log to stderr; Windows PowerShell would treat that as a failure
# under "Stop", so native commands are checked through $LASTEXITCODE instead.
$ErrorActionPreference = "Continue"
try {
    & $Python -c "import fastapi, uvicorn, sqlalchemy, pydantic_settings, alembic, geoalchemy2, httpx" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependencies are missing. Run: python -m pip install -r backend/requirements.txt"
    }
    & $Python -c "import google.auth" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Note: google-auth is not installed, so 'Continue with Google' is disabled. Email sign-in works." -ForegroundColor Yellow
    }

    if ($Demo -or $ResetDemo) {
        $DemoDatabase = Join-Path $BackendRoot "demo.db"
        # Preserve training work on ordinary restarts; reset only when explicitly requested.
        if ($ResetDemo -and (Test-Path $DemoDatabase)) { Remove-Item -LiteralPath $DemoDatabase -Confirm:$false }
        # Environment variables override .env for this window only.
        $env:DATABASE_URL = "sqlite:///" + ($DemoDatabase -replace "\\", "/")
        $env:ENVIRONMENT = "development"
        $env:REQUIRE_API_KEY = "false"
        $env:DEV_AUTH_BYPASS = "false"
        $env:SMS_PROVIDER = "dry_run"
        $env:AIRTIME_PROVIDER = "dry_run"
        $env:ALLOW_LIVE_MESSAGES = "false"
        $env:ANONYMOUS_REPLY_QUEUE_ENABLED = "false"
        $env:WEATHER_FORECAST_ENABLED = "false"
        $env:ADVICE_SCHEDULE_ENABLED = "false"
        $env:ALERT_PHONE_NUMBERS = ""
        $env:OPERATIONAL_ALERT_WEBHOOK_URL = ""
        & $Python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw "Could not prepare the demonstration database." }
        & $Python scripts/seed_demo_data.py
        if ($LASTEXITCODE -ne 0) { throw "Could not prepare the demonstration database." }
        Write-Host "DEMONSTRATION MODE: invented data in backend/demo.db. Sign in with an approved account; do not use for real records." -ForegroundColor Magenta
    }
    else {
        $DatabaseLine = (Get-Content $EnvironmentFile | Where-Object { $_ -match "^DATABASE_URL=" } | Select-Object -First 1)
        if ($DatabaseLine -match "^DATABASE_URL=postgres") {
            Write-Host "Applying database migrations..." -ForegroundColor Cyan
            & $Python -m alembic upgrade head
            if ($LASTEXITCODE -ne 0) { throw "Database migration failed. Check that PostgreSQL is running, then try again." }
            & $Python scripts/seed_reference_schemes.py
        }
    }

    # The React dashboard (/app/) is built once; rebuild after changing frontend/ (or use `npm run dev` there).
    $FrontendRoot = Join-Path $ProjectRoot "frontend"
    if (-not (Test-Path (Join-Path $FrontendRoot "dist\index.html"))) {
        if (Get-Command npm -ErrorAction SilentlyContinue) {
            Write-Host "Building the React dashboard (first run only)..." -ForegroundColor Cyan
            Push-Location $FrontendRoot
            try {
                if (-not (Test-Path "node_modules")) { npm ci --no-audit --no-fund }
                npm run build
                if ($LASTEXITCODE -ne 0) { Write-Host "React build failed; the classic dashboard still works." -ForegroundColor Yellow }
            }
            finally { Pop-Location }
        }
        else {
            Write-Host "Node.js is not installed, so the new dashboard (/app/) is not built. The classic pages work." -ForegroundColor Yellow
        }
    }

    Write-Host "CS-IRCFS is starting locally..." -ForegroundColor Green
    Write-Host "Platform:        http://127.0.0.1:$Port"
    Write-Host "Executive view:  http://127.0.0.1:$Port/app/"
    Write-Host "Planner:         http://127.0.0.1:$Port/planner.html"
    Write-Host "Phone simulator: http://127.0.0.1:$Port/simulator.html"
    Write-Host "API docs:        http://127.0.0.1:$Port/docs"
    Write-Host "Refresh the browser after dashboard changes. Restart this command after Python changes."
    Write-Host "Press Ctrl+C to stop the platform."
    if ($Reload) {
        & $Python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --reload
    }
    else {
        & $Python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
    }
}
finally {
    Pop-Location
}
