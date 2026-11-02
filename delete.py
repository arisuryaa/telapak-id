"""hapus.py - hapus data terdaftar. Contoh: python hapus.py pak_budi_kanan   |   python hapus.py semua"""
import sys, glob, os
FOLDER = "data_terdaftar"
if len(sys.argv) < 2:
    raise SystemExit("Contoh: python hapus.py pak_budi_kanan   atau   python hapus.py semua")
pola = "*" if sys.argv[1] == "semua" else sys.argv[1]
berkas = glob.glob(os.path.join(FOLDER, pola + ".npy"))
for f in berkas:
    os.remove(f)
print(f"{len(berkas)} data dihapus.")
