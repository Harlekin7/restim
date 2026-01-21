@echo off
echo Building restim.exe...
echo.

REM Use the clean build virtual environment
set VENV_PATH=%~dp0build_venv

REM Check if build_venv exists
if not exist "%VENV_PATH%\Scripts\python.exe" (
    echo Error: build_venv not found!
    echo Please create it first with: C:\Python313\python.exe -m venv build_venv
    echo Then install dependencies: build_venv\Scripts\pip.exe install -r requirements.txt pyinstaller
    pause
    exit /b 1
)

echo Using Python from: %VENV_PATH%
echo.

"%VENV_PATH%\Scripts\python.exe" -m PyInstaller restim.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build successful!
    echo Executable: %~dp0dist\restim.exe
) else (
    echo.
    echo Build failed!
)

pause
