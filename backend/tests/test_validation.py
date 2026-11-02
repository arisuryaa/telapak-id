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
