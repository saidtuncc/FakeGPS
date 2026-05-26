@echo off
title FakeGPS Pro
echo.
echo   ========================================
echo        FakeGPS Pro
echo   ========================================
echo.

REM Python kontrol
python --version >nul 2>&1
if errorlevel 1 (
    echo   X Python bulunamadi!
    echo   https://python.org adresinden indir
    echo   Kurulumda "Add Python to PATH" isaretlemeyi unutma!
    pause
    exit /b
)

echo   Python bulundu!

REM Bagimliliklari kur
echo   Bagimliliklar kontrol ediliyor...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo   Flask kuruluyor...
    pip install flask
)

python -c "import pymobiledevice3" >nul 2>&1
if errorlevel 1 (
    echo   pymobiledevice3 kuruluyor...
    pip install pymobiledevice3
)

echo.
echo   FakeGPS Pro baslatiliyor...
echo   Tarayicida ac: http://127.0.0.1:5555
echo.
echo   ONEMLI: Once ayri bir terminalde tunnel baslat:
echo   python -m pymobiledevice3 remote start-tunnel --protocol tcp
echo   (Yonetici olarak calistir!)
echo.

REM Tarayiciyi ac
start http://127.0.0.1:5555

REM Uygulamayi baslat
cd /d "%~dp0"
python fakegps_app.py

pause
