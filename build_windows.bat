@echo off
setlocal
cd /d "%~dp0"
py -3.11 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python -m pip install --upgrade pip
if errorlevel 1 goto fail
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python -m unittest discover -s tests -v
if errorlevel 1 goto fail
.venv\Scripts\python -m PyInstaller --noconfirm --clean --onedir --windowed --name PriceRadarBR --collect-all customtkinter --collect-all undetected_chromedriver --collect-all reportlab --hidden-import PIL._tkinter_finder main.py
if errorlevel 1 goto fail
.venv\Scripts\python -m pip freeze > dist\PriceRadarBR\DEPENDENCIES.txt
copy README.md dist\PriceRadarBR\README.md >nul
powershell -NoProfile -Command "Compress-Archive -Path 'dist\PriceRadarBR' -DestinationPath 'dist\PriceRadarBR-Windows.zip' -Force"
if errorlevel 1 goto fail
echo Pronto: dist\PriceRadarBR\PriceRadarBR.exe
echo Distribua o ZIP completo: dist\PriceRadarBR-Windows.zip
pause
exit /b 0
:fail
echo Falha na compilacao. Confira o erro acima. Requer Windows e Python 3.11 x64.
pause
exit /b 1
