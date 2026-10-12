@echo off
title TILORA Adaptiv Ta'lim Veb-Platformasi (Python Server)
chcp 65001 > nul
cd /d "%~dp0"

echo =========================================================
echo    TILORA — Adaptiv Ta'lim Veb-Platformasi
echo    To'liq Python veb-serveri orqali ishga tushirilmoqda...
echo =========================================================

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python start_server.py
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        py start_server.py
    ) else (
        echo [XATOLIK] Python tizimda topilmadi!
        echo Iltimos, Python o'rnatilganligini va PATH ga qo'shilganligini tekshiring.
        pause
    )
)

pause
