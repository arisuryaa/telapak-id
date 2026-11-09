"""bandingkan_metode.py - compare Canny edge matching with the Gabor competitive code on your own photos.

Same photo folders and the same protocol as bandingkan_skala.py (one folder per hand; the first
`--daftar` photos enroll the hand, the rest are scans; a scan's distance to a hand is the distance
to its closest enrolled sample). Everything before the feature step is the app's own analysis, so
only the method of turning the ROI into a comparable pattern differs:

  - Gabor: the competitive code the app uses
  - Canny: an edge map (canny.py), tried with several blur strengths because Canny is sensitive to them

Run from the backend folder:

    python tools/bandingkan_metode.py data_uji
    python tools/bandingkan_metode.py data_uji --sigma 1 2 3 --persen 90 95 --gambar gambar_canny

The distances of the two methods are not on the same scale, so the table compares them by:
  - EER: the error rate where false accepts equal false rejects (smaller is better)
  - d': how far apart same-hand and other-hand distances are, measured in standard deviations
        (larger is better; it does not depend on the scale of the distance)
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `import palm` works from anywhere

import canny  # noqa: E402
import palm  # noqa: E402
from pipeline import analisis  # noqa: E402
from tools import bandingkan_skala as bs  # noqa: E402

SIGMA_DEFAULT = [1.0, 1.5, 2.5]
PERSEN_DEFAULT = [92.0]
WARNA = [(46, 74, 217), (0, 169, 242), (80, 145, 47), (201, 167, 32), (224, 99, 53), (159, 68, 184)]  # BGR, code 0..5


def kumpulkan(kelas, skala, deteksi=palm.deteksi_tangan):
    """{hand: [(path, grey ROI or None, Gabor code or None, reason it failed)]} from the app's own analysis."""
    hasil = {}
    for nama, files in kelas.items():
        hasil[nama] = []
        for p in files:
            frame = cv2.imread(str(p))
            if frame is None:
                hasil[nama].append((p, None, None, "Gambar tidak bisa dibaca"))
                continue
            terdeteksi = deteksi(frame)
            a = analisis(frame, deteksi=lambda f, d=terdeteksi: d, roi_skala=skala)
            hasil[nama].append((p, a.roi_detail["roi"] if a.kode is not None else None, a.kode, a.gagal))
    return hasil


def daftar_metode(sigma_list, persen_list, toleransi, arah=False):
    """[(label, feature function(roi, gabor code), distance-to-hand function)]

    With `arah`, every Canny setting is also tried with the edge direction kept (canny.peta_tepi_arah).
    """
    metode = [("Gabor (aplikasi)", lambda roi, kode: kode, palm.jarak_ke_orang)]
    for s in sigma_list:
        for pr in persen_list:
            metode.append((
                f"Canny sigma {s:g}, persen {pr:g}",
                lambda roi, kode, s=s, pr=pr: canny.peta_tepi(roi, s, pr),
                lambda x, d, t=toleransi: canny.jarak_ke_orang(x, d, t),
            ))
            if arah:
                metode.append((
                    f"Canny+arah sigma {s:g}, persen {pr:g}",
                    lambda roi, kode, s=s, pr=pr: canny.peta_tepi_arah(roi, s, pr),
                    lambda x, d, t=toleransi: canny.jarak_ke_orang_arah(x, d, t),
                ))
    return metode


def dprime(asli, palsu):
    """Separation of the two groups in standard deviations (larger = easier to tell apart)."""
    simpangan = np.sqrt((np.var(asli) + np.var(palsu)) / 2)
    return float((np.mean(palsu) - np.mean(asli)) / simpangan) if simpangan > 0 else float("inf")


