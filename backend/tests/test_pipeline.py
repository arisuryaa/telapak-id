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


def test_langkah_tiga_menampilkan_kotak_sebelum_dan_sesudah_diluruskan():
    a = analisis(frame_uji(), deteksi=lambda f: (lm("terbuka_kanan"), "Left"))
    langkah3 = susun_langkah(a)[2]
    assert [g["label"] for g in langkah3["gambar"]] == ["Sebelum diluruskan", "Sesudah diluruskan"]
    assert all(g["src"].startswith("data:image/jpeg") for g in langkah3["gambar"])


def test_langkah_empat_menampilkan_potongan_berwarna_sebelum_abu_abu():
    a = analisis(frame_uji(), deteksi=lambda f: (lm("terbuka_kanan"), "Left"))
    langkah4 = susun_langkah(a)[3]
    assert [g["label"] for g in langkah4["gambar"]] == ["Hasil potongan (berwarna)", "Abu-abu 128×128"]
    x1, y1, x2, y2 = a.roi_detail["kotak"]
    assert a.roi_detail["potongan"].shape == (y2 - y1, x2 - x1, 3)  # colour, same size as the box
    assert a.roi_detail["roi"].shape == (128, 128)


def test_kotak_asli_adalah_kotak_lurus_yang_diputar_balik():
    a = analisis(frame_uji(), deteksi=lambda f: (lm("terbuka_kanan"), "Left"))
    d = a.roi_detail
    x1, y1, x2, y2 = d["kotak"]
    pojok = np.array([[[x1, y1], [x2, y1], [x2, y2], [x1, y2]]], np.float32)
    asli = cv2.transform(pojok, cv2.invertAffineTransform(d["putar"]))[0]
    sisi = [float(np.linalg.norm(asli[i] - asli[(i + 1) % 4])) for i in range(4)]
    # rotation keeps the box a rectangle of the same size
    assert abs(sisi[0] - (x2 - x1)) < 1 and abs(sisi[1] - (y2 - y1)) < 1
    # and the rotation maps the finger-base line onto a horizontal line
    p5r, p17r = (d["putar"] @ np.array([*d["p5"], 1.0])), (d["putar"] @ np.array([*d["p17"], 1.0]))
    assert abs(p5r[1] - p17r[1]) < 0.5


def test_metode_tidak_dikenal_ditolak():
    import pytest
    with pytest.raises(ValueError, match="METODE harus"):
        analisis(frame_uji(), deteksi=lambda f: (lm("terbuka_kanan"), "Left"), metode="sobel")


def test_analisis_canny_menghasilkan_peta_arah_dan_dicatat(caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="telapak"):
        a = analisis(frame_uji(), deteksi=lambda f: (lm("terbuka_kanan"), "Left"), metode="canny")
    assert a.gagal is None and a.metode == "canny" and a.kode.shape == (128, 128)
    assert a.kode.max() <= 6 and (a.kode > 0).any()
    assert "metode=canny" in caplog.text
    ls = susun_langkah(a, jarak=[], batas=0.75)
    assert [l["no"] for l in ls] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert [l["judul"] for l in ls[5:7]] == ["Canny: blur dan gradien", "Tepi Canny dan arahnya"]
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


def test_analisis_dengan_skala_roi(caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="telapak"):
        a = analisis(frame_uji(), deteksi=lambda f: (lm("terbuka_kanan"), "Left"), roi_skala=1.3)
    x1, _, x2, _ = a.roi_detail["kotak"]
    assert a.roi_skala == 1.3 and x2 - x1 > 100  # palm width is about 89 px at 1.0x
    assert "roi_skala=1.3" in caplog.text
    langkah3 = susun_langkah(a)[2]
    assert langkah3["angka"]["ukuran kotak"] == "1.3× lebar telapak"
