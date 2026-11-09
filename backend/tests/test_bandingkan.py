import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from tools import bandingkan_skala as bs

FIX = Path(__file__).parent / "fixtures"
DATA = json.loads((FIX / "landmarks_test.json").read_text())


def deteksi_tiruan(frame):
    """Always the same open right hand, whatever the photo shows."""
    titik = [SimpleNamespace(x=x / DATA["lebar"], y=y / DATA["tinggi"], z=0.0) for x, y in DATA["terbuka_kanan"]]
    return titik, "Left"


def buat_foto(folder, nama, benih, jumlah, mulai=0):
    """A fake hand: one fixed textured picture per hand, plus a 1 px shift and fresh noise per photo."""
    dasar = cv2.GaussianBlur(np.random.default_rng(benih).integers(0, 256, (480, 640, 3), dtype=np.uint8), (5, 5), 0)
    tujuan = folder / nama
    tujuan.mkdir(parents=True, exist_ok=True)
    for i in range(mulai, mulai + jumlah):
        rng = np.random.default_rng(10_000 + benih * 100 + i)
        img = np.roll(dasar, tuple(int(v) for v in rng.integers(-1, 2, 2)), axis=(0, 1)).astype(float)
        img = np.clip(img + rng.normal(0, 4, img.shape), 0, 255).astype(np.uint8)
        cv2.imwrite(str(tujuan / f"{i:02d}.png"), img)


def test_tingkat_salah_dan_batas_terbaik():
    asli, palsu = [0.1, 0.2, 0.3], [0.4, 0.45, 0.5]
    assert bs.tingkat_salah(asli, palsu, 0.35) == (0.0, 0.0)
    assert bs.tingkat_salah(asli, palsu, 0.25) == (0.0, pytest.approx(1 / 3))  # one genuine scan rejected
    assert bs.tingkat_salah(asli, palsu, 0.42) == (pytest.approx(1 / 3), 0.0)  # one impostor accepted
    batas, eer = bs.batas_terbaik(asli, palsu)
    assert eer == 0.0
    assert 0.33 < batas < 0.37  # the middle of the perfect range (0.3, 0.4], not its edge


def test_batas_terbaik_untuk_jarak_di_atas_setengah():
    asli, palsu = [0.55, 0.6, 0.65], [0.8, 0.85, 0.9]
    _, eer_sempit = bs.batas_terbaik(asli, palsu)  # the default range stops at 0.5, so it cannot see the gap
    assert eer_sempit > 0.4
    batas, eer = bs.batas_terbaik(asli, palsu, (0.5, 1.0), 0.005)
    assert eer == 0.0 and 0.65 < batas < 0.8


def test_batas_terbaik_pada_data_yang_tumpang_tindih():
    asli = [0.2, 0.25, 0.3, 0.36, 0.42]
    palsu = [0.33, 0.4, 0.45, 0.48, 0.5]
    batas, eer = bs.batas_terbaik(asli, palsu)
    assert 0.0 < eer < 0.5 and 0.2 < batas < 0.5


def test_baca_kelas_mengurutkan_dan_mengabaikan_folder_kosong(tmp_path):
    buat_foto(tmp_path, "b_kanan", 1, 3)
    buat_foto(tmp_path, "a_kanan", 2, 2)
    (tmp_path / "kosong").mkdir()
    (tmp_path / "a_kanan" / "catatan.txt").write_text("bukan foto")
    kelas = bs.baca_kelas(tmp_path)
    assert list(kelas) == ["a_kanan", "b_kanan"]
    assert [p.name for p in kelas["b_kanan"]] == ["00.png", "01.png", "02.png"]


def test_folder_tidak_ada(tmp_path, capsys):
    with pytest.raises(ValueError, match="Folder tidak ditemukan"):
        bs.baca_kelas(tmp_path / "tidak_ada")
    assert bs.main([str(tmp_path / "tidak_ada")]) == 1
    assert "Galat:" in capsys.readouterr().err


def test_satu_tangan_saja_ditolak(tmp_path):
    buat_foto(tmp_path, "dewa_kanan", 1, 12)
    with pytest.raises(ValueError, match="minimal 2 folder"):
        bs.bandingkan(tmp_path, [1.0], 4, deteksi=deteksi_tiruan)


