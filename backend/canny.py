"""canny.py - an edge-based alternative to the Gabor competitive code.

The app uses it when METODE=canny (see metode.py). It is also what tools/bandingkan_metode.py compares
with the Gabor code on the same photos. In the app the edge map keeps the direction of every edge pixel
(peta_tepi_arah); the plain 0/1 edge map is what the comparison tool calls "Canny".

Canny turns the ROI into a map of edges (1 on an edge, 0 elsewhere). Unlike the competitive code
it has no direction: a pixel is an edge or it is not. A thin dark palm line usually becomes two
parallel edges, one on each side.

Two edge maps are compared by how many edge pixels of one lie close to an edge pixel of the other:

    precision = share of A's edge pixels that have a B edge within `toleransi` pixels
    recall    = share of B's edge pixels that have an A edge within `toleransi` pixels
    F         = 2 * precision * recall / (precision + recall)
    distance  = 1 - F        (0 = identical, 1 = no edge in common)

The best of the shifts of up to +-3 pixels is taken, as palm.jarak_kode() does. The raw numbers are not
on the same scale as the Gabor distance (random edge maps do not land near 0.5), so compare methods by
EER and d', not by the raw distance.
"""
import cv2
import numpy as np

import palm

SIGMA = 1.5       # blur before Canny; larger removes fine noise and fine lines
PERSEN = 95       # the strongest (100 - PERSEN)% of gradients count as strong edges
TOLERANSI = 1     # how many pixels apart two edges may be and still count as the same edge
RASIO_RENDAH = 0.4  # the low (hysteresis) threshold is this fraction of the high one


