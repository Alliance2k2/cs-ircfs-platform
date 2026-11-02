param(
    [string]$OutputDirectory = "./backups",
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $OutputDirectory "cs-ircfs-$stamp.dump"

Write-Host "Creating PostgreSQL backup: $backup"
$process = Start-Process -FilePath "docker" -ArgumentList @("compose", "--env-file", "stack.env", "exec", "-T", "db", "pg_dump", "-U", "cs_ircfs", "-Fc", "cs_ircfs") -RedirectStandardOutput $backup -NoNewWindow -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "pg_dump failed with exit code $($process.ExitCode)" }
if (-not (Test-Path $backup) -or (Get-Item $backup).Length -eq 0) { throw "Backup was not created" }

Get-ChildItem -Path $OutputDirectory -Filter "cs-ircfs-*.dump" |
    Where-Object { $_.LastWriteTimeUtc -lt (Get-Date).AddDays(-$RetentionDays).ToUniversalTime() } |
    Remove-Item -Force

Write-Host "Backup complete. Do not retain an unencrypted copy on the application server."
