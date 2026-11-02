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
