"""metode.py - the two ways the app turns an ROI into a pattern and compares patterns.

  canny: Canny edge map that keeps the direction of each edge pixel (canny.py). Values 0..6.
  gabor: the competitive code of 6 Gabor filters (palm.py). Values 0..5.

Both give a 128x128 uint8 array, so the database stores them the same way, but codes made by one method
can never be compared with codes from the other. The method is stored with every enrolled hand
(telapak.metode) and a scan only looks at hands made with the active method.

Switch with METODE in backend/.env, then restart the backend. Hands enrolled with the other method are
kept and are used again when you switch back.

The two distances are on different scales: random Gabor codes sit near 0.5, Canny maps near 0.8 and up.
That is why each method has its own default threshold and slider range.
"""
import canny
import palm

METODE = ("canny", "gabor")
METODE_DEFAULT = "canny"

# batas_default: picked from tools/bandingkan_metode.py on 2 hands and about 30 scans, so treat it as a
# starting point and tune it on more data. For Gabor it is the value the app always used.
PENGATURAN = {
    "gabor": {"nama": "Gabor", "batas_default": 0.38, "batas_min": 0.10, "batas_maks": 0.50, "skala_jarak_maks": 0.5},
    "canny": {"nama": "Canny + arah", "batas_default": 0.75, "batas_min": 0.40, "batas_maks": 0.95, "skala_jarak_maks": 1.0},
}


def periksa(metode):
    """Return the method name if it is a known one, otherwise raise ValueError."""
    if metode not in METODE:
        raise ValueError(f"METODE harus salah satu dari {', '.join(METODE)}, bukan {metode!r}")
    return metode


def pengaturan(metode):
    return PENGATURAN[periksa(metode)]


def hitung_kode_detail(metode, roi_gray):
    """The pattern of an ROI plus the intermediate images, as {"clahe", "kode", ...}."""
    if periksa(metode) == "canny":
        return canny.hitung_kode_detail(roi_gray)
    return palm.hitung_kode_detail(roi_gray)


def jarak_ke_orang(metode, kode, daftar_kode):
    """Distance from a scan to one hand: the distance to its closest enrolled sample."""
    if periksa(metode) == "canny":
        return canny.jarak_ke_orang_arah(kode, daftar_kode)
    return palm.jarak_ke_orang(kode, daftar_kode)
