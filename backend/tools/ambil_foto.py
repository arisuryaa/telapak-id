"""ambil_foto.py - collect test photos from the webcam for bandingkan_skala.py.

Run from the backend folder, one hand at a time:

    python tools/ambil_foto.py dewa_kanan
    python tools/ambil_foto.py dewa_kiri --jumlah 30
    python tools/ambil_foto.py budi_kanan

A window shows the camera (mirrored, like the app). Press SPACE to start, ESC to quit. After a short
countdown it takes a photo every `--jeda` seconds. Move the hand slightly between photos, the way a
real person does between scans. Photos are saved unmirrored, like the frames the browser sends, to
data_uji/<name>/<date>_<time>_<number>.jpg.

Tips for a fair test:
  - at least 2 hands: your right and left hand count as different people, or ask a friend
  - 20+ photos per hand: the first 8 enroll the hand and the rest are scans
  - take the scan photos in another session (another time, other light), the way real use goes:
    run the command again for the same hand and the new photos are added after the old ones
  - same distance to the camera and same light as you normally use the app

These photos are biometric data. data_uji/ is ignored by git. Delete it when you are done.
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

FOLDER = Path(__file__).resolve().parent.parent / "data_uji"
JENDELA = "Ambil foto uji"


def tampil(frame, teks, kecil=""):
    """Show the mirrored preview with a message and return the key pressed (or -1)."""
    img = cv2.flip(frame, 1)
    for warna, tebal in (((0, 0, 0), 5), ((255, 255, 255), 2)):  # a black outline, then white text on top
        cv2.putText(img, teks, (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.0, warna, tebal, cv2.LINE_AA)
        if kecil:
            cv2.putText(img, kecil, (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna, max(1, tebal - 2), cv2.LINE_AA)
    cv2.imshow(JENDELA, img)
    return cv2.waitKey(30) & 0xFF


def buka_kamera(nomor):
    # DirectShow opens faster and honours the requested size on Windows
    kamera = cv2.VideoCapture(nomor, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(nomor)
    kamera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return kamera


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ambil foto telapak dari webcam untuk pengujian.")
    ap.add_argument("nama", help="nama folder tangan, misalnya dewa_kanan")
    ap.add_argument("--jumlah", type=int, default=20, help="jumlah foto (default 20)")
    ap.add_argument("--jeda", type=float, default=2.0, help="detik antar foto (default 2)")
    ap.add_argument("--kamera", type=int, default=0, help="nomor kamera (default 0)")
    ap.add_argument("--folder", default=str(FOLDER), help="folder tujuan (default backend/data_uji)")
    args = ap.parse_args(argv)

    tujuan = Path(args.folder) / args.nama
    kamera = buka_kamera(args.kamera)
    if not kamera.isOpened():
        print("Galat: kamera tidak bisa dibuka. Tutup aplikasi lain yang memakai kamera, atau coba --kamera 1.", file=sys.stderr)
        return 1
    tujuan.mkdir(parents=True, exist_ok=True)

    tersimpan = 0
    try:
        # wait for SPACE
        mulai = False
        while not mulai:
            ok, frame = kamera.read()
            if not ok:
                print("Galat: kamera berhenti mengirim gambar.", file=sys.stderr)
                return 1
            kunci = tampil(frame, f"{args.nama}: tekan SPASI untuk mulai", "Buka semua jari, telapak menghadap kamera. ESC untuk keluar.")
            if kunci == 27:
                return 0
            mulai = kunci == 32

        stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
        # countdown, then one photo every `jeda` seconds while the preview keeps running
        jadwal = time.monotonic() + 3.0
        while tersimpan < args.jumlah:
            ok, frame = kamera.read()
            if not ok:
                print("Galat: kamera berhenti mengirim gambar.", file=sys.stderr)
                return 1
            sisa = jadwal - time.monotonic()
            if sisa > 0:
                teks = f"Foto {tersimpan + 1}/{args.jumlah} dalam {sisa:0.0f} detik" if sisa >= 0.5 else "Tahan..."
                kunci = tampil(frame, teks, "Geser tangan sedikit dari foto sebelumnya. ESC untuk berhenti.")
                if kunci == 27:
                    break
                continue
            nama_file = tujuan / f"{stempel}_{tersimpan + 1:02d}.jpg"
            cv2.imwrite(str(nama_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])  # unmirrored, like the browser
            tersimpan += 1
            jadwal = time.monotonic() + args.jeda
    finally:
        kamera.release()
        cv2.destroyAllWindows()

    print(f"{tersimpan} foto disimpan di {tujuan}")
    print("Foto ini data biometrik. Folder data_uji tidak ikut git. Hapus setelah pengujian selesai.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
