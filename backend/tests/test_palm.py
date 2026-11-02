from pathlib import Path
from types import SimpleNamespace

import numpy as np

import palm

FIX = Path(__file__).parent / "fixtures"


def titik_tiruan(titik_px, w, h):
    """21 normalized landmarks; points not listed copy landmark 0."""
    base = titik_px[0]
    lm = [SimpleNamespace(x=base[0] / w, y=base[1] / h, z=0.0) for _ in range(21)]
    for i, (x, y) in titik_px.items():
        lm[i] = SimpleNamespace(x=x / w, y=y / h, z=0.0)
    return lm


def test_kode_sama_dengan_versi_lama():
    roi = np.load(FIX / "roi_test.npy")
    assert np.array_equal(palm.hitung_kode(roi), np.load(FIX / "code_golden.npy"))


def test_kode_detail_konsisten():
    roi = np.load(FIX / "roi_test.npy")
    d = palm.hitung_kode_detail(roi)
    assert d["respons"].shape == (6, 128, 128) and d["clahe"].dtype == np.uint8
    assert np.array_equal(d["kode"], palm.hitung_kode(roi))


def test_jarak_diri_nol_acak_setengah():
    rng = np.random.default_rng(1)
    a = rng.integers(0, 6, (128, 128), dtype=np.uint8)
    b = rng.integers(0, 6, (128, 128), dtype=np.uint8)
    assert palm.jarak_kode(a, a) == 0.0
    assert 0.40 < palm.jarak_kode(a, b) < 0.55


def test_roi_dari_landmark_tiruan():
    lm = titik_tiruan({0: (320, 420), 5: (360, 300), 17: (272, 312)}, 640, 480)
    d = palm.ambil_roi_detail(np.zeros((480, 640, 3), np.uint8), lm)
    assert d["roi"].shape == (128, 128) and isinstance(d["sudut"], float)
    assert d["rot"].shape == (480, 640, 3) and len(d["kotak"]) == 4


def test_roi_none_jika_terlalu_kecil():
    lm = titik_tiruan({0: (320, 420), 5: (330, 300), 17: (310, 300)}, 640, 480)
    assert palm.ambil_roi(np.zeros((480, 640, 3), np.uint8), lm) is None
