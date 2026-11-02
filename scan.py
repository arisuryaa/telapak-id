"""scan.py - mengenali tangan dari kamera. Jalankan: python scan.py
Tombol: + / -  = ubah batas, ESC = keluar"""
import os, glob
import cv2, numpy as np
import palm

FOLDER = "data_terdaftar"
batas = 0.38   # jarak di bawah ini dianggap "dikenali" (sesuaikan lewat tombol + / -)

galeri = {}
for f in glob.glob(os.path.join(FOLDER, "*.npy")):
    galeri[os.path.basename(f)[:-4]] = list(np.load(f))
if not galeri:
    raise SystemExit("Belum ada yang terdaftar. Jalankan daftar.py dulu.")
print("Terdaftar:", ", ".join(galeri))

cap = cv2.VideoCapture(0)
while True:
    ok, frame = cap.read()
    if not ok:
        break
    lm = palm.cari_landmark(frame)
    roi = palm.ambil_roi(frame, lm) if lm else None
    tampil = frame.copy()

    if roi is None:
        teks, warna = "Taruh telapak di depan kamera", (0, 0, 255)
    else:
        tampil[0:128, 0:128] = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
        kode = palm.hitung_kode(roi)
        jarak = {n: palm.jarak_ke_orang(kode, ks) for n, ks in galeri.items()}
        terdekat = min(jarak, key=jarak.get)
        if jarak[terdekat] < batas:
            teks, warna = f"Dikenali: {terdekat}  (jarak {jarak[terdekat]:.2f})", (0, 200, 0)
        else:
            teks, warna = f"Tidak dikenal  (terdekat {jarak[terdekat]:.2f})", (0, 165, 255)

    cv2.putText(tampil, teks, (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna, 2)
    cv2.putText(tampil, f"batas = {batas:.2f}  (+/-)", (10, 190),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.imshow("Scan", tampil)
    tombol = cv2.waitKey(1) & 0xFF
    if tombol == 27:
        break
    elif tombol in (ord("+"), ord("=")):
        batas = min(0.5, batas + 0.01)
    elif tombol == ord("-"):
        batas = max(0.1, batas - 0.01)

cap.release()
cv2.destroyAllWindows()
