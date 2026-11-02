"""palm.py - fungsi inti: potong ROI telapak, hitung Competitive Code, hitung jarak."""
import cv2
import numpy as np
import mediapipe as mp

UKURAN = 128  # ukuran ROI (piksel)

_hands = mp.solutions.hands.Hands(
    static_image_mode=False, max_num_hands=1,
    min_detection_confidence=0.6, min_tracking_confidence=0.6)


def cari_landmark(frame_bgr):
    """Kembalikan 21 titik tangan (atau None kalau tangan tidak terdeteksi)."""
    hasil = _hands.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    if not hasil.multi_hand_landmarks:
        return None
    return hasil.multi_hand_landmarks[0].landmark


def ambil_roi(frame_bgr, lm):
    """Potong area tengah telapak, diluruskan, ukuran UKURAN x UKURAN (grayscale)."""
    h, w = frame_bgr.shape[:2]
    p5 = np.array([lm[5].x * w, lm[5].y * h])    # pangkal telunjuk
    p17 = np.array([lm[17].x * w, lm[17].y * h])  # pangkal kelingking
    p0 = np.array([lm[0].x * w, lm[0].y * h])    # pergelangan

    v = p17 - p5
    jarak = float(np.linalg.norm(v))
    if jarak < 40:                      # tangan terlalu jauh/kecil
        return None
    sudut = np.degrees(np.arctan2(v[1], v[0]))
    pusat = (p5 + p17) / 2

    # putar gambar supaya garis p5-p17 mendatar (telapak selalu tegak)
    M = cv2.getRotationMatrix2D((float(pusat[0]), float(pusat[1])), float(sudut), 1.0)
    rot = cv2.warpAffine(frame_bgr, M, (w, h))
    p0r = M @ np.array([p0[0], p0[1], 1.0])
    arah = 1 if p0r[1] > pusat[1] else -1   # pergelangan ada di atas/bawah garis?

    s = jarak                                # sisi kotak = lebar telapak
    y_mulai = pusat[1] + arah * 0.15 * s
    y_akhir = pusat[1] + arah * 1.15 * s
    y1, y2 = int(min(y_mulai, y_akhir)), int(max(y_mulai, y_akhir))
    x1, x2 = int(pusat[0] - s / 2), int(pusat[0] + s / 2)
    if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
        return None                          # kotak keluar dari gambar
    roi = rot[y1:y2, x1:x2]
    if arah == -1:                           # samakan orientasi
        roi = cv2.rotate(roi, cv2.ROTATE_180)
    roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    return cv2.resize(roi, (UKURAN, UKURAN))


def _buat_filter():
    ks = []
    for j in range(6):                       # 6 arah: 0,30,60,90,120,150 derajat
        k = cv2.getGaborKernel((21, 21), sigma=4.0, theta=j * np.pi / 6,
                               lambd=10.0, gamma=0.5, psi=0)
        k -= k.mean()                        # buang pengaruh terang-gelap umum
        ks.append(k.astype(np.float32))
    return ks

_FILTER = _buat_filter()
_CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))


def hitung_kode(roi_gray):
    """Competitive Code: tiap piksel diberi angka 0..5 (arah garis pemenang)."""
    g = _CLAHE.apply(roi_gray).astype(np.float32)
    g = (g - g.mean()) / (g.std() + 1e-6)
    resp = np.stack([cv2.filter2D(g, cv2.CV_32F, k) for k in _FILTER])
    return np.argmin(resp, axis=0).astype(np.uint8)   # garis gelap = respons paling kecil


def jarak_kode(a, b, geser=3):
    """Jarak sudut (0 = identik, ~0.5 = acak). Toleransi geser kecil."""
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
    """Jarak ke satu orang = jarak ke foto pendaftarannya yang paling mirip."""
    return min(jarak_kode(kode, k) for k in daftar_kode)
