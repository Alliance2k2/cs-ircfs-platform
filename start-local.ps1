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

if (-not (Test-Path $EnvironmentFile)) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") $EnvironmentFile
    Write-Host "Created .env from .env.example." -ForegroundColor Yellow
}

Push-Location $BackendRoot
# Python tools (Alembic, uvicorn) log to stderr; Windows PowerShell would treat that as a failure
# under "Stop", so native commands are checked through $LASTEXITCODE instead.
$ErrorActionPreference = "Continue"
try {
    python -c "import fastapi, uvicorn, sqlalchemy, pydantic_settings, alembic, geoalchemy2, httpx" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependencies are missing. Run: python -m pip install -r backend/requirements.txt"
    }
    python -c "import google.auth" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Note: google-auth is not installed, so 'Continue with Google' is disabled. Email sign-in works." -ForegroundColor Yellow
    }

    if ($Demo -or $ResetDemo) {
        $DemoDatabase = Join-Path $BackendRoot "demo.db"
        # Always delete the demo database so migrations start clean.
        # The demo database holds invented data only — nothing is lost.
        if (Test-Path $DemoDatabase) { Remove-Item $DemoDatabase -Confirm:$false }
        # Environment variables override .env for this window only.
        $env:DATABASE_URL = "sqlite:///" + ($DemoDatabase -replace "\\", "/")
        $env:ENVIRONMENT = "development"
        $env:REQUIRE_API_KEY = "false"
        python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw "Could not prepare the demonstration database." }
        python scripts/seed_demo_data.py
        if ($LASTEXITCODE -ne 0) { throw "Could not prepare the demonstration database." }
        Write-Host "DEMONSTRATION MODE: invented data in backend/demo.db. Everyone has full access; do not use for real records." -ForegroundColor Magenta
    }
    else {
        $DatabaseLine = (Get-Content $EnvironmentFile | Where-Object { $_ -match "^DATABASE_URL=" } | Select-Object -First 1)
        if ($DatabaseLine -match "^DATABASE_URL=postgres") {
            Write-Host "Applying database migrations..." -ForegroundColor Cyan
            python -m alembic upgrade head
            if ($LASTEXITCODE -ne 0) { throw "Database migration failed. Check that PostgreSQL is running, then try again." }
            python scripts/seed_reference_schemes.py
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
        python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --reload
    }
    else {
        python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
    }
}
finally {
    Pop-Location
}
