import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from validation import jari_terbuka, kualitas_roi, menghadap_kamera, sisi_dari_label

FIX = Path(__file__).parent / "fixtures"
DATA = json.loads((FIX / "landmarks_test.json").read_text())
W, H = DATA["lebar"], DATA["tinggi"]


def lm(nama):
    return [SimpleNamespace(x=x / W, y=y / H, z=0.0) for x, y in DATA[nama]]


def test_sisi_dari_label():
    assert sisi_dari_label("Left") == "kanan" and sisi_dari_label("Right") == "kiri"


def test_tangan_terbuka_lolos():
    assert jari_terbuka(lm("terbuka_kanan"), W, H)


def test_tangan_mengepal_ditolak():
    assert not jari_terbuka(lm("kepal_kanan"), W, H)


def test_telapak_vs_punggung():
    assert menghadap_kamera(lm("terbuka_kanan"), "kanan", W, H)
    assert not menghadap_kamera(lm("punggung_kanan"), "kanan", W, H)
    assert menghadap_kamera(lm("punggung_kanan"), "kiri", W, H)


def test_kualitas_roi():
    assert kualitas_roi(np.full((128, 128), 10, np.uint8)) == "Foto terlalu gelap, tambah cahaya"
    assert kualitas_roi(np.full((128, 128), 250, np.uint8)) == "Foto terlalu terang"
    assert kualitas_roi(np.full((128, 128), 128, np.uint8)) == "Foto kurang jelas, tahan tangan lebih diam"
    assert kualitas_roi(np.load(FIX / "roi_test.npy")) is None


def roi_telapak_halus(seed=3):
    """Smooth skin with faint palm lines, like a real webcam ROI (low raw sharpness)."""
    import cv2  # noqa: F401
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:128, 0:128].astype(np.float32)
    img = 175 + 8 * np.sin(x / 37) + 6 * np.cos(y / 29)
    for a, b, c in [(1, -0.6, -20), (0.3, -1, 60), (1, 0.9, -150), (-0.4, -1, 100)]:
        d = np.abs(a * x + b * y + c) / np.hypot(a, b)
        img -= 10 * np.exp(-d ** 2 / 3)
    img += rng.normal(0, 0.8, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def test_telapak_halus_lolos():
    # A real palm ROI was rejected because sharpness was measured before CLAHE.
    assert kualitas_roi(roi_telapak_halus()) is None


def test_telapak_buram_ditolak():
    import cv2
    buram = cv2.GaussianBlur(roi_telapak_halus(), (0, 0), 3)
    assert kualitas_roi(buram) == "Foto kurang jelas, tahan tangan lebih diam"


def test_telapak_terang_tanpa_terpotong_lolos():
    # Bright lighting (mean ~220) with no clipped pixels still shows the lines.
    terang = np.clip(roi_telapak_halus().astype(np.int16) + 45, 0, 255).astype(np.uint8)
    assert terang.mean() > 215 and (terang >= 250).mean() < 0.05
    assert kualitas_roi(terang) is None


def test_telapak_terpotong_putih_ditolak():
    # Overexposed: most pixels are clipped to white and the lines are gone.
    roi = roi_telapak_halus().astype(np.int16) + 120
    assert kualitas_roi(np.clip(roi, 0, 255).astype(np.uint8)) == "Foto terlalu terang"
