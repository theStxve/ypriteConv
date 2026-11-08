@echo off
REM Quick Start Script for ypriteConvert
REM Launches the GUI application

echo ==========================================
echo                ypriteConvert
echo ==========================================
echo.

REM Check if EXE exists (compiled version)
if exist "dist\ypriteConvert\ypriteConvert.exe" (
    echo [INFO] Launching EXE...
    start "" "dist\ypriteConvert\ypriteConvert.exe"
    goto :end
)

REM Otherwise run from Python
echo [INFO] Launching Python version...

REM Activate virtual environment (silent errors)
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" main.py
    goto :end
)

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" main.py
    goto :end
)

if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" main.py
    goto :end
)

if exist "venv\Scripts\python.exe" (
    start "" "venv\Scripts\python.exe" main.py
    goto :end
)

REM Fallback to system Python
echo [WARNING] No venv found, using system Python...
start "" python main.py

:end
exit /b 0
