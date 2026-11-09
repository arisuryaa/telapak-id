import base64
import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app import create_app
from steps import ke_data_url

FIX = Path(__file__).parent / "fixtures"
DATA = json.loads((FIX / "landmarks_test.json").read_text())


def lm(nama):
    return [SimpleNamespace(x=x / DATA["lebar"], y=y / DATA["tinggi"], z=0.0) for x, y in DATA[nama]]


def frame_uji():
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
    return cv2.GaussianBlur(noise, (5, 5), 0)


FRAME = ke_data_url(frame_uji(), ".jpg")
ESTADO = {"tangan": "terbuka_kanan"}  # which fixture the fake detector returns


def detektor_palsu(frame):
    if ESTADO["tangan"] is None:
        return None
    return lm(ESTADO["tangan"]), "Left"


@pytest.fixture
def client():
    ESTADO["tangan"] = "terbuka_kanan"
    app = create_app("sqlite://", deteksi=detektor_palsu)
    return app.test_client()


def sampel_valid(client):
    s = client.post("/api/sampel", json={"frame": FRAME}).get_json()
    assert s["valid"]
    return s


def body_daftar(kode, **ubah):
    body = {"nama": "dewa", "umur": 21, "status": "mahasiswa", "sisi": "kanan",
            "persetujuan": True, "kode": [kode] * 8, "sisi_terdeteksi": ["kanan"] * 8}
    body.update(ubah)
    return body


def test_scan_galeri_kosong(client):
    r = client.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()
    assert r["hasil"]["status"] == "tidak_dikenal"
    assert r["hasil"]["pesan"] == "Belum ada yang terdaftar"
    assert [l["no"] for l in r["langkah"]][:7] == [1, 2, 3, 4, 5, 6, 7]


def test_daftar_lalu_dikenali(client):
    s = sampel_valid(client)
    assert s["sisi"] == "kanan"
    assert client.post("/api/orang", json=body_daftar(s["kode"])).status_code == 201
    r = client.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()
    assert r["hasil"]["status"] == "dikenali" and r["hasil"]["nama"] == "dewa"
    assert r["hasil"]["jarak"] == 0.0 and r["langkah"][-1]["no"] == 8


def test_kepal_tidak_pernah_dikenali(client):
    s = sampel_valid(client)
    client.post("/api/orang", json=body_daftar(s["kode"]))
    ESTADO["tangan"] = "kepal_kanan"
    r = client.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()
    assert r["hasil"]["status"] == "gagal" and r["hasil"]["pesan"] == "Buka semua jari"
    assert client.post("/api/sampel", json={"frame": FRAME}).get_json()["valid"] is False


def test_simpan_orang_input_salah(client):
    s = sampel_valid(client)
    salah = [
        body_daftar(s["kode"], persetujuan=False),
        body_daftar(s["kode"], nama=""),
        body_daftar(s["kode"], umur="dua puluh"),
        body_daftar(s["kode"], umur=0),
        body_daftar(s["kode"], umur=121),
        body_daftar(s["kode"], status="presiden"),
        {**body_daftar(s["kode"]), "kode": [s["kode"]] * 7},
        body_daftar(s["kode"], sisi_terdeteksi=["kiri"] * 8),
    ]
    for body in salah:
        assert client.post("/api/orang", json=body).status_code == 400


def test_simpan_telapak_duplikat(client):
    s = sampel_valid(client)
    orang = client.post("/api/orang", json=body_daftar(s["kode"])).get_json()["orang"]
    r = client.post("/api/orang", json=body_daftar(s["kode"], orang_id=orang["id"]))
    assert r.status_code == 409 and r.get_json()["perlu_konfirmasi"] is True
    r = client.post("/api/orang", json=body_daftar(s["kode"], orang_id=orang["id"], ganti=True))
    assert r.status_code == 201
    assert client.get(f"/api/orang/{orang['id']}").get_json()["tangan"] == ["kanan"]


def test_frame_rusak(client):
    assert client.post("/api/scan", json={"frame": "xx"}).status_code == 400


