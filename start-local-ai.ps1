$ErrorActionPreference = "Stop"
$AiProjectRoot = $PSScriptRoot
$AiRoot = Join-Path $AiProjectRoot "backend\.local-ai"
$AiPython = Join-Path $AiProjectRoot ".venv\Scripts\python.exe"
$AiKeyFile = Join-Path $AiRoot "access.key"
if (-not (Test-Path -LiteralPath $AiRoot)) { throw "Run backend/scripts/setup_local_ai.py first." }
if (-not (Test-Path -LiteralPath $AiKeyFile)) {
    & $AiPython -c "import secrets,sys; from pathlib import Path; Path(sys.argv[1]).write_text(secrets.token_urlsafe(48),encoding='utf-8')" $AiKeyFile
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare local model access key." }
}
$AiHeaders = @{ Authorization = "Bearer " + (Get-Content -LiteralPath $AiKeyFile -Raw).Trim() }
try {
    $AiExisting = Invoke-RestMethod -Uri "http://127.0.0.1:11435/v1/models" -Headers $AiHeaders -TimeoutSec 2
    if (@($AiExisting.data.id) -contains "cs-assistant-local") { Write-Host "Verified local AI is already running."; return }
    throw "Port 11435 is serving another model. Refusing to replace it."
} catch {
    if ($_.Exception.Message -like "Port 11435*") { throw }
}
& $AiPython (Join-Path $AiProjectRoot "backend\scripts\setup_local_ai.py") --verify-only
if ($LASTEXITCODE -ne 0) { throw "Local AI artifact verification failed." }
$AiBinary = Join-Path $AiRoot "bin\llama-server.exe"
$AiModel = Join-Path $AiRoot "qwen2.5-1.5b-instruct-q4_k_m.gguf"
$AiArguments = @("-m", ('"' + $AiModel + '"'), "--host", "127.0.0.1", "--port", "11435", "--alias", "cs-assistant-local", "--ctx-size", "4096", "--threads", "4", "--threads-batch", "4", "--parallel", "1", "--n-predict", "256", "--no-webui", "--no-webui-mcp-proxy", "--cors-origins", "localhost", "--api-key-file", ('"' + $AiKeyFile + '"'))
$AiProcess = Start-Process -FilePath $AiBinary -ArgumentList $AiArguments -WorkingDirectory $AiRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $AiRoot "server.stdout.log") -RedirectStandardError (Join-Path $AiRoot "server.stderr.log")
Set-Content -LiteralPath (Join-Path $AiRoot "server.pid") -Value $AiProcess.Id
Write-Host "Local model is starting on loopback port 11435 (PID $($AiProcess.Id)). No paid API."