def nilai_metode(hasil, jumlah_daftar, fitur, jarak):
    """Scores of one method on the photos that pass the app's checks."""
    hasil_k = {nama: [(p, fitur(roi, kode) if kode is not None else None, g) for p, roi, kode, g in items]
               for nama, items in hasil.items()}
    bersama = {nama: {p for p, f, _ in items if f is not None} for nama, items in hasil_k.items()}
    return bs.skor(hasil_k, bersama, jumlah_daftar, jarak)


def bandingkan(folder, skala=1.0, sigma_list=None, persen_list=None, jumlah_daftar=bs.JUMLAH_DAFTAR,
               toleransi=canny.TOLERANSI, deteksi=palm.deteksi_tangan, arah=False):
    """Run the comparison. Returns (one summary dict per method, info about the data, the raw results)."""
    kelas = bs.baca_kelas(folder)
    if len(kelas) < 2:
        raise ValueError("Butuh minimal 2 folder tangan (misalnya dewa_kanan dan dewa_kiri) supaya ada pembanding.")
    hasil = kumpulkan(kelas, skala, deteksi)
    ringkasan = []
    for label, fitur, jarak in daftar_metode(sigma_list or SIGMA_DEFAULT, persen_list or PERSEN_DEFAULT, toleransi, arah):
        asli, palsu, benar, total, tangan = nilai_metode(hasil, jumlah_daftar, fitur, jarak)
        baris = {"metode": label, "uji": total, "tangan": tangan}
        if asli and palsu:
            # each method has its own distance scale, so search the thresholds over the range its distances cover
            rendah, tinggi = min(asli + palsu), max(asli + palsu)
            batas, eer = bs.batas_terbaik(asli, palsu, (rendah - 0.01, tinggi + 0.01), (tinggi - rendah + 0.02) / 400)
            baris.update(rata_asli=float(np.mean(asli)), rata_palsu=float(np.mean(palsu)), dprime=dprime(asli, palsu),
                         eer=eer, batas_eer=batas, benar=benar / total)
        ringkasan.append(baris)
    semua = [item for items in hasil.values() for item in items]
    info = {"tangan": len(kelas), "foto": len(semua), "lolos": sum(k is not None for _, _, k, _ in semua),
            "jumlah_daftar": jumlah_daftar, "skala": skala}
    return ringkasan, info, hasil


