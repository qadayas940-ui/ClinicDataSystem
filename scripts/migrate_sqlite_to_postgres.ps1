param(
    [Parameter(Mandatory=$true)][string]$SqlitePath,
    [Parameter(Mandatory=$true)][string]$PostgresUrl
)

$ErrorActionPreference = "Stop"
$RepoDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoDir ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Build virtual environment not found at $Python" }
if (-not (Test-Path $SqlitePath)) { throw "SQLite source database was not found: $SqlitePath" }

$WorkingDir = Join-Path ([System.IO.Path]::GetTempPath()) ("clinic-migration-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $WorkingDir | Out-Null
$Fixture = Join-Path $WorkingDir "clinic-data.json"

try {
    $env:DJANGO_SETTINGS_MODULE = "config.settings.development"
    $env:CLINIC_DATA_PATH = Split-Path -Parent (Split-Path -Parent $SqlitePath)
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    & $Python "$RepoDir\manage.py" dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --indent 2 --output $Fixture

    $env:DATABASE_URL = $PostgresUrl
    $env:DJANGO_SETTINGS_MODULE = "config.settings.production"
    & $Python "$RepoDir\manage.py" migrate --noinput
    & $Python "$RepoDir\manage.py" loaddata $Fixture
    & $Python "$RepoDir\manage.py" check
    Write-Host "Migration completed. Keep the original SQLite database as a read-only backup until verification is complete."
} finally {
    Remove-Item -Recurse -Force $WorkingDir -ErrorAction SilentlyContinue
}
