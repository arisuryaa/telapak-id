"""palm.py - core recognition: palm ROI extraction and Competitive Code.

The math is unchanged from the terminal version. The *_detail functions
also return the intermediate arrays so the web app can show each step.
"""
import cv2
import numpy as np
import mediapipe as mp

UKURAN = 128  # ROI size in pixels
GABOR = {"ukuran": 21, "sigma": 4.0, "lambd": 10.0, "gamma": 0.5, "arah": 6}

# Static mode: every request is a single still frame, not a video stream.
_hands = mp.solutions.hands.Hands(
    static_image_mode=True, max_num_hands=1, min_detection_confidence=0.6)


def deteksi_tangan(frame_bgr):
    """Return (21 landmarks, MediaPipe handedness label), or None if no hand."""
    hasil = _hands.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    if not hasil.multi_hand_landmarks:
        return None
    label = hasil.multi_handedness[0].classification[0].label
    return hasil.multi_hand_landmarks[0].landmark, label


def ambil_roi_detail(frame_bgr, lm, skala=1.0):
    """Cut the palm ROI and return the intermediate steps, or None if it does not fit.

    skala=1.0 is the journal box (palm width square). A larger value grows the
    box evenly around the same centre to include more of the palm.
    """
    h, w = frame_bgr.shape[:2]
    p5 = np.array([lm[5].x * w, lm[5].y * h])    # index finger base
    p17 = np.array([lm[17].x * w, lm[17].y * h])  # little finger base
    p0 = np.array([lm[0].x * w, lm[0].y * h])    # wrist

    v = p17 - p5
    jarak = float(np.linalg.norm(v))
    if jarak < 40:  # hand too far or too small
        return None
    sudut = np.degrees(np.arctan2(v[1], v[0]))
    pusat = (p5 + p17) / 2

    # Rotate so the p5-p17 line is horizontal (palm always upright)
    M = cv2.getRotationMatrix2D((float(pusat[0]), float(pusat[1])), float(sudut), 1.0)
    rot = cv2.warpAffine(frame_bgr, M, (w, h))
    p0r = M @ np.array([p0[0], p0[1], 1.0])
    arah = 1 if p0r[1] > pusat[1] else -1  # is the wrist below or above the line?

    s = jarak  # palm width; the journal box is s x s
    tambah = 0.5 * (skala - 1)  # 0.0 at skala=1.0, so the journal values stay exact
    y_mulai = pusat[1] + arah * (0.15 - tambah) * s
    y_akhir = pusat[1] + arah * (1.15 + tambah) * s
    y1, y2 = int(min(y_mulai, y_akhir)), int(max(y_mulai, y_akhir))
    x1, x2 = int(pusat[0] - skala * s / 2), int(pusat[0] + skala * s / 2)
    if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
        return None  # box goes outside the image
    potongan = rot[y1:y2, x1:x2]
    if arah == -1:  # normalize orientation
        potongan = cv2.rotate(potongan, cv2.ROTATE_180)
    roi = cv2.cvtColor(potongan, cv2.COLOR_BGR2GRAY)
    return {
        "rot": rot,
        "kotak": (x1, y1, x2, y2),
        "sudut": float(sudut),
        "potongan": potongan.copy(),  # the colour crop, before grey and the resize to 128x128
        "roi": cv2.resize(roi, (UKURAN, UKURAN)),
        # kept so the results page can draw the same box on the photo before it was rotated
        "putar": M,
        "p5": p5,
        "p17": p17,
    }


def ambil_roi(frame_bgr, lm, skala=1.0):
    """Return only the 128x128 grayscale palm ROI, or None."""
    detail = ambil_roi_detail(frame_bgr, lm, skala)
    return None if detail is None else detail["roi"]


def _buat_filter():
    ks = []
    for j in range(GABOR["arah"]):  # 0, 30, 60, 90, 120, 150 degrees
        k = cv2.getGaborKernel((GABOR["ukuran"], GABOR["ukuran"]), sigma=GABOR["sigma"],
                               theta=j * np.pi / 6, lambd=GABOR["lambd"],
                               gamma=GABOR["gamma"], psi=0)
        k -= k.mean()  # remove the overall brightness effect
        ks.append(k.astype(np.float32))
    return ks


_FILTER = _buat_filter()
_CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))


def terapkan_clahe(roi_gray):
    """Contrast enhancement used before the Gabor filters (step 5)."""
    return _CLAHE.apply(roi_gray)


def hitung_kode_detail(roi_gray):
    """Competitive Code plus its intermediate arrays: CLAHE image, 6 Gabor responses, code."""
    clahe = terapkan_clahe(roi_gray)
    g = clahe.astype(np.float32)
    g = (g - g.mean()) / (g.std() + 1e-6)
    respons = np.stack([cv2.filter2D(g, cv2.CV_32F, k) for k in _FILTER])
    kode = np.argmin(respons, axis=0).astype(np.uint8)  # strongest dark line = smallest response
    return {"clahe": clahe, "respons": respons, "kode": kode}


def hitung_kode(roi_gray):
    """Competitive Code: each pixel gets a value 0..5 (the winning direction)."""
    return hitung_kode_detail(roi_gray)["kode"]


def jarak_kode(a, b, geser=3):
    """Angular distance (0 = identical, ~0.5 = random). Small shift tolerance."""
    H, W = a.shape
    a2 = a[geser:H - geser, geser:W - geser].astype(np.int16)
    terbaik = 1.0
    for dy in range(-geser, geser + 1):
        for dx in range(-geser, geser + 1):
            b2 = b[geser + dy:H - geser + dy, geser + dx:W - geser + dx].astype(np.int16)
            d = np.abs(a2 - b2)
            d = np.minimum(d, 6 - d)
            terbaik = min(terbaik, float(d.mean()) / 3.0)
    return terbaik


def jarak_ke_orang(kode, daftar_kode):
    """Distance to one person = distance to their closest enrolled sample."""
    return min(jarak_kode(kode, k) for k in daftar_kode)
