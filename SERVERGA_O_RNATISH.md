# 🚀 TILORA SAYTINI INTERNETGA CHIQARISH BO'YICHA TO'LIQ QO'LLANMA

Ushbu qo'llanma orqali siz **TILORA** platformasini 10 daqiqa ichida internetga (haqiqiy server va ochiq domen manziliga) muvaffaqiyatli chiqara olasiz.

---

## 📋 1-Qadam: Domen va Server (VPS) Tayyorlash

### 1. Domen olish:
* O'zbekiston milliy domen provayderlaridan (masalan: `cpanel.uz`, `eskiz.uz`, `regos.uz`):
  * Masalan: `tilora.uz` yoki `tilora.buxdu.uz` (OTM ichki subdomeni).
* Domen DNS sozlamalariga kirib, **`A Record`** qismiga serveringizning IP manzilini bog'laysiz:
  ```
  Type: A
  Host: @ (yoki www)
  Value: 185.xxx.xxx.xxx (Serveringizning haqiqiy IP manzili)
  ```

### 2. Server (VPS):
* Tavsiya etiladigan OT: **Ubuntu 22.04 LTS** yoki **Ubuntu 24.04 LTS**.
* Minimal talablar: 1 CPU, 2 GB RAM, 25 GB SSD (oyiga ~4–6$ yoki OTM serveri).

---

## 📦 2-Qadam: Kodni Serverga Yuklash

Kompyuteringizdagi `TILORA` papkasini serverga nusxalash:

### A varianti: Git orqali (eng osoni)
Serveringiz konsoliga (SSH) kirib yozasiz:
```bash
git clone https://github.com/sizning-akkount/TILORA.git /var/www/tilora
cd /var/www/tilora
```

### B varianti: FileZilla yoki SCP orqali
Kompyuteringizdagi `C:\Users\HP\Desktop\TILORA` jildini serveringizning `/var/www/tilora` jildiga ko'chiring.

---

## ⚡ 3-Qadam: Bitta Buyruq Bilan Ishga Tushirish (Docker Usuli)

Serverda loyiha papkasiga o'ting va avtomatik o'rnatish skriptini ishga tushiring:

```bash
cd /var/www/tilora
chmod +x deploy.sh
./deploy.sh
```

**Bu skript nima qiladi?**
1. Docker va Docker Compose o'rnatilmagan bo'lsa, o'zi avtomatik o'rnatadi.
2. PostgreSQL bazasini, Python FastAPI ilovasini va Nginx veb-serverini xavfsiz konteynerlarda ko'taradi.
3. Barcha 51 ta endpoint, 25 ta jadval va frontend sahifalarini bir zumda internetga ochadi!

Saytingiz darhol server IP manzili orqali ishlay boshlaydi:
* `http://SERVER_IP/` — Veb-sayt
* `http://SERVER_IP/docs` — API Swagger

---

## 🔒 4-Qadam: Bepul SSL (HTTPS) Sertifikatini Yoqish

Sayt xavfsiz qulf (`https://`) bilan ochilishi uchun Let's Encrypt bepul sertifikatini qo'shamiz:

```bash
# Certbot o'rnatish
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# Sertifikat olish (domen nomingizni yozing)
sudo certbot --nginx -d tilora.uz -d www.tilora.uz
```
Certbot avtomatik ravishda HTTPS ni yoqadi va muddati tugaganda o'zi yangilanib turadi.

---

## 🛠️ 5-Qadam: Foydali Server Buyruqlari

* **Sayt holatini tekshirish:**
  ```bash
  docker compose ps
  ```
* **Jonli loglarni ko'rish:**
  ```bash
  docker compose logs -f web
  ```
* **Serverni to'xtatish:**
  ```bash
  docker compose down
  ```
* **Serverni qayta ishga tushirish (yangilash kiritilganda):**
  ```bash
  docker compose up -d --build
  ```

---

## 🏛️ 6-Qadam: OTM Mahalliy Tarmog'ida (Lokal Tarmoqda) Ishlatish

Agar saytni tashqi internetga emas, faqat OTM ichki kompyuterlarida (Wi-Fi yoki lokal LAN orqali) ishlatmoqchi bo'lsangiz:
1. Bosh kompyuterda `start.bat` ni ishga tushiring.
2. Ushbu kompyuterning lokal IP manzilini bilib oling (masalan: `192.168.1.45`).
3. Auditoriyadagi barcha talaba va o'qituvchilar o'z telefon yoki noutbuklarida brauzerni ochib:
   `http://192.168.1.45:8010`
   manziliga kirsa, sayt lokal tarmoqda internet sarflamasdan ham tezkor ishlaydi!