def lembar(roi, kode, sigma_list, persen, skala_gambar=2):
    """One picture: grey ROI, after CLAHE, the Canny edge map for each blur strength, and the Gabor code."""
    def ubin(gambar, judul):
        besar = cv2.resize(gambar, None, fx=skala_gambar, fy=skala_gambar, interpolation=cv2.INTER_NEAREST)
        if besar.ndim == 2:
            besar = cv2.cvtColor(besar, cv2.COLOR_GRAY2BGR)
        besar = cv2.copyMakeBorder(besar, 26, 0, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(besar, judul, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        return besar
    ubins = [ubin(roi, "ROI abu-abu"), ubin(palm.terapkan_clahe(roi), "Setelah CLAHE")]
    for s in sigma_list:
        ubins.append(ubin((1 - canny.peta_tepi(roi, s, persen)) * 255, f"Canny sigma {s:g}"))
    peta = np.array(WARNA, np.uint8)[kode]
    ubins.append(ubin(peta, "Kode Gabor"))
    return np.hstack(ubins)


MET = [("Metode", 34),("EER", 7), ("d'", 6), ("Jarak sama", 11), ("Jarak lain", 11), ("Batas terbaik", 13), ("Kenal benar", 11)]


def cetak(ringkasan, info):
    print(f"\n{info['tangan']} tangan, {info['foto']} foto ({info['lolos']} lolos pengecekan aplikasi). "
          f"Ukuran kotak {info['skala']:g}x. Pendaftaran: {info['jumlah_daftar']} foto pertama tiap tangan.\n")
    print("  ".join(f"{n:<{w}}" for n, w in MET))
    print("  ".join("-" * w for _, w in MET))
    for r in ringkasan:
        if "eer" not in r:
            print(f"{r['metode']:<34}  tidak cukup data uji")
            continue
        sel = [r["metode"], f"{100 * r['eer']:.1f}%", f"{r['dprime']:.2f}", f"{r['rata_asli']:.3f}", f"{r['rata_palsu']:.3f}",
               f"{r['batas_eer']:.2f}", f"{100 * r['benar']:.0f}%"]
        print("  ".join(f"{v:<{w}}" for v, (_, w) in zip(sel, MET)).rstrip())
    layak = [r for r in ringkasan if "eer" in r]
    if not layak:
        return
    uji = min(r["uji"] for r in layak)
    if uji < bs.MIN_UJI:
        print(f"\nPERINGATAN: hanya {uji} scan uji. Dengan data sekecil ini selisih antar metode belum bisa dipercaya. "
              f"Ambil lebih banyak foto (target minimal {bs.MIN_UJI} scan uji).")
    terbaik = min(layak, key=lambda r: (r["eer"], -r["dprime"]))
    print(f"\nEER terendah: {terbaik['metode']} ({100 * terbaik['eer']:.1f}%). d' tertinggi: "
          f"{max(layak, key=lambda r: r['dprime'])['metode']}.")
    print("Parameter Canny dipilih dengan melihat data yang sama, jadi hasil Canny sedikit lebih optimis daripada Gabor.")
    print("\nCara membaca:")
    print("  EER          tingkat salah ketika salah tolak sama dengan salah terima. Makin kecil makin baik.")
    print("  d'           jarak antara kelompok 'tangan sama' dan 'tangan lain' dalam satuan simpangan baku. Makin besar makin baik.")
    print("  Jarak        skala jarak Gabor dan Canny berbeda, jadi jangan dibandingkan langsung.")
    print("  Batas terbaik  batas kecocokan terbaik untuk metode itu (tidak sama antar metode).")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bandingkan Canny dengan filter Gabor pada foto sendiri.")
    ap.add_argument("folder", help="folder berisi satu sub-folder per tangan, misalnya data_uji")
    ap.add_argument("--skala", type=float, default=1.0, help="ukuran kotak ROI (default 1.0)")
    ap.add_argument("--sigma", type=float, nargs="+", default=SIGMA_DEFAULT, help="kekuatan blur sebelum Canny")
    ap.add_argument("--persen", type=float, nargs="+", default=PERSEN_DEFAULT, help="persentil gradien untuk ambang Canny")
    ap.add_argument("--toleransi", type=int, default=canny.TOLERANSI, help="selisih piksel yang masih dianggap tepi yang sama")
    ap.add_argument("--daftar", type=int, default=bs.JUMLAH_DAFTAR, help="jumlah foto pertama per tangan untuk pendaftaran")
    ap.add_argument("--gambar", help="simpan gambar perbandingan (ROI, CLAHE, tepi Canny, kode Gabor) ke folder ini")
    ap.add_argument("--arah", action="store_true", help="coba juga Canny yang menyimpan arah tepi (lebih lambat)")
    args = ap.parse_args(argv)
    try:
        ringkasan, info, hasil = bandingkan(args.folder, args.skala, args.sigma, args.persen, args.daftar, args.toleransi,
                                            arah=args.arah)
    except ValueError as err:
        print(f"Galat: {err}", file=sys.stderr)
        return 1
    cetak(ringkasan, info)
    if args.gambar:
        tujuan = Path(args.gambar)
        tujuan.mkdir(parents=True, exist_ok=True)
        for nama, items in hasil.items():
            pertama = next(((roi, kode) for _, roi, kode, _ in items if kode is not None), None)
            if pertama:
                cv2.imwrite(str(tujuan / f"{nama}.png"), lembar(pertama[0], pertama[1], args.sigma, args.persen[0]))
        print(f"\nGambar perbandingan disimpan di {tujuan}. Isinya ROI dari foto Anda (data biometrik), jangan dibagikan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
