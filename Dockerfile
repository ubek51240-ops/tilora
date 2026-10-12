# ============================================================
# TILORA — Production Multi-stage Dockerfile
# ============================================================

# 1-BOSQICH: Paketlarni yig'ish (Builder)
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 2-BOSQICH: Yakuniy yengil va xavfsiz imidj (Runner)
FROM python:3.11-slim AS runner

WORKDIR /app

# Xavfsizlik: Non-root foydalanuvchi yaratish
RUN useradd -m -u 1001 -s /bin/bash tilora

# Builder bosqichidan paketlarni nusxalash
COPY --from=builder /root/.local /home/tilora/.local

# Ilova fayllarini ko'chirish
COPY backend /app/backend
COPY frontend /app/frontend
COPY gunicorn_conf.py /app/gunicorn_conf.py

# O'qituvchi yuklaydigan audio fayllar uchun papka (docker-compose da volume sifatida ulanadi)
RUN mkdir -p /app/uploads/audio

# Huquqlarni tilora foydalanuvchisiga berish
RUN chown -R tilora:tilora /app

ENV PATH=/home/tilora/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend

USER tilora

EXPOSE 8010

# Production serverni Gunicorn + Uvicorn bilan ishga tushirish
CMD ["gunicorn", "-c", "/app/gunicorn_conf.py", "app.main:app"]