def test_hapus(client):
    s = sampel_valid(client)
    orang = client.post("/api/orang", json=body_daftar(s["kode"])).get_json()["orang"]
    assert client.delete(f"/api/orang/{orang['id']}").status_code == 204
    assert client.get(f"/api/orang/{orang['id']}").status_code == 404
    client.post("/api/orang", json=body_daftar(s["kode"]))
    assert client.delete("/api/orang").get_json() == {"dihapus": 1}


def test_api_mencatat_log(client, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="telapak"):
        s = sampel_valid(client)
        client.post("/api/orang", json=body_daftar(s["kode"]))
        client.post("/api/scan", json={"frame": FRAME, "batas": 0.38})
        client.post("/api/orang", json=body_daftar(s["kode"], umur=0))
    assert "sampel: diterima, sisi=kanan" in caplog.text
    assert "tersimpan: orang_id=1 sisi=kanan" in caplog.text
    assert "scan: dikenali, terdekat dewa (kanan) jarak=0.000" in caplog.text
    assert "POST /api/orang -> 400: Umur harus angka" in caplog.text


def test_pengaturan_dan_skala_berbeda(client):
    assert client.get("/api/pengaturan").get_json()["roi_skala"] == 1.0
    s = sampel_valid(client)
    client.post("/api/orang", json=body_daftar(s["kode"]))
    besar = create_app("sqlite://", deteksi=detektor_palsu, roi_skala=1.3).test_client()
    assert besar.get("/api/pengaturan").get_json()["roi_skala"] == 1.3
    s2 = besar.post("/api/sampel", json={"frame": FRAME}).get_json()
    assert s2["valid"]
    besar.post("/api/orang", json=body_daftar(s2["kode"], nama="lama"))
    # each test app has its own in-memory database; a 1.3x enrollment matches a 1.3x scan
    r = besar.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()
    assert r["hasil"]["status"] == "dikenali"


def test_scan_abaikan_data_bentuk_kotak_lama(tmp_path):
    # A hand enrolled at 1.3x before the box stopped growing past the wrist has the same scale but another shape.
    from sqlalchemy import create_engine, text
    url = f"sqlite:///{tmp_path / 'bentuk.db'}"
    c = create_app(url, deteksi=detektor_palsu, roi_skala=1.3).test_client()
    s = c.post("/api/sampel", json={"frame": FRAME}).get_json()
    c.post("/api/orang", json=body_daftar(s["kode"]))
    assert c.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()["hasil"]["status"] == "dikenali"
    with create_engine(url).begin() as conn:
        conn.execute(text("UPDATE telapak SET roi_bentuk = 1"))
    r = c.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()
    assert r["hasil"]["pesan"] == "Belum ada yang terdaftar dengan metode Canny + arah dan ukuran kotak 1.3×. Daftar ulang dulu."
    assert r["jarak"] == []


def test_scan_abaikan_data_skala_lain(tmp_path):
    url = f"sqlite:///{tmp_path / 'campur.db'}"
    lama = create_app(url, deteksi=detektor_palsu, roi_skala=1.0).test_client()
    s = lama.post("/api/sampel", json={"frame": FRAME}).get_json()
    lama.post("/api/orang", json=body_daftar(s["kode"]))
    baru = create_app(url, deteksi=detektor_palsu, roi_skala=1.3).test_client()
    r = baru.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()
    assert r["hasil"]["status"] == "tidak_dikenal"
    assert r["hasil"]["pesan"] == "Belum ada yang terdaftar dengan metode Canny + arah dan ukuran kotak 1.3×. Daftar ulang dulu."
    assert r["jarak"] == []


def test_pengaturan_menyebut_metode_dan_rentang_batas():
    canny = create_app("sqlite://", deteksi=detektor_palsu, metode="canny").test_client().get("/api/pengaturan").get_json()
    gabor = create_app("sqlite://", deteksi=detektor_palsu, metode="gabor").test_client().get("/api/pengaturan").get_json()
    assert canny["metode"] == "canny" and gabor["metode"] == "gabor"
    assert (gabor["batas_default"], gabor["batas_min"], gabor["batas_maks"]) == (0.38, 0.10, 0.50)
    assert (canny["batas_default"], canny["batas_min"], canny["batas_maks"]) == (0.75, 0.40, 0.95)
    assert gabor["skala_jarak_maks"] == 0.5 and canny["skala_jarak_maks"] == 1.0


