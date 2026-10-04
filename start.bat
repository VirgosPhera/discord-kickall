@echo off
rem ============================================================
rem  KickAll - jalankan bot (mode online, perintah !kickall)
rem  Double-click file ini. Tekan Ctrl+C untuk mematikan bot.
rem ============================================================
cd /d "%~dp0"

echo [1/2] Cek config...
.venv\Scripts\python.exe bot.py check
if errorlevel 1 (
    echo.
    echo Config belum siap, lihat pesan di atas. Tekan tombol apa saja untuk tutup.
    pause
    exit /b 1
)

echo.
echo [2/2] Menyalakan bot... (Ctrl+C untuk matikan)
.venv\Scripts\python.exe bot.py run
echo.
echo Bot berhenti. Tekan tombol apa saja untuk tutup.
pause
