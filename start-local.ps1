param(
    [int]$Port = 8000,
    [switch]$Reload
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
try {
    python -c "import fastapi, uvicorn, sqlalchemy" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependencies are missing. Run: python -m pip install -r backend/requirements.txt"
    }

    Write-Host "CS-IRCFS is starting locally..." -ForegroundColor Green
    Write-Host "Platform: http://127.0.0.1:$Port"
    Write-Host "API documentation: http://127.0.0.1:$Port/docs"
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
