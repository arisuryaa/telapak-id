import cv2
import numpy as np

import canny
from test_bandingkan import buat_foto, deteksi_tiruan
from tools import bandingkan_metode as bm


def roi_acak(benih):
    """A 128x128 grey ROI of blurred noise: lots of faint structure, like skin texture."""
    ruis = np.random.default_rng(benih).integers(0, 256, (128, 128), dtype=np.uint8)
    return cv2.GaussianBlur(ruis, (0, 0), 2.0)


def test_peta_tepi_biner_dan_seukuran_roi():
    tepi = canny.peta_tepi(roi_acak(1))
    assert tepi.shape == (128, 128) and tepi.dtype == np.uint8
    assert set(np.unique(tepi)) <= {0, 1} and tepi.sum() > 0


def test_garis_gelap_menjadi_dua_tepi_sejajar():
    roi = np.full((128, 128), 160, np.uint8)
    roi[:, 62:66] = 70  # one dark vertical line
    tepi = canny.peta_tepi(roi, sigma=1.0)
    kolom = np.where(tepi.sum(axis=0) > 20)[0]
    assert kolom.min() < 62 and kolom.max() > 64  # an edge on each side of the line, not one on the line
    assert tepi[:, :55].sum() == 0 and tepi[:, 72:].sum() == 0  # nothing away from the line


def test_roi_rata_tidak_punya_tepi():
    assert canny.peta_tepi(np.full((128, 128), 128, np.uint8)).sum() == 0


def test_jarak_tepi_identik_nol_dan_kosong_satu():
    a = canny.peta_tepi(roi_acak(1))
    assert canny.jarak_tepi(a, a) == 0.0
    assert canny.jarak_tepi(np.zeros_like(a), a) == 1.0 and canny.jarak_tepi(a, np.zeros_like(a)) == 1.0


def test_jarak_tepi_menoleransi_geseran_kecil_tetapi_tidak_pola_lain():
    a = canny.peta_tepi(roi_acak(1))
    geser = np.roll(a, (2, -2), axis=(0, 1))
    lain = canny.peta_tepi(roi_acak(2))
    assert canny.jarak_tepi(a, geser) < 0.02  # a 2 px shift is inside the +-3 px tolerance
    assert canny.jarak_tepi(a, lain) > 0.2


def test_jarak_ke_orang_ambil_sampel_terdekat():
    a, lain = canny.peta_tepi(roi_acak(1)), canny.peta_tepi(roi_acak(2))
    assert canny.jarak_ke_orang(a, [lain, a]) == 0.0
    assert canny.jarak_ke_orang(a, [lain]) > 0.2


def test_arah_tepi_vertikal_dan_horizontal_berbeda():
    tegak = np.full((128, 128), 160, np.uint8)
    tegak[:, 62:66] = 70
    datar = np.full((128, 128), 160, np.uint8)
    datar[62:66, :] = 70
    a, b = canny.peta_tepi_arah(tegak, sigma=1.0), canny.peta_tepi_arah(datar, sigma=1.0)
    arah_a, arah_b = np.unique(a[a > 0]), np.unique(b[b > 0])
    assert len(arah_a) == 1 and len(arah_b) == 1 and arah_a[0] != arah_b[0]  # a vertical and a horizontal line


def test_peta_tepi_arah_sama_dengan_peta_tepi_dengan_label():
    roi = roi_acak(1)
    biasa, arah = canny.peta_tepi(roi), canny.peta_tepi_arah(roi)
    assert np.array_equal(biasa > 0, arah > 0)  # same edges, now with a direction 1..6
    assert arah.max() <= 6 and arah.min() == 0


def test_jarak_tepi_arah_identik_nol_geser_kecil_dan_pola_lain():
    a = canny.peta_tepi_arah(roi_acak(1))
    lain = canny.peta_tepi_arah(roi_acak(2))
    assert canny.jarak_tepi_arah(a, a) == 0.0
    assert canny.jarak_tepi_arah(a, np.roll(a, (2, -2), axis=(0, 1))) < 0.02
    assert canny.jarak_tepi_arah(a, lain) > 0.2
    assert canny.jarak_tepi_arah(np.zeros_like(a), a) == 1.0


