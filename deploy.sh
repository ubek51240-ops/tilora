#!/bin/bash
# ============================================================
# TILORA — Avtomatik Serverga O'rnatish Skripti (Ubuntu/Debian)
# ============================================================

set -e

echo "=========================================================="
echo "   TILORA — Veb-Platformasini Serverga O'rnatish"
echo "=========================================================="

# 1. Docker va Docker Compose o'rnatilganligini tekshirish
if ! command -v docker &> /dev/null; then
    echo "[1/4] Docker o'rnatilmoqda..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "Docker muvaffaqiyatli o'rnatildi."
else
    echo "[1/4] Docker allaqachon mavjud."
fi

# 2. Muhit faylini sozlash
if [ ! -f .env ]; then
    echo "[2/4] .env fayli .env.production dan nusxalanmoqda..."
    cp .env.production .env
fi

# 3. Konteynerlarni qurish va ishga tushirish
echo "[3/4] Konteynerlar yig'ilmoqda va ishga tushirilmoqda..."
docker compose down || true
docker compose up -d --build

# 4. Kutilayotgan xizmatlarni tekshirish
echo "[4/4] Tizim holati tekshirilmoqda..."
sleep 5

docker compose ps

echo ""
echo "=========================================================="
echo " [MUVAFFAQIYAT]: TILORA sayti internetda ishga tushdi!"
echo " Sayt manzili: http://$(curl -s ifconfig.me || echo 'SERVER_IP')"
echo " API Docs:     http://$(curl -s ifconfig.me || echo 'SERVER_IP')/docs"
echo "=========================================================="
