"""daftar.py - mendaftarkan tangan seseorang. Jalankan: python daftar.py"""
import os, time
import cv2, numpy as np
import palm

JUMLAH = 8          # jumlah sampel per tangan
JEDA = 0.8          # detik antar sampel
FOLDER = "data_terdaftar"
os.makedirs(FOLDER, exist_ok=True)

nama = input("Nama (tanpa spasi, mis. pak_budi): ").strip()
tangan = input("Tangan kiri atau kanan? (kiri/kanan): ").strip().lower()
setuju = input("Orang ini setuju datanya disimpan? (y/n): ").strip().lower()
if setuju != "y" or not nama:
    raise SystemExit("Dibatalkan: pendaftaran butuh persetujuan.")
nama = f"{nama}_{tangan}"

cap = cv2.VideoCapture(0)
kumpulan, terakhir = [], 0
print("Taruh telapak menghadap kamera. Tekan ESC untuk batal.")

while len(kumpulan) < JUMLAH:
    ok, frame = cap.read()
    if not ok:
        break
    lm = palm.cari_landmark(frame)
    roi = palm.ambil_roi(frame, lm) if lm else None
    tampil = frame.copy()

    if roi is None:
        teks, warna = "Tangan belum terdeteksi / terlalu dekat-jauh", (0, 0, 255)
    else:
        teks, warna = f"Tahan... sampel {len(kumpulan)}/{JUMLAH}", (0, 200, 0)
        tampil[0:128, 0:128] = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)  # pratinjau ROI
        if time.time() - terakhir > JEDA:
            kumpulan.append(palm.hitung_kode(roi))
            terakhir = time.time()

    cv2.putText(tampil, teks, (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna, 2)
    cv2.imshow("Daftar", tampil)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()

if len(kumpulan) == JUMLAH:
    np.save(os.path.join(FOLDER, nama + ".npy"), np.stack(kumpulan))  # hanya kode, bukan foto
    print(f"Tersimpan: {nama} ({JUMLAH} sampel)")
else:
    print("Pendaftaran tidak selesai, tidak ada yang disimpan.")