def test_metode_tidak_dikenal_ditolak():
    with pytest.raises(ValueError, match="METODE harus"):
        create_app("sqlite://", deteksi=detektor_palsu, metode="sobel")


def test_metode_bawaan_dari_env(monkeypatch, tmp_path):
    monkeypatch.setenv("METODE", "gabor")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'env.db'}")
    app = create_app(deteksi=detektor_palsu)
    assert app.test_client().get("/api/pengaturan").get_json()["metode"] == "gabor"


def test_batas_dijepit_ke_rentang_metode():
    gabor = create_app("sqlite://", deteksi=detektor_palsu, metode="gabor").test_client()
    canny = create_app("sqlite://", deteksi=detektor_palsu, metode="canny").test_client()
    assert gabor.post("/api/scan", json={"frame": FRAME, "batas": 0.9}).get_json()["batas"] == 0.5
    assert canny.post("/api/scan", json={"frame": FRAME, "batas": 0.1}).get_json()["batas"] == 0.4
    assert canny.post("/api/scan", json={"frame": FRAME}).get_json()["batas"] == 0.75  # no value sent: the default


@pytest.mark.parametrize("metode,judul6,judul7,jumlah_gambar6", [
    ("gabor", "Filter Gabor 6 arah", "Competitive Code", 6),
    ("canny", "Canny: blur dan gradien", "Tepi Canny dan arahnya", 2),
])
def test_daftar_dan_scan_dengan_setiap_metode(metode, judul6, judul7, jumlah_gambar6):
    c = create_app("sqlite://", deteksi=detektor_palsu, metode=metode).test_client()
    s = sampel_valid(c)
    assert c.post("/api/orang", json=body_daftar(s["kode"])).status_code == 201
    batas = c.get("/api/pengaturan").get_json()["batas_default"]
    r = c.post("/api/scan", json={"frame": FRAME, "batas": batas}).get_json()
    assert r["hasil"]["status"] == "dikenali" and r["hasil"]["jarak"] == 0.0
    assert r["metode"] == metode and r["skala_maks"] == (0.5 if metode == "gabor" else 1.0)
    langkah = {l["no"]: l for l in r["langkah"]}
    assert langkah[6]["judul"] == judul6 and len(langkah[6]["gambar"]) == jumlah_gambar6
    assert langkah[7]["judul"] == judul7 and len(langkah[7]["legenda"]) == 6
    assert [l["no"] for l in r["langkah"]] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert c.get("/api/orang").get_json()[0]["metode_tangan"] == {"kanan": metode}


def test_scan_abaikan_data_metode_lain_dan_pakai_lagi_saat_kembali(tmp_path):
    url = f"sqlite:///{tmp_path / 'metode.db'}"
    gabor = create_app(url, deteksi=detektor_palsu, metode="gabor").test_client()
    s = gabor.post("/api/sampel", json={"frame": FRAME}).get_json()
    gabor.post("/api/orang", json=body_daftar(s["kode"]))
    canny = create_app(url, deteksi=detektor_palsu, metode="canny").test_client()
    r = canny.post("/api/scan", json={"frame": FRAME}).get_json()
    assert r["hasil"]["status"] == "tidak_dikenal" and r["jarak"] == []
    assert "metode Canny + arah" in r["hasil"]["pesan"] and "Daftar ulang dulu" in r["hasil"]["pesan"]
    # the Gabor hand is still in the database and is used again when the method goes back to Gabor
    lagi = create_app(url, deteksi=detektor_palsu, metode="gabor").test_client()
    assert lagi.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()["hasil"]["status"] == "dikenali"


def test_kode_dengan_nilai_di_luar_rentang_ditolak(client):
    s = sampel_valid(client)
    rusak = base64.b64encode(bytes([9]) * (128 * 128)).decode("ascii")
    assert client.post("/api/orang", json=body_daftar(rusak)).status_code == 400
