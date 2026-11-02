import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

import palm
from pipeline import analisis, baca_frame
from steps import ke_data_url, susun_langkah

FIX = Path(__file__).parent / "fixtures"
DATA = json.loads((FIX / "landmarks_test.json").read_text())


def lm(nama):
    return [SimpleNamespace(x=x / DATA["lebar"], y=y / DATA["tinggi"], z=0.0) for x, y in DATA[nama]]


def frame_uji():
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
    return cv2.GaussianBlur(noise, (5, 5), 0)


def test_baca_frame_rusak():
    assert baca_frame("data:image/jpeg;base64,bukan-gambar") is None


def test_baca_frame_bolak_balik():
    url = ke_data_url(frame_uji(), ".jpg")
    assert baca_frame(url).shape == (480, 640, 3)


def test_tanpa_tangan():
    a = analisis(frame_uji(), deteksi=lambda f: None)
    assert (a.tahap, a.gagal) == (1, "Tangan tidak terdeteksi")
    assert [l["no"] for l in susun_langkah(a)] == [1]


def test_kepal_ditolak_di_server():
    a = analisis(frame_uji(), deteksi=lambda f: (lm("kepal_kanan"), "Left"))
    assert (a.tahap, a.gagal, a.kode) == (2, "Buka semua jari", None)


def test_punggung_ditolak_di_server():
    a = analisis(frame_uji(), deteksi=lambda f: (lm("punggung_kanan"), "Left"))
    assert a.gagal == "Tunjukkan telapak tangan, bukan punggung tangan"


def test_lengkap_tujuh_langkah_dan_kode_jujur():
    a = analisis(frame_uji(), deteksi=lambda f: (lm("terbuka_kanan"), "Left"))
    assert a.gagal is None and a.sisi == "kanan"
    assert np.array_equal(a.kode, palm.hitung_kode(a.roi_detail["roi"]))
    ls = susun_langkah(a, jarak=[], batas=0.38)
    assert [l["no"] for l in ls] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert len(ls[5]["gambar"]) == 6 and len(ls[6]["legenda"]) == 6
    assert all(g["src"].startswith("data:image/") for l in ls for g in l["gambar"])


def test_analisis_mencatat_log(caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="telapak"):
        analisis(frame_uji(), deteksi=lambda f: (lm("terbuka_kanan"), "Left"))
        analisis(frame_uji(), deteksi=lambda f: (lm("punggung_kanan"), "Left"))
    assert "label=Left sisi=kanan silang=-" in caplog.text
    assert "roi_terang=" in caplog.text and "roi_tajam=" in caplog.text
    assert "hasil=lolos" in caplog.text
    assert "hasil=gagal: Tunjukkan telapak tangan" in caplog.text
