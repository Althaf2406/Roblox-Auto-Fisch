import time
import mss
import numpy as np
import cv2
import ctypes
import keyboard
import os

# Konstanta untuk event klik kiri mouse di Windows
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

def mouse_down():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)

def mouse_up():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def mouse_click():
    mouse_down()
    time.sleep(0.05)
    mouse_up()

# ==========================================
# KONFIGURASI AREA TANGKAPAN LAYAR
# ==========================================
CAPTURE_ZONE = {
    "top": 800,    
    "left": 500,   
    "width": 920,  
    "height": 150  
}

# Hotkeys
START_KEY = 'up'
PAUSE_KEY = 'down'
EXIT_KEY = 'q'

# Konfigurasi Macro
CAST_POWER_TIME = 1.0 # Waktu tahan klik untuk lempar pancingan (detik)
SHAKE_CLICK_DELAY = 0.1 # Jeda antar klik saat fase Shaking (detik)
REELING_TIMEOUT = 3.0 # Waktu (detik) tanpa deteksi bar/fish sebelum dianggap selesai/gagal

# State Machine
STATE_IDLE = "IDLE"
STATE_CASTING = "CASTING"
STATE_SHAKING = "SHAKING"
STATE_REELING = "REELING"

def main():
    print("==================================")
    print("AUTO FISCH BOT (VISION + FULL LOOP)")
    print("==================================")
    
    if not os.path.exists("fish.png") or not os.path.exists("bar.png"):
        print("[ERROR] Gambar 'fish.png' atau 'bar.png' tidak ditemukan!")
        print("Silakan ambil screenshot KECIL (menggunakan Snipping Tool / Win+Shift+S):")
        print("1. Ikon ikan saja, lalu save sebagai 'fish.png'")
        print("2. Bagian tengah bar kontrol pemain saja, lalu save sebagai 'bar.png'")
        return

    template_fish = cv2.imread("fish.png", 0)
    template_bar = cv2.imread("bar.png", 0)
    
    fish_w, fish_h = template_fish.shape[::-1]
    bar_w, bar_h = template_bar.shape[::-1]

    print(f"[{START_KEY}] - Start/Resume Bot")
    print(f"[{PAUSE_KEY}] - Pause Bot")
    print(f"[{EXIT_KEY}] - Exit Program")
    
    current_state = STATE_IDLE
    is_clicking_bar = False
    last_seen_minigame = 0

    with mss.MSS() as sct:
        while True:
            # 1. Cek hotkeys
            if keyboard.is_pressed(EXIT_KEY):
                if is_clicking_bar:
                    mouse_up()
                print("Keluar dari program...")
                break
                
            if keyboard.is_pressed(START_KEY) and current_state == STATE_IDLE:
                print("Bot MULAI bekerja! Memulai Casting...")
                current_state = STATE_CASTING
                time.sleep(0.3)
                
            if keyboard.is_pressed(PAUSE_KEY) and current_state != STATE_IDLE:
                print("Bot DI-PAUSE!")
                current_state = STATE_IDLE
                if is_clicking_bar:
                    mouse_up()
                    is_clicking_bar = False
                time.sleep(0.3)

            if current_state == STATE_IDLE:
                time.sleep(0.01)
                continue

            # 2. Tangkap layar pada area bar
            img = np.array(sct.grab(CAPTURE_ZONE))
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

            # 3. Cari posisi ikan dan bar menggunakan template matching
            res_fish = cv2.matchTemplate(img_gray, template_fish, cv2.TM_CCOEFF_NORMED)
            _, max_val_fish, _, max_loc_fish = cv2.minMaxLoc(res_fish)
            
            res_bar = cv2.matchTemplate(img_gray, template_bar, cv2.TM_CCOEFF_NORMED)
            _, max_val_bar, _, max_loc_bar = cv2.minMaxLoc(res_bar)

            threshold = 0.6
            fish_detected = (max_val_fish >= threshold)
            bar_detected = (max_val_bar >= threshold)

            # STATE MACHINE LOGIC

            if current_state == STATE_CASTING:
                print("[STATE] Casting: Melempar pancingan...")
                # Tahan klik kiri selama CAST_POWER_TIME
                mouse_down()
                time.sleep(CAST_POWER_TIME)
                mouse_up()
                print("[STATE] Casting selesai. Menunggu gigitan (Shaking)...")
                # Beri waktu bobber mendarat
                time.sleep(2.0)
                current_state = STATE_SHAKING
                continue

            elif current_state == STATE_SHAKING:
                # Spam klik untuk menekan tombol 'Shake'
                # (Pastikan opsi 'UI Navigation' menyala di pengaturan Fisch di Roblox)
                mouse_click()
                
                # Jika bar reeling muncul, pindah ke state REELING
                if fish_detected and bar_detected:
                    print("[STATE] Minigame terdeteksi! Pindah ke Reeling...")
                    current_state = STATE_REELING
                    last_seen_minigame = time.time()
                
                time.sleep(SHAKE_CLICK_DELAY)
                continue

            elif current_state == STATE_REELING:
                fish_x = None
                bar_x = None

                if fish_detected:
                    fish_x = max_loc_fish[0] + (fish_w // 2)
                if bar_detected:
                    bar_x = max_loc_bar[0] + (bar_w // 2)

                if fish_x is not None and bar_x is not None:
                    last_seen_minigame = time.time()
                    tolerance = 10 
                    
                    # Jika ikan di KANAN bar -> Tahan Klik Kiri
                    if fish_x > bar_x + tolerance:
                        if not is_clicking_bar:
                            mouse_down()
                            is_clicking_bar = True
                    # Jika ikan di KIRI bar -> Lepas Klik Kiri
                    elif fish_x < bar_x - tolerance:
                        if is_clicking_bar:
                            mouse_up()
                            is_clicking_bar = False
                else:
                    if is_clicking_bar:
                        mouse_up()
                        is_clicking_bar = False

                    # Cek apakah minigame sudah selesai
                    if time.time() - last_seen_minigame > REELING_TIMEOUT:
                        print("[STATE] Minigame selesai atau hilang. Mengulang Casting...")
                        current_state = STATE_CASTING
                        time.sleep(2.0) # Jeda sebelum lempar lagi

            time.sleep(0.01)

if __name__ == "__main__":
    main()
