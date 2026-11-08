@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==========================================
echo   ypriteConvert - build app + installer
echo ==========================================

REM ---- Python environment ---------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv || goto :fail
)
set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install -q --upgrade pip
"%PY%" -m pip install -q -r requirements.txt -r requirements-build.txt || goto :fail

REM ---- Version: optional first argument, e.g. build.bat 1.2.0 ---------------
if not "%~1"=="" "%PY%" tools\set_version.py %1 || goto :fail
"%PY%" -c "import app_info; print(app_info.VERSION)" > "%TEMP%\ypc_version.txt" || goto :fail
set /p VERSION=<"%TEMP%\ypc_version.txt"
echo [INFO] Version %VERSION%

REM ---- FFmpeg (bundled into the installer) -----------------------------------
if not exist "bin\ffmpeg.exe" (
    echo [INFO] bin\ffmpeg.exe missing - fetching FFmpeg...
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\fetch_ffmpeg.ps1 || goto :fail
)

REM ---- Icons --------------------------------------------------------------
if not exist "assets\icon.ico" "%PY%" tools\make_icon.py

REM ---- App ------------------------------------------------------------------
echo [INFO] Building app with PyInstaller...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
"%PY%" -m PyInstaller ypriteConvert.spec --clean --noconfirm || goto :fail

REM ---- Installer --------------------------------------------------------------
set "ISCC="
for %%p in ("%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do (
    if exist %%p set "ISCC=%%~p"
)
if not defined ISCC (
    echo [WARN] Inno Setup 6 not found - skipping installer.
    echo        Install it with:  winget install JRSoftware.InnoSetup
    goto :done
)
echo [INFO] Building installer...
"%ISCC%" /Q /DAppVersion=%VERSION% installer\ypriteConvert.iss || goto :fail

:done
echo.
echo ==========================================
echo   Done
echo   App:       dist\ypriteConvert\ypriteConvert.exe
if defined ISCC echo   Installer: Output\ypriteConvert-Setup-%VERSION%.exe
echo ==========================================
if "%CI%"=="" pause
exit /b 0

:fail
echo.
echo [ERROR] Build failed - see output above.
if "%CI%"=="" pause
exit /b 1
