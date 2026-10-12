import os
import sys
import time
import socket
import webbrowser
import threading
import subprocess

# Windows Application Control ujson DLL bloklanishidan himoya
sys.modules['ujson'] = None

# Konsolda o'zbekcha belgilar va QR kod to'g'ri chiqishi uchun UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def get_network_ips():
    """Barcha faol lokal IP manzillarni (Wi-Fi, LAN) aniqlash"""
    ips = []
    # 1. Asosiy chiquvchi yo'nalish IP-si (odatda Wi-Fi yoki LAN)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        primary = s.getsockname()[0]
        s.close()
        if primary and not primary.startswith('127.') and not primary.startswith('169.254.'):
            ips.append(primary)
    except Exception:
        pass

    # 2. Hostname orqali boshqa interfeyslar
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.') and not ip.startswith('169.254.') and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    # 3. getaddrinfo fallback
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None):
            ip = item[4][0]
            if ':' not in ip and not ip.startswith('127.') and not ip.startswith('169.254.') and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    return ips

def generate_qr_codes(url, frontend_dir, base_dir):
    """Telefon bilan ulanish uchun QR-kod rasmlarini yaratish"""
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        
        # Sayt ichida ko'rinishi uchun
        img.save(os.path.join(frontend_dir, "wifi_qr.png"))
        # Papkaning o'zida ham saqlash
        img.save(os.path.join(base_dir, "wifi_qr_kod.png"))
        return True
    except Exception:
        return False

def print_ascii_qr(url):
    """Terminalda skanerlash uchun ASCII QR-kodni ko'rsatish"""
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        print("\n 📱 TELEFON KAMERASI BILAN SKANERLASH UCHUN QR KOD:")
        qr.print_ascii(invert=True)
    except Exception:
        pass

def free_port(port=8010):
    """Agar port boshqa eski jarayon tomonidan band bo'lsa, uni avtomatik bo'shatish"""
    current_pid = os.getpid()
    try:
        output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True, stderr=subprocess.DEVNULL)
        pids = set()
        for line in output.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and f":{port}" in parts[1] and "LISTENING" in parts[3]:
                try:
                    pid = int(parts[4])
                    if pid != current_pid and pid != 0:
                        pids.add(pid)
                except ValueError:
                    pass
        for pid in pids:
            try:
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f" [!] Port {port} ni band qilgan eski jarayon (PID: {pid}) to'xtatildi va port bo'shatildi.")
            except Exception:
                pass
        if pids:
            time.sleep(0.6)
    except Exception:
        pass

def open_browser():
    time.sleep(1.2)
    print(" [✓] Sayt brauzerda ochilmoqda: http://127.0.0.1:8010")
    webbrowser.open("http://127.0.0.1:8010")

def main():
    # Port 8010 band bo'lsa avtomatik bo'shatish
    free_port(8010)

    print("=" * 68)
    print("      TILORA — Adaptiv-Metakognitiv Ta'lim Veb-Platformasi")
    print("   To'liq Python orqali ishlovchi rasmiy veb-tizim (Wi-Fi / LAN)")
    print("=" * 68)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")
    
    os.chdir(backend_dir)
    sys.path.insert(0, backend_dir)
    
    # Tarmoq IP manzillarini aniqlash
    lan_ips = get_network_ips()
    primary_ip = lan_ips[0] if lan_ips else "127.0.0.1"
    primary_lan_url = f"http://{primary_ip}:8010"
    
    # QR kodlarni generatsiya qilish
    generate_qr_codes(primary_lan_url, frontend_dir, base_dir)
    
    print("\n [✓] Sayt manzillari:")
    print("     💻 Shu kompyuterda:   http://127.0.0.1:8010  (yoki http://localhost:8010)")
    
    if lan_ips:
        for idx, ip in enumerate(lan_ips, 1):
            print(f"     📱 Wi-Fi / Tarmoqda:  http://{ip}:8010  (Telefon, planshet, noutbuk)")
    else:
        print("     ⚠️  Wi-Fi yoki lokal tarmoq ulanishi topilmadi.")
        
    print("     📖 API Swagger:       http://127.0.0.1:8010/docs")

    # Terminalda QR kodni chiqarish
    if primary_ip != "127.0.0.1":
        print_ascii_qr(primary_lan_url)
        print(f" (QR kod rasmi: '{os.path.join(base_dir, 'wifi_qr_kod.png')}')\n")

    print("-" * 68)
    print(" [!] Eslatma: Telefon yoki boshqa noutbuk ham SHU Wi-Fi ga ulangan bo'lishi lozim.")
    print(" [!] Agar boshqa qurilmalar ulanolmasa, 'tarmoqqa_ruxsat_berish.bat' faylini")
    print("     sichqonchaning o'ng tugmasi bilan 'Run as administrator' qilib ishga tushiring.")
    print(" [!] Serverni to'xtatish uchun: CTRL + C tugmalarini bosing.")
    print("-" * 68 + "\n")

    try:
        import uvicorn
        from app.main import app
        
        # Brauzerni ochish
        threading.Thread(target=open_browser, daemon=True).start()
        
        uvicorn.run(app, host="0.0.0.0", port=8010, log_level="info")
    except Exception as e:
        print(f"\n[XATOLIK]: {e}")
        input("\nChiqish uchun Enter tugmasini bosing...")

if __name__ == "__main__":
    main()