def test_tangan_sama_lebih_dekat_daripada_orang_lain(tmp_path):
    buat_foto(tmp_path, "dewa_kanan", 1, 12)
    buat_foto(tmp_path, "budi_kanan", 2, 12)
    ringkasan, info = bs.bandingkan(tmp_path, [1.0, 1.3], jumlah_daftar=4, deteksi=deteksi_tiruan)
    assert info["tangan"] == 2 and info["foto"] == 24 and info["bersama"] == 24
    assert [r["skala"] for r in ringkasan] == [1.0, 1.3]
    for r in ringkasan:
        assert r["lolos"] == r["foto"] == 24 and r["uji"] == 16 and r["tangan"] == 2
        assert r["rata_asli"] < r["rata_palsu"] and r["selisih"] > 0.1
        assert r["benar"] >= 0.9
        assert 0 <= r["eer"] <= 0.5


def test_foto_dihitung_dari_pendaftaran_lalu_uji(tmp_path):
    # 5 photos per hand, 4 enroll it, so each hand is scanned once; two hands give 2 scans
    buat_foto(tmp_path, "dewa_kanan", 1, 5)
    buat_foto(tmp_path, "budi_kanan", 2, 5)
    ringkasan, _ = bs.bandingkan(tmp_path, [1.0], jumlah_daftar=4, deteksi=deteksi_tiruan)
    assert ringkasan[0]["uji"] == 2


def test_tangan_dengan_foto_kurang_dilewati(tmp_path):
    buat_foto(tmp_path, "dewa_kanan", 1, 8)
    buat_foto(tmp_path, "budi_kanan", 2, 3)  # not enough to enroll 4 and still scan
    ringkasan, _ = bs.bandingkan(tmp_path, [1.0], jumlah_daftar=4, deteksi=deteksi_tiruan)
    assert ringkasan[0]["tangan"] == 1
    assert "eer" not in ringkasan[0]  # no other hand to compare against, so no impostor scores


def test_foto_rusak_dihitung_gagal(tmp_path):
    buat_foto(tmp_path, "dewa_kanan", 1, 6)
    buat_foto(tmp_path, "budi_kanan", 2, 6)
    (tmp_path / "dewa_kanan" / "99.jpg").write_text("bukan gambar")
    ringkasan, info = bs.bandingkan(tmp_path, [1.0], jumlah_daftar=3, deteksi=deteksi_tiruan)
    assert ringkasan[0]["foto"] == 13 and ringkasan[0]["lolos"] == 12
    assert info["bersama"] == 12  # the broken file is never used for scores


def test_alasan_foto_ditolak_dilaporkan(tmp_path, capsys):
    buat_foto(tmp_path, "dewa_kanan", 1, 6)
    buat_foto(tmp_path, "budi_kanan", 2, 6)
    for nama in ("dewa_kanan", "budi_kanan"):
        cv2.imwrite(str(tmp_path / nama / "99.png"), np.zeros((480, 640, 3), np.uint8))  # a black photo
    ringkasan, info = bs.bandingkan(tmp_path, [1.0], jumlah_daftar=3, deteksi=deteksi_tiruan)
    assert ringkasan[0]["gagal"] == {"Foto terlalu gelap, tambah cahaya": 2}
    assert len(info["ditolak"]) == 2 and info["ditolak"][0][1] == "Foto terlalu gelap, tambah cahaya"
    bs.cetak(ringkasan, info)
    keluar = capsys.readouterr().out
    assert "ditolak pada ukuran 1.0x (2 dari 14)" in keluar and "Foto terlalu gelap" in keluar
    assert "--detail" in keluar and "PERINGATAN: hanya 6 scan uji" in keluar
    bs.cetak(ringkasan, info, detail=True)
    assert "99.png  ->  Foto terlalu gelap" in capsys.readouterr().out


def test_cetak_dan_csv(tmp_path, capsys):
    buat_foto(tmp_path, "dewa_kanan", 1, 8)
    buat_foto(tmp_path, "budi_kanan", 2, 8)
    ringkasan, info = bs.bandingkan(tmp_path, [1.0, 1.2], jumlah_daftar=4, deteksi=deteksi_tiruan)
    bs.cetak(ringkasan, info)
    keluar = capsys.readouterr().out
    assert "2 tangan, 16 foto" in keluar and "EER terendah" in keluar and "1.2x" in keluar
    assert "hampir sama untuk 1.0x, 1.2x" in keluar  # both sizes separate the fake hands perfectly: no winner
    csv_path = tmp_path / "hasil.csv"
    bs.simpan_csv(ringkasan, csv_path)
    baris = csv_path.read_text(encoding="utf-8").splitlines()
    assert baris[0].startswith("skala,lolos,foto") and len(baris) == 3