def test_arah_membuat_tepi_di_tempat_sama_tetapi_beda_arah_tidak_cocok():
    a = np.zeros((128, 128), np.uint8)
    a[30:100, 60] = 1  # a line, direction bin 1
    sama_posisi_arah_sama = a.copy()
    sama_posisi_arah_lain = np.where(a > 0, 4, 0).astype(np.uint8)  # same pixels, direction bin 4 (90 degrees apart)
    tetangga = np.where(a > 0, 2, 0).astype(np.uint8)  # next bin, 30 degrees apart: still counts as the same line
    biner = lambda m: (m > 0).astype(np.uint8)  # jarak_tepi() expects plain 0/1 edge maps
    assert canny.jarak_tepi(biner(a), biner(sama_posisi_arah_lain)) == 0.0  # plain edges cannot tell them apart
    assert canny.jarak_tepi_arah(a, sama_posisi_arah_sama) == 0.0
    assert canny.jarak_tepi_arah(a, sama_posisi_arah_lain) == 1.0
    assert canny.jarak_tepi_arah(a, tetangga) == 0.0
    # directions wrap: bin 6 is next to bin 1
    assert canny.jarak_tepi_arah(a, np.where(a > 0, 6, 0).astype(np.uint8)) == 0.0


def test_hitung_kode_detail_untuk_halaman_hasil():
    roi = roi_acak(1)
    d = canny.hitung_kode_detail(roi)
    for kunci in ("clahe", "halus", "gradien", "tepi", "kode"):
        assert d[kunci].shape == (128, 128) and d[kunci].dtype == np.uint8
    assert np.array_equal(d["kode"], canny.peta_tepi_arah(roi))  # what is stored is the direction map
    assert np.array_equal(d["tepi"], canny.peta_tepi(roi))
    assert d["gradien"].max() == 255 and d["ambang_rendah"] == canny.RASIO_RENDAH * d["ambang_tinggi"]
    assert d["sigma"] == canny.SIGMA and d["persen"] == canny.PERSEN
    # a flat ROI has no gradient at all: no edges, and no division by zero when scaling the gradient
    rata = canny.hitung_kode_detail(np.full((128, 128), 128, np.uint8))
    assert rata["kode"].sum() == 0 and rata["gradien"].sum() == 0


def test_jarak_ke_orang_arah_memakai_hasil_yang_sama_dengan_jarak_tepi_arah():
    a, lain = canny.peta_tepi_arah(roi_acak(1)), canny.peta_tepi_arah(roi_acak(2))
    assert canny.jarak_ke_orang_arah(a, [lain, a]) == 0.0
    assert canny.jarak_ke_orang_arah(a, [lain]) == canny.jarak_tepi_arah(a, lain)


def test_dprime():
    assert bm.dprime([0.1, 0.2], [0.4, 0.5]) > 5
    assert bm.dprime([0.1, 0.5], [0.1, 0.5]) == 0.0


def test_perbandingan_metode_pada_foto_tiruan(tmp_path):
    buat_foto(tmp_path, "dewa_kanan", 1, 12)
    buat_foto(tmp_path, "budi_kanan", 2, 12)
    ringkasan, info, _ = bm.bandingkan(tmp_path, 1.0, [1.0, 2.0], [92.0], 4, 1, deteksi_tiruan)
    assert [r["metode"] for r in ringkasan] == ["Gabor (aplikasi)", "Canny sigma 1, persen 92", "Canny sigma 2, persen 92"]
    assert info["tangan"] == 2 and info["foto"] == 24 and info["lolos"] == 24
    for r in ringkasan:
        assert r["uji"] == 16 and r["rata_asli"] < r["rata_palsu"] and 0 <= r["eer"] <= 0.5 and r["dprime"] > 0


def test_cetak_lembar_dan_galat(tmp_path, capsys):
    buat_foto(tmp_path, "dewa_kanan", 1, 8)
    buat_foto(tmp_path, "budi_kanan", 2, 8)
    ringkasan, info, hasil = bm.bandingkan(tmp_path, 1.0, [1.5], [92.0], 4, 1, deteksi_tiruan)
    bm.cetak(ringkasan, info)
    keluar = capsys.readouterr().out
    assert "Gabor (aplikasi)" in keluar and "Canny sigma 1.5" in keluar and "PERINGATAN: hanya 8 scan uji" in keluar
    roi, kode = next((r, k) for _, r, k, _ in hasil["dewa_kanan"] if k is not None)
    gambar = bm.lembar(roi, kode, [1.0, 2.0], 92.0)
    assert gambar.shape == (26 + 256, 256 * 5, 3)  # ROI, CLAHE, two Canny maps, Gabor code
    assert bm.main([str(tmp_path / "tidak_ada")]) == 1
