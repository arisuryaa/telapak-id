import numpy as np
import pytest
from sqlalchemy.orm import Session

from db import (DatabaseTidakTersedia, TelapakSudahAda, ambil_orang, buat_engine,
                hapus_orang, hapus_semua, muat_galeri, simpan_telapak, tambah_orang)

KODE = np.random.default_rng(0).integers(0, 6, (8, 128, 128), dtype=np.uint8)


@pytest.fixture
def s():
    engine = buat_engine("sqlite://")
    with Session(engine) as sess:
        yield sess


def test_simpan_muat_kode_utuh(s):
    o = tambah_orang(s, "dewa", 21, "mahasiswa")
    simpan_telapak(s, o.id, "kanan", KODE)
    s.commit()
    g = muat_galeri(s)
    assert len(g) == 1 and g[0]["sisi"] == "kanan" and g[0]["nama"] == "dewa"
    assert np.array_equal(g[0]["kode"], KODE)


def test_duplikat_dan_ganti(s):
    o = tambah_orang(s, "dewa", 21, "mahasiswa")
    simpan_telapak(s, o.id, "kanan", KODE)
    with pytest.raises(TelapakSudahAda):
        simpan_telapak(s, o.id, "kanan", KODE)
    baru = np.zeros_like(KODE)
    simpan_telapak(s, o.id, "kanan", baru, ganti=True)
    s.commit()
    assert np.array_equal(muat_galeri(s)[0]["kode"], baru)


def test_dua_tangan_satu_orang(s):
    o = tambah_orang(s, "dewa", 21, "mahasiswa")
    simpan_telapak(s, o.id, "kiri", KODE)
    simpan_telapak(s, o.id, "kanan", KODE)
    s.commit()
    assert ambil_orang(s, o.id)["tangan"] == ["kanan", "kiri"]


def test_hapus_kaskade(s):
    o = tambah_orang(s, "dewa", 21, "mahasiswa")
    simpan_telapak(s, o.id, "kanan", KODE)
    tambah_orang(s, "budi", 30, "dosen")
    s.commit()
    assert hapus_orang(s, o.id) is True
    s.commit()
    assert muat_galeri(s) == []
    assert hapus_semua(s) == 1
    s.commit()


def test_engine_mysql_mati():
    with pytest.raises(DatabaseTidakTersedia, match="Laragon"):
        buat_engine("mysql+pymysql://root:@127.0.0.1:1/telapak_id")


def test_url_server_tanpa_database():
    from sqlalchemy.engine import make_url
    from db import _url_server
    u = _url_server(make_url("mysql+pymysql://root:@localhost:3306/telapak_id"))
    assert u.database is None
    assert (u.host, u.port, u.username) == ("localhost", 3306, "root")


def test_pesan_galat_menyertakan_detail():
    with pytest.raises(DatabaseTidakTersedia, match="Detail:"):
        buat_engine("mysql+pymysql://root:@127.0.0.1:1/telapak_id")


def test_skala_roi_tersimpan(s):
    o = tambah_orang(s, "dewa", 21, "mahasiswa")
    simpan_telapak(s, o.id, "kanan", KODE, roi_skala=1.3)
    simpan_telapak(s, o.id, "kiri", KODE)
    s.commit()
    skala = {g["sisi"]: g["roi_skala"] for g in muat_galeri(s)}
    assert skala == {"kanan": 1.3, "kiri": 1.0}
    assert ambil_orang(s, o.id)["skala_tangan"] == {"kanan": 1.3, "kiri": 1.0}


def test_migrasi_kolom_skala(tmp_path):
    # A database created before this column existed gets it added on startup.
    import sqlite3
    from sqlalchemy import inspect
    path = tmp_path / "lama.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE orang (id INTEGER PRIMARY KEY, nama VARCHAR(100), umur INTEGER, status VARCHAR(9), dibuat_pada DATETIME)")
    con.execute("CREATE TABLE telapak (id INTEGER PRIMARY KEY, orang_id INTEGER, sisi VARCHAR(5), kode BLOB, dibuat_pada DATETIME)")
    con.execute("INSERT INTO orang VALUES (1, 'lama', 30, 'dosen', '2026-11-01 10:00:00')")
    con.execute("INSERT INTO telapak VALUES (1, 1, 'kanan', ?, '2026-11-01 10:00:00')", (KODE.tobytes(),))
    con.commit(); con.close()
    engine = buat_engine(f"sqlite:///{path}")
    kolom = [c["name"] for c in inspect(engine).get_columns("telapak")]
    assert "roi_skala" in kolom and "roi_bentuk" in kolom and "metode" in kolom
    with Session(engine) as sess:
        g = muat_galeri(sess)[0]
        assert g["roi_skala"] == 1.0 and g["roi_bentuk"] == 1  # old rows count as the original box shape
        assert g["metode"] == "gabor"  # and as Gabor, the only method that existed


def test_bentuk_kotak_tersimpan_dan_diganti(s):
    o = tambah_orang(s, "dewa", 21, "mahasiswa")
    simpan_telapak(s, o.id, "kanan", KODE, roi_skala=1.3, roi_bentuk=2)
    s.commit()
    assert muat_galeri(s)[0]["roi_bentuk"] == 2
    simpan_telapak(s, o.id, "kanan", KODE, ganti=True, roi_skala=1.0, roi_bentuk=1)
    s.commit()
    assert muat_galeri(s)[0]["roi_bentuk"] == 1


def test_metode_tersimpan_dan_diganti(s):
    o = tambah_orang(s, "dewa", 21, "mahasiswa")
    simpan_telapak(s, o.id, "kanan", KODE)
    s.commit()
    assert muat_galeri(s)[0]["metode"] == "gabor"  # the default
    simpan_telapak(s, o.id, "kanan", KODE, ganti=True, metode="canny")
    s.commit()
    assert muat_galeri(s)[0]["metode"] == "canny"
    assert ambil_orang(s, o.id)["metode_tangan"] == {"kanan": "canny"}
