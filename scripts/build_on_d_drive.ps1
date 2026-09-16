$ErrorActionPreference = "Stop"

$BaseDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$RepoDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RepoUrl = "https://github.com/qadayas940-ui/ClinicDataSystem.git"
$Branch = "codex/v1-complete"
$PythonLauncher = "py"

Write-Host "== ClinicDataSystem build =="
Write-Host "Base directory: $BaseDir"

$RunningApp = Get-Process "ClinicDataSystem" -ErrorAction SilentlyContinue
if ($RunningApp) {
    Write-Host "Stopping the previous ClinicDataSystem process..."
    $RunningApp | Stop-Process -Force
}

New-Item -ItemType Directory -Force -Path $BaseDir | Out-Null
Set-Location $BaseDir

if (Test-Path $RepoDir) {
    if (Test-Path (Join-Path $RepoDir ".git")) {
        Set-Location $RepoDir
        git fetch origin $Branch
        git checkout $Branch
        git pull --ff-only origin $Branch
    } else {
        throw "The path $RepoDir exists but is not a Git repository. Rename it first, then run this script again."
    }
} else {
    git clone -b $Branch $RepoUrl $RepoDir
    Set-Location $RepoDir
}

Write-Host "Repository: $(Get-Location)"
$BuildCommit = (git rev-parse --short HEAD).Trim()
Write-Host "Building commit: $BuildCommit"

& $PythonLauncher -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-build.txt

& ".\.venv\Scripts\python.exe" manage.py check
& ".\.venv\Scripts\python.exe" manage.py test

$OldDist = Join-Path $RepoDir "dist\ClinicDataSystem"
$OldBuild = Join-Path $RepoDir "build\ClinicDataSystem"
if (Test-Path $OldDist) { Remove-Item -Recurse -Force $OldDist }
if (Test-Path $OldBuild) { Remove-Item -Recurse -Force $OldBuild }
& ".\.venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm ClinicDataSystem.spec

$ExePath = Join-Path $RepoDir "dist\ClinicDataSystem\ClinicDataSystem.exe"
if (-not (Test-Path $ExePath)) {
    throw "PyInstaller finished, but the EXE was not found at $ExePath"
}

Write-Host "Desktop EXE ready:"
Write-Host $ExePath

$DesktopDir = [Environment]::GetFolderPath("Desktop")
if ($DesktopDir) {
    $ShortcutPath = Join-Path $DesktopDir "ClinicDataSystem.lnk"
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = Split-Path $ExePath
    $Shortcut.Description = "ClinicDataSystem $BuildCommit"
    $Shortcut.Save()
    Write-Host "Desktop shortcut updated: $ShortcutPath"
}

$IsccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (Test-Path $IsccPath) {
    & $IsccPath "installer\ClinicDataSystem.iss"
    $SetupPath = Join-Path $RepoDir "release\ClinicDataSystem-Setup-1.3.0.exe"
    if (Test-Path $SetupPath) {
        Write-Host "Installer ready:"
        Write-Host $SetupPath
    } else {
        Write-Warning "Inno Setup finished, but the installer file was not found in release."
    }
} else {
    Write-Warning ("Inno Setup 6 was not found. Install it, then run this command from {0}:" -f $RepoDir)
    Write-Host '& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\ClinicDataSystem.iss'
}

Write-Host "Done."
