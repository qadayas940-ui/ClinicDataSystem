$ErrorActionPreference = "Stop"

$RepoDir = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
Set-Location $RepoDir

$RunningApp = Get-Process "ClinicDataSystem" -ErrorAction SilentlyContinue
if ($RunningApp) { $RunningApp | Stop-Process -Force }

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher was not found. Install Python 3.12 on the build machine only."
}

& py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-build.txt
& ".\.venv\Scripts\python.exe" manage.py check --settings=config.settings.testing
& ".\.venv\Scripts\python.exe" manage.py test

$DistDir = Join-Path $RepoDir "dist\ClinicDataSystem"
$BuildDir = Join-Path $RepoDir "build\ClinicDataSystem"
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }

& ".\.venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm ClinicDataSystem.spec

$IsccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (Test-Path $IsccPath) {
    & $IsccPath "installer\ClinicDataSystem.iss"
    Write-Host "Installer ready in: $(Join-Path $RepoDir 'release')"
} else {
    Write-Warning "Inno Setup 6 is not installed. The portable EXE bundle is ready in dist."
}
