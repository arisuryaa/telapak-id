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
