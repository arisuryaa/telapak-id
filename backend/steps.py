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


_WARNA_GARIS = (0, 190, 255)  # BGR amber, the line between the two finger bases


def _gambar_sebelum_diluruskan(frame, detail):
    """The original photo with the ROI box and the finger-base line drawn where they really are.

    The box is cut from the rotated photo, so its corners are mapped back through the
    inverse of the rotation to show where that region sits on the photo before it was rotated.
    """
    x1, y1, x2, y2 = detail["kotak"]
    pojok_lurus = np.array([[[x1, y1], [x2, y1], [x2, y2], [x1, y2]]], np.float32)
    asli = cv2.transform(pojok_lurus, cv2.invertAffineTransform(detail["putar"]))[0]
    out = frame.copy()
    cv2.polylines(out, [np.round(asli).astype(np.int32)], True, (0, 255, 0), 3)
    cv2.line(out, tuple(int(v) for v in detail["p5"]), tuple(int(v) for v in detail["p17"]), _WARNA_GARIS, 3)
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
        sebelum = _gambar_sebelum_diluruskan(a.frame, a.roi_detail)
        atas, bawah = palm.batas_vertikal(a.roi_skala)
        tinggi = bawah - atas
        # the same ruler line (index base to little-finger base) on the rotated photo: now horizontal
        M = a.roi_detail["putar"]
        p5r = tuple(int(v) for v in M @ np.array([*a.roi_detail["p5"], 1.0]))
        p17r = tuple(int(v) for v in M @ np.array([*a.roi_detail["p17"], 1.0]))
        cv2.line(diluruskan, p5r, p17r, _WARNA_GARIS, 3)
        langkah.append({
            "no": 3, "judul": "Telapak diluruskan",
            "penjelasan": ("Foto diputar sampai garis pangkal jari (garis kuning, dari pangkal telunjuk ke pangkal "
                           "kelingking) mendatar, lalu kotak telapak (hijau) dipotong dari foto yang sudah lurus. "
                           "Gambar kiri menunjukkan di mana kotak itu berada pada foto asli."),
            "gambar": [
                {"label": "Sebelum diluruskan", "src": ke_data_url(sebelum, ".jpg")},
                {"label": "Sesudah diluruskan", "src": ke_data_url(diluruskan, ".jpg")},
            ],
            "angka": {"sudut putar": f"{a.roi_detail['sudut']:.1f}°",
                      "ukuran kotak": f"{a.roi_skala:g}× lebar telapak",
                      "tinggi kotak": f"{tinggi:.2f}× lebar telapak"},
        })
        potongan = a.roi_detail["potongan"]
        langkah.append({
            "no": 4, "judul": "ROI abu-abu",
            "penjelasan": ("Area tengah telapak dipotong dari foto yang sudah lurus (kiri, masih berwarna), "
                           "diubah menjadi abu-abu, lalu diperkecil ke 128×128 (kanan)."),
            "gambar": [
                {"label": "Hasil potongan (berwarna)", "src": ke_data_url(potongan), "halus": True},
                {"label": "Abu-abu 128×128", "src": ke_data_url(a.roi_detail["roi"])},
            ],
            "angka": {"ukuran potongan": f"{potongan.shape[1]}×{potongan.shape[0]}", "ukuran ROI": "128×128"},
        })
    if a.kode_detail is not None:
        clahe = a.kode_detail["clahe"]
        langkah.append({
            "no": 5, "judul": "CLAHE dan normalisasi",
            "penjelasan": "Kontras garis tipis dipertegas agar garis telapak lebih jelas.",
            "gambar": [{"label": "Setelah CLAHE", "src": ke_data_url(clahe)}],
            "angka": {"rata-rata": round(float(clahe.mean()), 1), "simpangan": round(float(clahe.std()), 1)},
        })
        warna = np.array([_hex_ke_bgr(c) for c in WARNA_KODE], np.uint8)
        legenda = [{"arah": LABEL_ARAH[j], "warna": WARNA_KODE[j]} for j in range(6)]
        if a.metode == "canny":
            kd = a.kode_detail
            langkah.append({
                "no": 6, "judul": "Canny: blur dan gradien",
                "penjelasan": ("Foto diperhalus dengan Gaussian blur agar bintik kecil tidak ikut dihitung. Lalu di setiap "
                               "titik dihitung seberapa tajam perubahan terang-gelapnya (gradien Sobel). Terang berarti "
                               "perubahannya tajam, yaitu calon tepi."),
                "gambar": [{"label": "Setelah blur", "src": ke_data_url(kd["halus"])},
                           {"label": "Kekuatan gradien", "src": ke_data_url(kd["gradien"])}],
                "angka": {"sigma blur": kd["sigma"], "ukuran Sobel": "3×3"},
            })
            kode = kd["kode"]
            peta = np.zeros(kode.shape + (3,), np.uint8)
            peta[kode > 0] = warna[kode[kode > 0] - 1]
            jumlah_tepi = int((kode > 0).sum())
            langkah.append({
                "no": 7, "judul": "Tepi Canny dan arahnya",
                "penjelasan": ("Canny menipiskan tepi menjadi garis setebal satu piksel, lalu memilih tepi yang kuat dengan "
                               "dua ambang (ambang rendah hanya dipakai jika tersambung ke tepi yang kuat). Setiap piksel "
                               "tepi diberi warna menurut arah garisnya (6 arah, sama seperti Gabor). Peta arah inilah yang "
                               "disimpan dan dicocokkan."),
                "gambar": [{"label": "Tepi Canny", "src": ke_data_url(kd["tepi"] * 255)},
                           {"label": "Arah tepi", "src": ke_data_url(peta)}],
                "angka": {"ambang tinggi": round(kd["ambang_tinggi"], 1), "ambang rendah": round(kd["ambang_rendah"], 1),
                          "piksel tepi": jumlah_tepi, "kepadatan tepi": f"{100 * jumlah_tepi / kode.size:.1f}%"},
                "legenda": legenda,
            })
        else:
            respons = a.kode_detail["respons"]
            langkah.append({
                "no": 6, "judul": "Filter Gabor 6 arah",
                "penjelasan": "Enam filter Gabor mencari garis ke enam arah. Terang berarti garis searah dengan filter.",
                "gambar": [{"label": LABEL_ARAH[j], "src": ke_data_url(_skala_0_255(respons[j]))}
                           for j in range(palm.GABOR["arah"])],
                "angka": {"ukuran filter": palm.GABOR["ukuran"], "arah": palm.GABOR["arah"]},
            })
            peta = warna[a.kode_detail["kode"]]
            langkah.append({
                "no": 7, "judul": "Competitive Code",
                "penjelasan": "Di tiap piksel, arah dengan respons terkuat menjadi kodenya. Peta inilah yang disimpan dan dicocokkan.",
                "gambar": [{"label": "Peta kode", "src": ke_data_url(peta)}],
                "angka": {"jumlah arah": palm.GABOR["arah"]},
                "legenda": legenda,
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
