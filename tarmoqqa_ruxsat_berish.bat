@echo off
title TILORA — Wi-Fi va Lokal Tarmoq Ruxsati
chcp 65001 > nul
cls

echo ================================================================
echo    TILORA — Wi-Fi va Lokal Tarmoqda Ishlash Uchun Ruxsat Berish
echo ================================================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [OGOHLANTIRISH]
    echo Ushbu amal Windows Firewall sozlamasini o'zgartirish uchun
    echo Administrator huquqini talab qiladi.
    echo.
    echo Agar avtomatik ochilmasa:
    echo 1. Ushbu fayl (tarmoqqa_ruxsat_berish.bat) ustiga o'ng tugmani bosing.
    echo 2. "Запуск от имени администратора" (Run as administrator) ni tanlang.
    echo.
    echo Ruxsat so'rovi (UAC) chiqsa "Ha" / "Yes" tugmasini bosing...
    powershell -Command "Start-Process cmd.exe -ArgumentList '/k \"\"%~dp0tarmoqqa_ruxsat_berish.bat\"\" admin' -Verb RunAs" 2>nul
    pause
    exit /b
)

echo [1/3] 80-port (standart veb-port) qoidasi sozlanmoqda...
netsh advfirewall firewall delete rule name="TILORA Web Port 80" >nul 2>&1
netsh advfirewall firewall add rule name="TILORA Web Port 80" dir=in action=allow protocol=TCP localport=80 profile=any >nul 2>&1

echo [2/3] 8010-port qoidasi sozlanmoqda...
netsh advfirewall firewall delete rule name="TILORA Web Port 8010" >nul 2>&1
netsh advfirewall firewall add rule name="TILORA Web Port 8010" dir=in action=allow protocol=TCP localport=8010 profile=any >nul 2>&1

echo [3/3] Python ilovasi barcha tarmoqlar uchun ruxsatlanmoqda...
netsh advfirewall firewall delete rule name="TILORA Python Server" >nul 2>&1
for /f "delims=" %%I in ('where python 2^>nul') do (
    netsh advfirewall firewall add rule name="TILORA Python Server" dir=in action=allow program="%%I" profile=any >nul 2>&1
)

echo.
echo ================================================================
echo   [MUVAFFAQIN QABUL QILINDI!]
echo   8010-port va Python barcha tarmoqlar (Wi-Fi, Private, Public)
echo   uchun muvaffaqiyatli ochildi!
echo.
echo   Endi bir xil Wi-Fi yoki LAN tarmog'idagi barcha telefon,
echo   planshet va boshqa noutbuklar saytga bemalol kirishi mumkin.
echo ================================================================
echo.
pause
