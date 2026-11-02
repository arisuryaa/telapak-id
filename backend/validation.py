"""validation.py - hand rules checked on the server: open fingers, palm facing, side, ROI quality."""
import cv2
import numpy as np

AMBANG = {"rasio_jari": 1.1, "rasio_jempol": 0.7,
          "terang_min": 40, "terang_max": 215, "tajam_min": 20.0}

# (fingertip, PIP joint) for index, middle, ring, little finger
PASANGAN_JARI = [(8, 6), (12, 10), (16, 14), (20, 18)]


def _px(lm, i, w, h):
    return np.array([lm[i].x * w, lm[i].y * h])


def sisi_dari_label(label):
    """Map MediaPipe's label on the unmirrored frame to the hand's side."""
    return "kanan" if label == "Left" else "kiri"


def jari_terbuka(lm, w, h):
    """True only if all five fingers are extended."""
    p0 = _px(lm, 0, w, h)
    for ujung, pip in PASANGAN_JARI:
        if np.linalg.norm(_px(lm, ujung, w, h) - p0) <= AMBANG["rasio_jari"] * np.linalg.norm(_px(lm, pip, w, h) - p0):
            return False
    jempol = np.linalg.norm(_px(lm, 4, w, h) - _px(lm, 5, w, h))
    return jempol > AMBANG["rasio_jempol"] * np.linalg.norm(_px(lm, 5, w, h) - _px(lm, 17, w, h))


def menghadap_kamera(lm, sisi, w, h):
    """Palm faces the camera when the cross product of wrist->index and wrist->little
    has the sign expected for that hand (image y points down)."""
    p0 = _px(lm, 0, w, h)
    a = _px(lm, 5, w, h) - p0
    b = _px(lm, 17, w, h) - p0
    z = a[0] * b[1] - a[1] * b[0]
    return z < 0 if sisi == "kanan" else z > 0


def kualitas_roi(roi):
    """Return None if the ROI is usable, otherwise the reason in Indonesian."""
    rata = float(roi.mean())
    if rata < AMBANG["terang_min"]:
        return "Foto terlalu gelap, tambah cahaya"
    if rata > AMBANG["terang_max"]:
        return "Foto terlalu terang"
    if cv2.Laplacian(roi, cv2.CV_64F).var() < AMBANG["tajam_min"]:
        return "Foto kurang jelas, tahan tangan lebih diam"
    return None
