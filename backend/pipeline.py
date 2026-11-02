"""pipeline.py - decode one frame and run the recognition steps in order.

The steps stop at the first check that fails and record which step it was,
so the results page can show exactly how far the photo got.
"""
import base64
from dataclasses import dataclass

import cv2
import numpy as np

import palm
from validation import jari_terbuka, kualitas_roi, menghadap_kamera, sisi_dari_label


def baca_frame(data_url):
    """Decode a data URL or plain base64 JPEG/PNG into a BGR image, or None."""
    try:
        data = base64.b64decode(data_url.split(",", 1)[-1], validate=True)
    except (ValueError, TypeError):
        return None
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


@dataclass
class Analisis:
    frame: np.ndarray
    lm: list = None
    label: str = None
    sisi: str = None
    roi_detail: dict = None
    kode_detail: dict = None
    tahap: int = 1          # last step reached (1..7)
    gagal: str = None       # reason the photo was rejected, if any

    @property
    def kode(self):
        return None if self.kode_detail is None else self.kode_detail["kode"]


def analisis(frame_bgr, deteksi=palm.deteksi_tangan):
    """Run steps 1-7 on one frame. `deteksi` is injectable for tests."""
    a = Analisis(frame=frame_bgr)
    hasil = deteksi(frame_bgr)
    if hasil is None:
        a.gagal = "Tangan tidak terdeteksi"
        return a
    a.lm, a.label = hasil
    a.sisi = sisi_dari_label(a.label)
    a.tahap = 2
    h, w = frame_bgr.shape[:2]
    if not jari_terbuka(a.lm, w, h):
        a.gagal = "Buka semua jari"
        return a
    if not menghadap_kamera(a.lm, a.sisi, w, h):
        a.gagal = "Tunjukkan telapak tangan, bukan punggung tangan"
        return a
    a.roi_detail = palm.ambil_roi_detail(frame_bgr, a.lm)
    if a.roi_detail is None:
        a.gagal = "Tangan terlalu dekat/jauh atau keluar dari bingkai"
        return a
    a.tahap = 4
    a.gagal = kualitas_roi(a.roi_detail["roi"])
    if a.gagal:
        return a
    a.tahap = 7
    a.kode_detail = palm.hitung_kode_detail(a.roi_detail["roi"])
    return a
