@echo off
REM Build ClipboardDLP.exe for Windows.
REM Requires Python 3.10+ (the Windows launcher "py" is recommended).
setlocal
cd /d "%~dp0\.."

if not exist .venv-build (
    echo Creating build venv...
    py -3.12 -m venv .venv-build 2>nul || py -m venv .venv-build
    if errorlevel 1 goto :fail
)

call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e . pyinstaller
if errorlevel 1 goto :fail

echo Building ClipboardDLP.exe...
pyinstaller --clean --noconfirm packaging\ClipboardDLP.spec
if errorlevel 1 goto :fail

echo.
echo Done: dist\ClipboardDLP.exe
echo.
pause
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1
