"""bandingkan_skala.py - compare ROI box sizes (ROI_SKALA) on your own photos.

Put photos in one folder per hand. File names must sort in the order the photos were taken
(ambil_foto.py names them that way):

    data_uji/dewa_kanan/20261109_101500_01.jpg
    data_uji/dewa_kiri/...
    data_uji/budi_kanan/...

Run from the backend folder:

    python tools/bandingkan_skala.py data_uji
    python tools/bandingkan_skala.py data_uji --skala 1.0 1.2 1.3 --daftar 8 --csv hasil.csv

It follows what the app does. The first `--daftar` photos of each hand are its enrollment samples
(the app takes 8). The remaining photos are scans. A scan's distance to a hand is the distance to
that hand's closest enrollment sample, exactly like palm.jarak_ke_orang(). Two things are measured:

  - genuine: a scan against its own hand (should be small)
  - impostor: a scan against every other hand (should be large)

Every size is judged on the same photos (the ones that pass the app's checks at every size), so the
sizes are comparable. The share of photos that pass at each size is reported separately, because a
larger box leaves the frame more often.
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `import palm` works from anywhere

import palm  # noqa: E402
from pipeline import analisis  # noqa: E402

SKALA_DEFAULT = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
JUMLAH_DAFTAR = 8  # the app enrolls 8 samples per hand
BATAS_DEFAULT = 0.38  # the app's default threshold
EKSTENSI = {".jpg", ".jpeg", ".png"}
KELUAR_BINGKAI = "Tangan terlalu dekat/jauh atau keluar dari bingkai"


def baca_kelas(folder):
    """{hand name: [photo paths sorted by file name]} for every sub-folder that has photos."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"Folder tidak ditemukan: {folder}")
    kelas = {}
    for d in sorted(folder.iterdir()):
        if d.is_dir():
            foto = sorted(p for p in d.iterdir() if p.suffix.lower() in EKSTENSI)
            if foto:
                kelas[d.name] = foto
    return kelas


def analisis_semua(kelas, skala_list, deteksi=palm.deteksi_tangan):
    """Run the app's own analysis for every photo at every size.

    Returns {skala: {hand: [(path, code or None, reason it failed)]}}. Hand detection does not
    depend on the box size, so it runs once per photo and is reused for every size.
    """
    hasil = {k: {nama: [] for nama in kelas} for k in skala_list}
    for nama, files in kelas.items():
        for p in files:
            frame = cv2.imread(str(p))
            if frame is None:
                for k in skala_list:
                    hasil[k][nama].append((p, None, "Gambar tidak bisa dibaca"))
                continue
            terdeteksi = deteksi(frame)
            for k in skala_list:
                a = analisis(frame, deteksi=lambda f, d=terdeteksi: d, roi_skala=k)
                hasil[k][nama].append((p, a.kode, a.gagal))
    return hasil


def foto_bersama(hasil, skala_list):
    """Per hand, the photos that pass at every size, so every size is judged on the same photos."""
    bersama = {}
    for nama in hasil[skala_list[0]]:
        ok = None
        for k in skala_list:
            lolos = {p for p, kode, _ in hasil[k][nama] if kode is not None}
            ok = lolos if ok is None else ok & lolos
        bersama[nama] = ok
    return bersama


def skor(hasil_k, bersama, jumlah_daftar, jarak_ke_orang=palm.jarak_ke_orang):
    """Genuine and impostor distances for one size, plus how often the closest hand is the right one.

    A hand needs more than `jumlah_daftar` usable photos: the first ones enroll it, the rest are scans.
    `jarak_ke_orang(feature, enrolled features)` is the distance to one hand; it defaults to the Gabor code.
    Returns (genuine, impostor, correct, scans, hands used).
    """
    daftar, uji = {}, {}
    for nama, items in hasil_k.items():
        kode = [k for p, k, _ in items if k is not None and p in bersama[nama]]
        if len(kode) > jumlah_daftar:
            daftar[nama] = np.stack(kode[:jumlah_daftar])
            uji[nama] = kode[jumlah_daftar:]
    asli, palsu, benar, total = [], [], 0, 0
    for nama, scans in uji.items():
        for kode in scans:
            jarak = {c: jarak_ke_orang(kode, daftar[c]) for c in daftar}
            asli.append(jarak[nama])
            palsu.extend(v for c, v in jarak.items() if c != nama)
            benar += min(jarak, key=jarak.get) == nama
            total += 1
    return asli, palsu, benar, total, len(daftar)


def tingkat_salah(asli, palsu, batas):
    """(false accept rate, false reject rate) at a threshold. A scan is accepted when distance < threshold."""
    far = sum(d < batas for d in palsu) / len(palsu)
    frr = sum(d >= batas for d in asli) / len(asli)
    return far, frr


