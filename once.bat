@echo off
rem ============================================================
rem  KickAll - mode sekali jalan
rem  Pakai  : once.bat ID_SERVER        (preview, nol kick)
rem           once.bat ID_SERVER --yes  (eksekusi)
rem ============================================================
cd /d "%~dp0"

if "%~1"=="" (
    echo Cara pakai:
    echo   once.bat ID_SERVER        preview dulu, tidak ada yang di-kick
    echo   once.bat ID_SERVER --yes  eksekusi
    echo.
    echo Contoh: once.bat 987654321098765432
    echo.
    pause
    exit /b 2
)

.venv\Scripts\python.exe bot.py check
if errorlevel 1 (
    echo.
    echo Config belum siap. Tekan tombol apa saja untuk tutup.
    pause
    exit /b 1
)

echo.
.venv\Scripts\python.exe bot.py once %1 %2
echo.
pause
