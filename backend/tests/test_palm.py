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


def test_kotak_skala_satu_sama_dengan_rumus_jurnal():
    # Same box as the original terminal version: s x s, from 0.15s to 1.15s below the knuckles.
    lm = titik_tiruan({0: (320, 420), 5: (360, 300), 17: (272, 312)}, 640, 480)
    frame = np.zeros((480, 640, 3), np.uint8)
    p5, p17 = np.array([360.0, 300.0]), np.array([272.0, 312.0])
    s, pusat = float(np.linalg.norm(p17 - p5)), (p5 + p17) / 2
    d = palm.ambil_roi_detail(frame, lm, skala=1.0)
    x1, y1, x2, y2 = d["kotak"]
    assert (x1, x2) == (int(pusat[0] - s / 2), int(pusat[0] + s / 2))
    assert y2 - y1 in (int(s) - 1, int(s), int(s) + 1)
    assert d["kotak"] == palm.ambil_roi_detail(frame, lm)["kotak"]


def test_kotak_skala_lebih_besar():
    lm = titik_tiruan({0: (320, 420), 5: (360, 300), 17: (272, 312)}, 640, 480)
    frame = np.zeros((480, 640, 3), np.uint8)
    a = palm.ambil_roi_detail(frame, lm, skala=1.0)["kotak"]
    b = palm.ambil_roi_detail(frame, lm, skala=1.3)["kotak"]
    lebar_a, lebar_b = a[2] - a[0], b[2] - b[0]
    assert abs(lebar_b - 1.3 * lebar_a) <= 2
    assert abs((a[0] + a[2]) / 2 - (b[0] + b[2]) / 2) <= 1  # same horizontal centre
    # The photo may be turned upside down, so measure from the finger-base line (y = 306 after rotation).
    dekat_a, jauh_a = _jarak_tepi(a, 306)
    dekat_b, jauh_b = _jarak_tepi(b, 306)
    assert abs(jauh_b - jauh_a) <= 1  # the edge toward the wrist stays put
    assert dekat_b < dekat_a  # the edge toward the fingers moves closer to the finger-base line


def _jarak_tepi(kotak, y_garis):
    """Distance of the near and far edge of the box from the finger-base line, in pixels."""
    return tuple(sorted(abs(y - y_garis) for y in (kotak[1], kotak[3])))


def test_batas_vertikal_dan_versi_bentuk():
    assert palm.batas_vertikal(1.0) == (0.15, 1.15)
    atas, bawah = palm.batas_vertikal(0.8)
    assert abs(atas - 0.25) < 1e-9 and abs(bawah - 1.05) < 1e-9  # smaller boxes still shrink evenly
    assert palm.batas_vertikal(1.3) == (0.0, 1.15)  # top reaches the finger-base line, bottom stays at the wrist
    assert palm.batas_vertikal(1.5) == (0.0, 1.15)
    assert [palm.versi_bentuk(k) for k in (0.8, 1.0, 1.3, 1.5)] == [1, 1, 2, 2]


def test_kotak_besar_tidak_melewati_pergelangan():
    lm = titik_tiruan({0: (320, 420), 5: (360, 300), 17: (272, 312)}, 640, 480)
    frame = np.zeros((480, 640, 3), np.uint8)
    p5, p17 = np.array([360.0, 300.0]), np.array([272.0, 312.0])
    s = float(np.linalg.norm(p17 - p5))
    for k in (1.0, 1.3, 1.5):
        dekat, jauh = _jarak_tepi(palm.ambil_roi_detail(frame, lm, skala=k)["kotak"], 306)
        assert abs(jauh - 1.15 * s) <= 2  # the wrist edge is 1.15 palm widths from the line, whatever the scale
        assert abs(dekat - palm.batas_vertikal(k)[0] * s) <= 2
