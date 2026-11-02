"""steps.py - turn one analysis into the step cards shown on the results page."""
import base64

import cv2
import mediapipe as mp
import numpy as np

import palm

# Colors for directions 0, 30, 60, 90, 120, 150 degrees (hex, shown in the legend)
WARNA_KODE = ["#ef4444", "#f59e0b", "#22c55e", "#06b6d4", "#3b82f6", "#a855f7"]
LABEL_ARAH = ["0°", "30°", "60°", "90°", "120°", "150°"]


def ke_data_url(img, fmt=".png"):
    ok, buf = cv2.imencode(fmt, img)
    if not ok:
        raise ValueError("image could not be encoded")
    mime = "image/jpeg" if fmt == ".jpg" else "image/png"
    return f"data:{mime};base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def _hex_ke_bgr(hex_warna):
    r, g, b = (int(hex_warna[i:i + 2], 16) for i in (1, 3, 5))
    return (b, g, r)


def _skala_0_255(img):
    return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def _gambar_landmark(frame, lm):
    """Draw the hand skeleton and the 21 points on a copy of the frame."""
    h, w = frame.shape[:2]
    out = frame.copy()
    titik = [(int(p.x * w), int(p.y * h)) for p in lm]
    for a, b in mp.solutions.hands.HAND_CONNECTIONS:
        cv2.line(out, titik[a], titik[b], (0, 200, 0), 2)
    for p in titik:
        cv2.circle(out, p, 4, (0, 0, 255), -1)
    return out


def susun_langkah(a, jarak=None, batas=None):
    """Return the step cards for an analysis. Each card is ready for JSON.

    A step appears only when its data exists, so a rejected photo shows the
    steps it got through. Step 8 appears only when `jarak` is given.
    """
    langkah = [{
        "no": 1, "judul": "Foto dari kamera",
        "penjelasan": "Satu frame diambil dari webcam ketika tangan sudah valid.",
        "gambar": [{"label": "Frame asli", "src": ke_data_url(a.frame, ".jpg")}],
        "angka": {"resolusi": f"{a.frame.shape[1]}×{a.frame.shape[0]}"},
    }]
    if a.tahap >= 2:
        langkah.append({
            "no": 2, "judul": "Deteksi tangan",
            "penjelasan": "MediaPipe menemukan 21 titik pada tangan. Garis hijau adalah kerangka tangan.",
            "gambar": [{"label": "21 titik", "src": ke_data_url(_gambar_landmark(a.frame, a.lm), ".jpg")}],
            "angka": {"jumlah titik": 21, "sisi": a.sisi},
        })
    if a.roi_detail is not None:
        x1, y1, x2, y2 = a.roi_detail["kotak"]
        diluruskan = a.roi_detail["rot"].copy()
        cv2.rectangle(diluruskan, (x1, y1), (x2, y2), (0, 255, 0), 3)
        langkah.append({
            "no": 3, "judul": "Telapak diluruskan",
            "penjelasan": "Gambar diputar agar garis pangkal jari mendatar, lalu kotak telapak diambil.",
            "gambar": [{"label": "Diluruskan + kotak ROI", "src": ke_data_url(diluruskan, ".jpg")}],
            "angka": {"sudut putar": f"{a.roi_detail['sudut']:.1f}°"},
        })
        langkah.append({
            "no": 4, "judul": "ROI abu-abu",
            "penjelasan": "Area tengah telapak diubah menjadi abu-abu dan diperkecil ke 128×128.",
            "gambar": [{"label": "ROI", "src": ke_data_url(a.roi_detail["roi"])}],
            "angka": {"ukuran": "128×128"},
        })
    if a.kode_detail is not None:
        clahe = a.kode_detail["clahe"]
        langkah.append({
            "no": 5, "judul": "CLAHE dan normalisasi",
            "penjelasan": "Kontras garis tipis dipertegas agar garis telapak lebih jelas.",
            "gambar": [{"label": "Setelah CLAHE", "src": ke_data_url(clahe)}],
            "angka": {"rata-rata": round(float(clahe.mean()), 1), "simpangan": round(float(clahe.std()), 1)},
        })
        respons = a.kode_detail["respons"]
        langkah.append({
            "no": 6, "judul": "Filter Gabor 6 arah",
            "penjelasan": "Enam filter Gabor mencari garis ke enam arah. Terang berarti garis searah dengan filter.",
            "gambar": [{"label": LABEL_ARAH[j], "src": ke_data_url(_skala_0_255(respons[j]))}
                       for j in range(palm.GABOR["arah"])],
            "angka": {"ukuran filter": palm.GABOR["ukuran"], "arah": palm.GABOR["arah"]},
        })
        warna = np.array([_hex_ke_bgr(c) for c in WARNA_KODE], np.uint8)
        peta = warna[a.kode_detail["kode"]]
        langkah.append({
            "no": 7, "judul": "Competitive Code",
            "penjelasan": "Di tiap piksel, arah dengan respons terkuat menjadi kodenya. Peta inilah yang disimpan dan dicocokkan.",
            "gambar": [{"label": "Peta kode", "src": ke_data_url(peta)}],
            "angka": {"jumlah arah": palm.GABOR["arah"]},
            "legenda": [{"arah": LABEL_ARAH[j], "warna": WARNA_KODE[j]} for j in range(6)],
        })
    if jarak is not None:
        terkecil = min((d["jarak"] for d in jarak), default=None)
        langkah.append({
            "no": 8, "judul": "Pencocokan",
            "penjelasan": "Jarak ke setiap orang terdaftar dibandingkan. Jarak di bawah batas berarti dikenali.",
            "gambar": [],
            "angka": {
                "jarak terkecil": "-" if terkecil is None else round(terkecil, 3),
                "batas": "-" if batas is None else round(batas, 2),
            },
            "jarak": jarak,
        })
    return langkah