def batas_terbaik(asli, palsu, rentang=(0.10, 0.50), langkah=0.002):
    """Threshold where false accepts and false rejects are closest, and that equal error rate.

    Several thresholds can tie (for example when the two groups do not overlap at all). The middle one
    is returned, which is the safest choice: equally far from both groups. `rentang` is the range of
    thresholds tried. The default suits the Gabor distance (0 to about 0.5); a method whose distances
    reach further needs a wider range, otherwise its best threshold would lie outside what is searched.
    """
    kandidat = []
    for b in np.arange(rentang[0], rentang[1] + langkah / 2, langkah):
        far, frr = tingkat_salah(asli, palsu, b)
        kandidat.append((abs(far - frr), float(b), far, frr))
    terkecil = min(k[0] for k in kandidat)
    sama = [k for k in kandidat if k[0] <= terkecil + 1e-12]
    _, b, far, frr = sama[len(sama) // 2]
    return b, (far + frr) / 2


def bandingkan(folder, skala_list=None, jumlah_daftar=JUMLAH_DAFTAR, batas=BATAS_DEFAULT,
               deteksi=palm.deteksi_tangan):
    """Run the whole comparison. Returns (one summary dict per size, info about the data)."""
    skala_list = skala_list or SKALA_DEFAULT
    kelas = baca_kelas(folder)
    if len(kelas) < 2:
        raise ValueError("Butuh minimal 2 folder tangan (misalnya dewa_kanan dan dewa_kiri) supaya ada pembanding.")
    hasil = analisis_semua(kelas, skala_list, deteksi)
    bersama = foto_bersama(hasil, skala_list)
    jumlah_foto = sum(len(v) for v in kelas.values())

    ringkasan = []
    for k in skala_list:
        semua = [item for items in hasil[k].values() for item in items]
        gagal = Counter(g for _, kode, g in semua if kode is None)
        asli, palsu, benar, total, tangan = skor(hasil[k], bersama, jumlah_daftar)
        baris = {"skala": k, "lolos": sum(kode is not None for _, kode, _ in semua), "foto": len(semua),
                 "keluar_bingkai": gagal.get(KELUAR_BINGKAI, 0), "tangan": tangan, "uji": total,
                 "gagal": dict(gagal)}
        if asli and palsu:
            far, frr = tingkat_salah(asli, palsu, batas)
            b, eer = batas_terbaik(asli, palsu)
            baris.update(rata_asli=float(np.mean(asli)), rata_palsu=float(np.mean(palsu)),
                         selisih=float(np.mean(palsu) - np.mean(asli)), batas_eer=b, eer=eer,
                         far=far, frr=frr, benar=benar / total)
        ringkasan.append(baris)
    # the rejected photos of the first size, so you can open them and see what is wrong
    ditolak = [(str(p), alasan) for items in hasil[skala_list[0]].values() for p, kode, alasan in items if kode is None]
    info = {"tangan": len(kelas), "foto": jumlah_foto, "bersama": sum(len(v) for v in bersama.values()),
            "jumlah_daftar": jumlah_daftar, "batas": batas, "ditolak": ditolak}
    return ringkasan, info


KOLOM = [
    ("Ukuran", "{skala:.1f}x", 7),
    ("Lolos", "{lolos}/{foto}", 9),
    ("Keluar bingkai", "{keluar_bingkai}", 14),
    ("Jarak tangan sama", "{rata_asli:.3f}", 17),
    ("Jarak orang lain", "{rata_palsu:.3f}", 16),
    ("Selisih", "{selisih:.3f}", 8),
    ("EER", "{eer_persen:.1f}%", 7),
    ("Batas terbaik", "{batas_eer:.2f}", 13),
    ("Salah tolak", "{frr_persen:.1f}%", 11),
    ("Salah terima", "{far_persen:.1f}%", 12),
    ("Kenal benar", "{benar_persen:.0f}%", 11),
]


MIN_UJI = 30  # below this many scans, an error rate of 0% says very little


def cetak(ringkasan, info, detail=False):
    print(f"\n{info['tangan']} tangan, {info['foto']} foto. Pendaftaran: {info['jumlah_daftar']} foto pertama "
          f"tiap tangan, sisanya untuk uji. Foto yang lolos di semua ukuran: {info['bersama']}.\n")
    print("  ".join(f"{nama:<{lebar}}" for nama, _, lebar in KOLOM))
    print("  ".join("-" * lebar for _, _, lebar in KOLOM))
    for r in ringkasan:
        if "eer" not in r:
            print(f"{r['skala']:.1f}x  tidak cukup data uji (butuh lebih dari {info['jumlah_daftar']} foto lolos per tangan)")
            continue
        nilai = dict(r, eer_persen=100 * r["eer"], frr_persen=100 * r["frr"], far_persen=100 * r["far"],
                     benar_persen=100 * r["benar"])
        print("  ".join(f"{fmt.format(**nilai):<{lebar}}" for _, fmt, lebar in KOLOM).rstrip())
    pertama = ringkasan[0]
    if pertama["gagal"]:
        print(f"\nFoto yang ditolak pada ukuran {pertama['skala']:.1f}x ({pertama['foto'] - pertama['lolos']} dari {pertama['foto']}), "
              "dengan alasan yang sama seperti di aplikasi:")
        for alasan, jumlah in sorted(pertama["gagal"].items(), key=lambda x: -x[1]):
            print(f"  {jumlah:>3}  {alasan}")
        if not detail:
            print("  Tambahkan --detail untuk melihat nama file yang ditolak.")
    if detail and info["ditolak"]:
        print("\nFile yang ditolak:")
        for path, alasan in info["ditolak"]:
            print(f"  {path}  ->  {alasan}")
    layak = [r for r in ringkasan if "eer" in r]
    if not layak:
        return
    if min(r["uji"] for r in layak) < MIN_UJI:
        print(f"\nPERINGATAN: hanya {min(r['uji'] for r in layak)} scan uji. EER 0% dengan data sekecil ini bukan bukti "
              f"sempurna. Ambil lebih banyak foto (target minimal {MIN_UJI} scan uji).")
    terbaik = min(layak, key=lambda r: (r["eer"], -r["selisih"]))
    print(f"\nEER terendah: {terbaik['skala']:.1f}x ({100 * terbaik['eer']:.1f}%), "
          f"dengan batas terbaik sekitar {terbaik['batas_eer']:.2f}.")
    mirip = [r for r in layak if r["eer"] <= terbaik["eer"] + 0.005]
    if len(mirip) > 1:
        daftar = ", ".join(f"{r['skala']:.1f}x" for r in mirip)
        print(f"Hasilnya hampir sama untuk {daftar} (selisih EER di bawah 0,5 poin persen). "
              "Dengan data ini belum ada alasan memilih salah satunya. Pakai kolom Selisih sebagai pembeda, "
              "atau tambah foto.")
    print(f"Jumlah uji: {terbaik['uji']} scan dari {terbaik['tangan']} tangan. "
          "Selisih kecil antar ukuran dengan foto sedikit belum bisa dianggap nyata, ulangi dengan lebih banyak foto.")
    print(f"Salah tolak dan salah terima dihitung pada batas {info['batas']:.2f}.")
    print("\nCara membaca:")
    print("  Lolos           foto yang lolos pengecekan aplikasi pada ukuran itu. Ukuran besar lebih sering keluar bingkai.")
    print("  Jarak           rata-rata jarak scan ke tangan yang sama (harus kecil) dan ke tangan lain (harus besar).")
    print("  Selisih         jarak orang lain dikurangi jarak tangan sama. Makin besar makin mudah dibedakan.")
    print("  EER             tingkat salah ketika salah tolak sama dengan salah terima. Makin kecil makin baik.")
    print("  Salah tolak     tangan yang sama ditolak. Salah terima: orang lain dikenali. Kenal benar: tangan terdekat sudah benar.")


def simpan_csv(ringkasan, path):
    kolom = ["skala", "lolos", "foto", "keluar_bingkai", "tangan", "uji", "rata_asli", "rata_palsu", "selisih",
             "batas_eer", "eer", "far", "frr", "benar"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolom, extrasaction="ignore")
        w.writeheader()
        w.writerows(ringkasan)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bandingkan ukuran kotak ROI (ROI_SKALA) pada foto sendiri.")
    ap.add_argument("folder", help="folder berisi satu sub-folder per tangan, misalnya data_uji")
    ap.add_argument("--skala", type=float, nargs="+", default=SKALA_DEFAULT, help="ukuran yang dibandingkan")
    ap.add_argument("--daftar", type=int, default=JUMLAH_DAFTAR, help="jumlah foto pertama per tangan untuk pendaftaran")
    ap.add_argument("--batas", type=float, default=BATAS_DEFAULT, help="batas kecocokan untuk salah tolak/terima")
    ap.add_argument("--csv", help="simpan ringkasan ke file CSV ini")
    ap.add_argument("--detail", action="store_true", help="tampilkan nama file yang ditolak beserta alasannya")
    args = ap.parse_args(argv)
    try:
        ringkasan, info = bandingkan(args.folder, args.skala, args.daftar, args.batas)
    except ValueError as err:
        print(f"Galat: {err}", file=sys.stderr)
        return 1
    cetak(ringkasan, info, args.detail)
    if args.csv:
        simpan_csv(ringkasan, args.csv)
        print(f"\nRingkasan disimpan di {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