def _hitung(roi_gray, sigma, persen):
    """Every intermediate of the Canny path: (CLAHE, blurred, gradient strength, edge map 0/1, thresholds).

    The same CLAHE step as the Gabor path runs first, so both methods see the same contrast. The
    thresholds follow the image: the high threshold is the `persen` percentile of the gradient
    strength and the low threshold is RASIO_RENDAH times that, so a pale photo and a contrasty one
    give a similar amount of edges.
    """
    clahe = palm.terapkan_clahe(roi_gray)
    halus = cv2.GaussianBlur(clahe, (0, 0), sigma) if sigma > 0 else clahe
    gx = cv2.Sobel(halus, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(halus, cv2.CV_32F, 0, 1, ksize=3)
    kuat = np.abs(gx) + np.abs(gy)
    tinggi = float(np.percentile(kuat, persen))
    if tinggi <= 0:
        tepi = np.zeros(halus.shape, np.uint8)
    else:
        tepi = (cv2.Canny(halus, RASIO_RENDAH * tinggi, tinggi) > 0).astype(np.uint8)
    return clahe, halus, gx, gy, kuat, tepi, tinggi


def peta_tepi(roi_gray, sigma=SIGMA, persen=PERSEN):
    """Canny edge map (uint8, 0 or 1) of a 128x128 grey ROI."""
    return _hitung(roi_gray, sigma, persen)[5]


def jarak_tepi(a, b, geser=3, toleransi=TOLERANSI):
    """Distance between two edge maps (0 = identical, 1 = nothing in common)."""
    inti = np.ones((2 * toleransi + 1, 2 * toleransi + 1), np.uint8)
    da, db = cv2.dilate(a, inti), cv2.dilate(b, inti)
    H, W = a.shape
    pusat = (slice(geser, H - geser), slice(geser, W - geser))
    terbaik = 1.0
    for dy in range(-geser, geser + 1):
        for dx in range(-geser, geser + 1):
            geser_b = (slice(geser + dy, H - geser + dy), slice(geser + dx, W - geser + dx))
            na, nb = int(a[pusat].sum()), int(b[geser_b].sum())
            if na == 0 or nb == 0:
                continue
            presisi = int((a[pusat] & db[geser_b]).sum()) / na
            recall = int((b[geser_b] & da[pusat]).sum()) / nb
            if presisi + recall == 0:
                continue
            terbaik = min(terbaik, 1.0 - 2 * presisi * recall / (presisi + recall))
    return terbaik


def jarak_ke_orang(peta, daftar_peta, toleransi=TOLERANSI):
    """Distance to one hand = distance to its closest enrolled edge map (like palm.jarak_ke_orang)."""
    return min(jarak_tepi(peta, p, toleransi=toleransi) for p in daftar_peta)


# --- Canny with edge direction -------------------------------------------------------------------
# Canny already computes the gradient direction at every pixel (it needs it to thin the edges). Keeping
# that direction gives each edge pixel a label, the same idea as the 6 directions of the competitive code.

JUMLAH_ARAH = 6


def _beri_arah(gx, gy, tepi):
    """Direction label of every edge pixel: 0 = no edge, 1..6 = direction.

    The edge itself runs perpendicular to the gradient, so the direction of the line is the gradient
    angle plus 90 degrees. Lines are unsigned (a line at 10 and at 190 degrees is the same line), so the
    angle is folded into 0..180 and cut into 6 bins of 30 degrees.
    """
    sudut_garis = (np.degrees(np.arctan2(gy, gx)) + 90.0) % 180.0
    arah = np.minimum((sudut_garis / (180.0 / JUMLAH_ARAH)).astype(np.int64), JUMLAH_ARAH - 1)
    return np.where(tepi > 0, arah + 1, 0).astype(np.uint8)


def peta_tepi_arah(roi_gray, sigma=SIGMA, persen=PERSEN):
    """Canny edge map where each edge pixel carries its direction: 0 = no edge, 1..6 = direction."""
    _, _, gx, gy, _, tepi, _ = _hitung(roi_gray, sigma, persen)
    return _beri_arah(gx, gy, tepi)


def hitung_kode_detail(roi_gray, sigma=SIGMA, persen=PERSEN):
    """Canny pattern plus its intermediate images, shaped like palm.hitung_kode_detail().

    "kode" is the direction map that is stored and compared (0 = no edge, 1..6 = direction), the same
    128x128 uint8 shape as the Gabor code. The rest is for the results page: the CLAHE image, the blurred
    image, the gradient strength scaled to 0..255, the Canny edge map (0/1) and the thresholds used.
    """
    clahe, halus, gx, gy, kuat, tepi, tinggi = _hitung(roi_gray, sigma, persen)
    puncak = float(kuat.max())
    return {
        "clahe": clahe, "halus": halus,
        "gradien": (kuat / puncak * 255).astype(np.uint8) if puncak > 0 else np.zeros_like(clahe),
        "tepi": tepi, "kode": _beri_arah(gx, gy, tepi),
        "ambang_tinggi": tinggi, "ambang_rendah": RASIO_RENDAH * tinggi, "sigma": sigma, "persen": persen,
    }


def _dekat_searah(peta, toleransi, selisih):
    """(6, H, W) bool. [d] marks pixels within `toleransi` of an edge whose direction is within `selisih` bins of d."""
    inti = np.ones((2 * toleransi + 1, 2 * toleransi + 1), np.uint8)
    per_arah = np.stack([cv2.dilate((peta == d + 1).astype(np.uint8), inti) for d in range(JUMLAH_ARAH)]).astype(bool)
    hasil = np.zeros_like(per_arah)
    for d in range(JUMLAH_ARAH):
        for s in range(-selisih, selisih + 1):
            hasil[d] |= per_arah[(d + s) % JUMLAH_ARAH]  # directions wrap around: bin 5 is next to bin 0
    return hasil


def jarak_tepi_arah(a, b, geser=3, toleransi=TOLERANSI, selisih=1, sa=None, sb=None):
    """Distance between two direction-labelled edge maps (0 = identical, 1 = nothing in common).

    An edge pixel of one map only counts as matched when the other map has an edge of a similar direction
    (within `selisih` bins, 30 degrees per bin) within `toleransi` pixels. The rest is as in jarak_tepi().
    `sa` and `sb` are the precomputed _dekat_searah() of a and b; passing them saves repeating that work
    when one scan is compared with many enrolled samples.
    """
    sa = _dekat_searah(a, toleransi, selisih) if sa is None else sa
    sb = _dekat_searah(b, toleransi, selisih) if sb is None else sb
    H, W = a.shape
    pusat = (slice(geser, H - geser), slice(geser, W - geser))
    terbaik = 1.0
    for dy in range(-geser, geser + 1):
        for dx in range(-geser, geser + 1):
            geser_b = (slice(geser + dy, H - geser + dy), slice(geser + dx, W - geser + dx))
            ac, bs = a[pusat], b[geser_b]
            ada_a, ada_b = ac > 0, bs > 0
            na, nb = int(ada_a.sum()), int(ada_b.sum())
            if na == 0 or nb == 0:
                continue
            cocok_a = np.take_along_axis(sb[(slice(None),) + geser_b], np.clip(ac.astype(np.int64) - 1, 0, 5)[None], 0)[0] & ada_a
            cocok_b = np.take_along_axis(sa[(slice(None),) + pusat], np.clip(bs.astype(np.int64) - 1, 0, 5)[None], 0)[0] & ada_b
            presisi, recall = int(cocok_a.sum()) / na, int(cocok_b.sum()) / nb
            if presisi + recall == 0:
                continue
            terbaik = min(terbaik, 1.0 - 2 * presisi * recall / (presisi + recall))
    return terbaik


def jarak_ke_orang_arah(peta, daftar_peta, toleransi=TOLERANSI, selisih=1):
    """Distance to one hand = distance to its closest enrolled direction map."""
    sa = _dekat_searah(peta, toleransi, selisih)  # the scan is the same in every comparison
    return min(jarak_tepi_arah(peta, p, toleransi=toleransi, selisih=selisih, sa=sa) for p in daftar_peta)
