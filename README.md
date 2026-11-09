# Telapak ID: Pengenalan Identitas dari Pola Telapak Tangan (Computer Vision)

Prototipe pembelajaran berbasis web: seseorang **mendaftarkan telapak tangannya**, lalu sistem **mengenalinya kembali** lewat webcam.

Halaman scan menampilkan kerangka tangan, kotak area telapak yang diproses, dan FPS. Setelah foto diambil, halaman hasil menampilkan **8 langkah pemrosesan** dengan gambar asli dari tiap tahap, lalu detail orang yang dikenali.

---

## 1. Isi folder

```
backend/                  Flask API + inti computer vision (Python)
  app.py                  endpoint API
  palm.py                 ROI telapak, filter Gabor, Competitive Code, jarak
  validation.py           aturan tangan: jari terbuka, telapak menghadap kamera, kualitas ROI
  pipeline.py             membaca frame dan menjalankan langkah secara berurutan
  steps.py                menyusun 8 kartu langkah untuk halaman hasil
  db.py                   model MySQL (orang, telapak) dan fungsi data
  tests/                  tes otomatis (pytest) dan fixture
frontend/                 React + Tailwind + Vite
  src/pages/              Scan, Hasil, Detail orang, Daftar, Data terdaftar
  src/components/         kamera berpanduan, grafik jarak
  src/hooks/              deteksi tangan di browser (MediaPipe) dan FPS
  src/lib/                aturan validasi (sisi browser) dan pemanggil API
docs/superpowers/         desain dan rencana implementasi
registered_data/          (tidak dipakai lagi; sisa data versi terminal, boleh dihapus)
```

## 2. Kebutuhan

- Windows 10/11, Python 3.10 (disarankan 3.10 atau 3.11), Node.js 20 atau lebih baru.
- MySQL 8.

Catatan: `mediapipe` dikunci ke **0.10.14** karena versi lebih baru tidak lagi menyertakan antarmuka `mp.solutions` yang dipakai backend.

## 3. Cara menjalankan

Nyalakan MySQL, lalu:

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
copy .env.example .env          # sesuaikan DATABASE_URL jika perlu
python app.py                   # berjalan di http://127.0.0.1:5000

# 2. Frontend (terminal lain)
cd frontend
npm install                     # menyalin aset MediaPipe ke public/mediapipe
npm run dev                     # buka http://localhost:5173
```

Database `telapak_id` dan tabelnya dibuat otomatis saat backend pertama kali berjalan. Jika MySQL belum menyala, backend menampilkan pesan dan berhenti tanpa traceback.

Browser perlu izin akses kamera. Halaman Scan dan Daftar tidak berjalan tanpa kamera.

## 4. Alur pemakaian

| Halaman | Isi |
|---|---|
| **Scan** (`/`) | Kamera dengan kerangka tangan, kotak area telapak, FPS, dan daftar syarat foto. Foto diambil otomatis saat semua syarat terpenuhi dan tangan ditahan sekitar 1 detik. Slider batas mengatur ambang kecocokan. |
| **Hasil** (`/hasil`) | Timeline 8 langkah pemrosesan dengan gambar, lalu kotak hasil: dikenali (dengan tombol *Lihat detail*), tidak dikenal, atau gagal (dengan alasannya). |
| **Detail orang** (`/orang/:id`) | Nama, umur, status, tangan yang terdaftar, dan jarak kecocokan dari scan terakhir. |
| **Daftar** (`/daftar`) | Form nama, umur, status, sisi tangan, dan persetujuan. Lalu kamera mengambil 8 sampel. Orang yang sudah terdaftar bisa ditambah tangan satunya. |
| **Data terdaftar** (`/data`) | Tabel orang yang terdaftar, dengan hapus per orang atau hapus semua. |

## 5. Proses computer vision

| # | Tahap | Alat | Keterangan |
|---|---|---|---|
| 1 | Foto dari kamera | browser (`getUserMedia`) | Satu frame diambil saat tangan valid |
| 2 | Deteksi tangan | MediaPipe Hands | 21 titik tangan. Di browser untuk panduan, di server untuk pengenalan |
| 3 | Telapak diluruskan | `getRotationMatrix2D`, `warpAffine` | Diputar sampai garis pangkal jari mendatar |
| 4 | ROI abu-abu | slicing, `cvtColor`, `resize` | Kotak tengah telapak, 128×128 |
| 5 | CLAHE dan normalisasi | CLAHE, normalisasi | Garis tipis dipertegas |
| 6 | Filter Gabor 6 arah (`METODE=gabor`) atau Canny: blur dan gradien (`METODE=canny`) | `getGaborKernel`, `filter2D` atau `GaussianBlur`, `Sobel` | Gabor: respons tiap arah (0°–150°). Canny: foto diperhalus lalu kekuatan gradiennya dihitung |
| 7 | Competitive Code (Gabor) atau tepi Canny dan arahnya (Canny) | `argmin` atau `Canny` | Gabor: tiap piksel diberi arah pemenang (0–5). Canny: tiap piksel tepi diberi arah garisnya (1–6, 0 = bukan tepi) |
| 8 | Pencocokan | NumPy | Jarak sudut ke sampel tiap orang terdaftar, toleransi geser ±3 piksel |

Pengelompokan untuk laporan: tahap 2–4 = *preprocessing*, tahap 5–6 = *feature extraction*, tahap 7–8 = *matching*.

Gambar pada halaman hasil adalah **data yang sama** dengan yang dipakai untuk mencocokkan, bukan ilustrasi. Hanya tahap 1–3 yang ditampilkan dengan frame penuh, sisanya berukuran 128×128.

### Ukuran kotak ROI (`ROI_SKALA`)

Kotak jurnal (1,0×) adalah persegi selebar telapak (jarak pangkal telunjuk ke pangkal kelingking), dimulai 0,15× lebar di bawah garis pangkal jari. Kotak ini hanya mengambil tengah telapak, karena tepi telapak (pangkal ibu jari, pergelangan) bentuknya berubah-ubah antar foto.

Untuk perbandingan, ukuran kotak bisa diubah di `backend/.env`, misalnya `ROI_SKALA=1.3`. `ROI_SKALA` adalah **lebar** kotak dalam lebar telapak. Rentang yang diizinkan 0,8–1,5; di atas 1,5 kotak keluar dari telapak dan ikut mengambil latar belakang.

- **Di bawah 1,0**, kotak mengecil merata di sekitar titik tengah yang sama.
- **Di atas 1,0**, kotak melebar ke samping dan tepi atasnya naik mendekati garis pangkal jari (tepat di garis itu pada 1,3× atau lebih), tetapi tepi bawahnya tetap di 1,15× lebar, yaitu sekitar pergelangan. Kotak jadi lebih lebar daripada tinggi (misalnya 1,3 × 1,15 pada 1,3×) dan tetap diperkecil ke 128×128. Rumusnya ada di `batas_vertikal()` di `backend/palm.py` dan `batasVertikal()` di `frontend/src/lib/validation.js`, dan keduanya harus sama.

- Setiap tangan menyimpan ukuran dan **versi bentuk** kotak yang dipakai saat mendaftar. Scan hanya membandingkan dengan data yang ukuran dan bentuknya sama, karena kode dari kotak yang berbeda tidak bisa dibandingkan. Tangan yang didaftarkan dengan 1,3× sebelum bentuk ini (kotak yang tumbuh merata sampai melewati pergelangan) dianggap berbeda dan harus didaftar ulang.
- Setelah mengubah `ROI_SKALA` (atau `METODE`), restart backend dan daftar ulang (pilih orangnya, lalu setujui penggantian).
- Halaman *Data terdaftar* menampilkan ukuran kotak setiap tangan, misalnya `kanan (1.3×)`.

### Metode pengenalan: Canny atau Gabor (`METODE`)

Aplikasi punya dua cara mengubah ROI menjadi pola yang dicocokkan. Pilih di `backend/.env`, lalu restart backend:

```
METODE=canny     # tepi Canny yang menyimpan arah tiap tepi (sedang dipakai)
METODE=gabor     # kode 6 filter Gabor (metode semula, metode inti di jurnal rujukan)
```

- **Canny + arah.** Canny mencari tepi, dan satu garis tipis sering menjadi dua tepi sejajar. Canny sendiri menghitung arah gradien untuk menipiskan tepi. Arah itu disimpan di tiap piksel tepi (6 kelompok, 30° per kelompok), dan dua tepi hanya dianggap cocok jika letaknya berdekatan (toleransi 1 piksel, geser ±3 piksel) dan arahnya mirip. Parameter: blur sigma 1,5 dan ambang atas di persentil ke-95 gradien (`SIGMA`, `PERSEN` di `backend/canny.py`).
- **Gabor.** 6 filter dengan arah berbeda, lalu tiap piksel diberi arah pemenang. Lihat bagian 5.
- Hasil pengujian pada foto sendiri (satu orang, sekitar 33 scan) menunjukkan Gabor lebih akurat: EER 0% dibanding 3 sampai 9% untuk Canny + arah dan 9 sampai 18% untuk Canny tanpa arah. Datanya masih sedikit, jadi ulangi dengan lebih banyak orang (bagian 10).
- Kode dari dua metode **tidak bisa dibandingkan**. Setiap tangan menyimpan metode yang dipakai saat mendaftar, dan scan hanya memakai tangan yang metodenya sama. Tangan dari metode lain tidak dihapus dan dipakai lagi kalau Anda kembali ke metode itu. Setelah mengganti `METODE`, daftar ulang (pilih orangnya, lalu setujui penggantian).
- **Skala jarak berbeda.** Jarak Gabor acak sekitar 0,5. Jarak Canny acak sekitar 0,8 ke atas. Karena itu setiap metode punya batas bawaan dan rentang slider sendiri (`backend/metode.py`): Gabor 0,38 (0,10 sampai 0,50) dan Canny 0,75 (0,40 sampai 0,95). Batas Canny diambil dari data sedikit, jadi setel ulang dari pengujian Anda.
- Halaman Hasil menampilkan tahapan sesuai metode: langkah 6 dan 7 berbeda, sisanya sama.

## 6. Validasi tangan

Dicek dua kali: di browser (untuk panduan langsung) dan di server (sebelum pengenalan). Foto yang gagal di server tidak pernah menghasilkan "dikenali".

| Syarat | Cara cek |
|---|---|
| Tangan terdeteksi | MediaPipe menemukan satu tangan |
| Kelima jari terbuka | Ujung jari lebih jauh dari pergelangan daripada sendi tengahnya. **Ini yang menolak tangan mengepal.** |
| Telapak menghadap kamera | Arah perkalian silang pergelangan–telunjuk dan pergelangan–kelingking sesuai sisi tangan. Ini yang menolak punggung tangan. |
| Jarak pas | Lebar telapak dalam rentang tertentu dan kotak area tidak keluar dari gambar |
| Tangan diam | Pergeseran titik tangan antar frame kecil |
| Kualitas ROI | Di server: tidak terlalu gelap (rata-rata ≥ 40), tidak lebih dari 40% piksel terpotong putih, dan cukup tajam setelah CLAHE (≥ 20) |

## 7. Bagaimana sistem membedakan orang

Garis tangan **tidak mengandung nama**. Sistem menyimpan **kode angka** (peta arah garis) bersama nama yang dimasukkan saat mendaftar.

1. **Daftar:** 8 sampel telapak menjadi 8 kode, disimpan di bawah satu orang dan sisi tangan.
2. **Scan:** kode baru dihitung, lalu dibandingkan dengan semua kode yang tersimpan. Jarak ke satu orang = jarak ke sampel pendaftarannya yang paling mirip.
3. **Keputusan:** orang dengan jarak terkecil dipilih. Jika jaraknya masih di atas **batas**, jawabannya "tidak dikenal".

Skala jarak: 0 = identik. Pola acak berjarak sekitar 0,5 pada Gabor dan sekitar 0,8 pada Canny (skala keduanya berbeda). Batas yang baik **harus disetel dari pengujian sendiri** (lihat bagian 10), bukan ditebak.

## 8. Privasi dan data

- Pola telapak adalah data biometrik. Persetujuan wajib dicentang sebelum mendaftar.
- Hanya kode angka yang disimpan ke MySQL, **tidak ada foto**, dan tidak ada riwayat scan.
- Data bisa dihapus per orang atau sekaligus lewat halaman *Data terdaftar*.
- Seluruh data demo sebaiknya dihapus setelah presentasi.

### Log untuk debugging

- **Terminal backend** (`python app.py`): satu baris per foto yang dianalisis, misalnya
  `analisis frame=1280x720 tahap=7 label=Left sisi=kanan silang=-10080 roi_terang=127.7 roi_terpotong=0% roi_tajam=36.0 hasil=lolos`,
  lalu ringkasan `scan: ...`, `sampel: ...`, `tersimpan: ...`. Permintaan yang ditolak muncul sebagai `WARNING`.
- **Console browser** (F12 → Console, filter `[Telapak]`): perubahan status tangan (label, sisi, silang, tiap syarat), foto yang diambil, dan setiap panggilan API beserta durasinya.
- **Panel "Info teknis"** di bawah syarat foto: label, sisi, dan nilai silang secara langsung.

Aturan telapak vs punggung tangan: untuk tangan kanan, telapak menghadap kamera jika `silang < 0`; untuk tangan kiri jika `silang > 0`.
Label kiri/kanan dari MediaPipe berbeda antara browser dan server: versi Python (`mp.solutions`) menganggap gambar dicermin, sehingga tangan kanan asli dilaporkan sebagai `Left`. Versi browser (MediaPipe Tasks) melaporkan tangan asli, `Right`. Pemetaannya ada di konstanta `LABEL_KANAN` di `backend/validation.py` dan `frontend/src/lib/validation.js`.

## 9. Menjalankan tes

```bash
cd backend && python -m pytest -q       # tes palm, validasi, pipeline, database, API
cd frontend && npm test                 # tes aturan validasi di browser
cd frontend && npm run build            # memastikan frontend bisa dibangun
```

Tes backend memakai SQLite di memori, jadi tidak membutuhkan MySQL. Tes frontend memakai fixture landmark yang sama dengan backend.

## 10. Cara menyetel batas dan menguji sistem

Parameter filter Gabor di `backend/palm.py` adalah nilai awal yang masuk akal, **bukan hasil penyetelan**, dan sistem belum diuji pada data skala besar.

1. Daftarkan 2–3 orang (atau tangan kiri dan kanan Anda sendiri).
2. Scan tangan **yang sama** beberapa kali, catat jaraknya.
3. Scan tangan **orang lain / yang belum terdaftar**, catat jaraknya.
4. Atur batas dengan slider di halaman Scan ke titik di antara kedua rentang.
5. Uji juga: tangan kiri vs kanan orang yang sama harus tidak dikenali sebagai satu orang.

Tabel hasil (isi dari pengujian nyata):

| Skenario | Jumlah percobaan | Benar | Jarak rata-rata |
|---|---|---|---|
| Tangan sama (terdaftar) | [ ] | [ ] | [ ] |
| Orang lain (terdaftar) | [ ] | [ ] | [ ] |
| Belum terdaftar | [ ] | [ ] | [ ] |

Jika hasil kurang baik, urutan perbaikan: (1) cahaya merata dan latar polos, (2) periksa kotak area telapak di kamera, pastikan yang terpotong adalah tengah telapak dengan garis terlihat, (3) daftar dan scan di tempat serta kamera yang sama.

### Membandingkan ukuran kotak ROI

Dua skrip di `backend/tools/` membantu memilih `ROI_SKALA` berdasarkan data, bukan tebakan. Jalankan dari folder `backend`.

```bash
python tools/ambil_foto.py dewa_kanan          # ambil 20 foto telapak kanan dari webcam
python tools/ambil_foto.py dewa_kiri
python tools/ambil_foto.py budi_kanan          # tangan orang lain, sebagai pembanding
python tools/bandingkan_skala.py data_uji      # bandingkan ukuran 1.0x sampai 1.5x
```

- `ambil_foto.py` membuka kamera. Tekan **SPASI** untuk mulai, lalu foto diambil otomatis tiap 2 detik. Geser tangan sedikit di antara foto. Foto disimpan di `backend/data_uji/<nama>/` dan **tidak ikut git** karena data biometrik. Hapus folder itu setelah selesai.
- Butuh minimal 2 tangan (tangan kiri dan kanan Anda dihitung berbeda) dan sebaiknya 20 foto atau lebih per tangan.
- `bandingkan_skala.py` meniru aplikasi: 8 foto pertama tiap tangan dipakai untuk mendaftar, sisanya untuk scan. Jarak scan ke satu tangan adalah jarak ke sampel terdekatnya. Hasilnya adalah tabel per ukuran: foto yang lolos pengecekan, jarak ke tangan yang sama dan ke tangan lain, **EER** (tingkat salah ketika salah tolak sama dengan salah terima), batas terbaik, serta salah tolak dan salah terima pada batas 0,38. Setiap ukuran dinilai dengan foto yang sama.
- Pilihan lain: `--skala 1.0 1.3`, `--daftar 5`, `--batas 0.35`, `--csv hasil.csv`, dan `--detail` (daftar file yang ditolak beserta alasannya). Alasan penolakan selalu dihitung dan ditampilkan di bawah tabel.
- Untuk uji yang lebih jujur, ambil foto pendaftaran dan foto uji di sesi berbeda (jalankan `ambil_foto.py` lagi untuk tangan yang sama; foto baru ditambahkan setelah yang lama).
- Hasil dari beberapa orang dan puluhan foto adalah petunjuk, bukan bukti. Selisih kecil antar ukuran belum berarti.

### Mencoba Canny sebagai pengganti Gabor

`backend/tools/bandingkan_metode.py` membandingkan kode Gabor dan peta tepi Canny pada foto dan protokol yang sama (folder `data_uji` yang sama dengan di atas). Aplikasi sendiri memakai metode yang dipilih lewat `METODE` (bagian 5).

```bash
python tools/bandingkan_metode.py data_uji
python tools/bandingkan_metode.py data_uji --sigma 1 1.5 2.5 --persen 90 95 --gambar gambar_canny
```

- Canny membuat peta tepi (1 di tepi, 0 di tempat lain) tanpa arah. Dua peta dibandingkan dari seberapa banyak tepi yang berdekatan (toleransi 1 piksel, geser ±3 piksel seperti Gabor), dan jarak ke satu tangan tetap jarak ke sampel terdekatnya.
- Hasil Canny sangat bergantung pada kekuatan blur (`--sigma`) dan ambang (`--persen`), jadi beberapa kombinasi dicoba sekaligus.
- `--arah` mencoba juga **Canny + arah**: Canny sudah menghitung arah gradien untuk memangkas tepi, dan arah itu (6 kelompok, 30° per kelompok) disimpan di tiap piksel tepi. Dua piksel tepi hanya dianggap cocok jika arahnya mirip. Lebih lambat, sekitar 30 detik untuk 60 foto.
- Skala jarak Canny berbeda dari Gabor, jadi tabel membandingkan dengan **EER** dan **d'** (selisih kelompok "tangan sama" dan "tangan lain" dalam satuan simpangan baku), bukan jarak mentah.
- `--gambar folder` menyimpan gambar ROI, hasil CLAHE, tepi Canny, dan kode Gabor untuk dilihat langsung. Folder `backend/gambar_canny/` tidak ikut git.
- Parameter Canny dipilih dengan melihat data yang sama, jadi hasilnya sedikit lebih optimis daripada Gabor. Pakai minimal 30 scan uji sebelum memutuskan.

## 11. Keterbatasan

- Bergantung pada cahaya, fokus, dan posisi tangan.
- Pengujian berskala kecil dengan webcam biasa. Tidak bisa disamakan dengan angka jurnal (alat khusus, ribuan sampel).
- Luka, keringat berlebih, atau penuaan dapat memengaruhi hasil.
- Prototipe pembelajaran, belum layak sebagai pengaman utama.

## 12. Pengembangan

- Evaluasi pada dataset publik (11k Hands, IIT Delhi Touchless Palmprint) untuk angka akurasi yang lebih kuat.
- Perbandingan dengan deep learning (CNN) sebagai "Jalur 2".

## 13. Rujukan

Pastikan detail (halaman, tahun, DOI) diverifikasi di Google Scholar sebelum dikutip.

- Kong, A. W.-K., & Zhang, D. (2004). *Competitive Coding Scheme for Palmprint Verification*. ICPR 2004, hlm. 520–523. **(metode inti)**
- Zhang, D., Kong, A. W.-K., You, J., & Wong, M. (2003). *Online Palmprint Identification*. IEEE TPAMI, 25(9), 1041–1050.
- Kong, A. W.-K. (2007). *Palmprint Identification Based on Generalization of IrisCode*. Disertasi, University of Waterloo.
- Yue, F., Zuo, W., Zhang, D., & Wang, K. (2009). *Orientation selection using modified FCM for competitive code-based palmprint recognition*. Pattern Recognition, 42(11).
- Guo, Z., Zuo, W., Zhang, L., & Zhang, D. (2009). *A unified distance measurement for orientation coding in palmprint verification*. Neurocomputing.
- Afifi, M. (2019). *11K Hands: gender recognition and biometric identification using a large dataset of hand images*. Multimedia Tools and Applications. doi:10.1007/s11042-019-7424-8

Repo terkait (periksa lisensi dan tanggal pembaruan sebelum dipakai):
- `github.com/Leosocy/EDCC-Palmprint-Recognition` (implementasi berbasis competitive code, OpenCV)
- `github.com/Zi-YuanYang/CO3Net` (PyTorch, Jalur 2)

## 14. Catatan jujur

- Perhitungan kode dan jarak sudah diuji dengan data sintetis (jarak diri sendiri 0, data acak sekitar 0,49) dan dengan fixture yang dibuat dari versi lama (kode harus sama persis).
- Validasi tangan diuji dengan titik tangan tiruan. Kinerja dengan tangan dan kamera sungguhan bergantung pada kondisi Anda.
- Parameter filter Gabor (ukuran 21×21, sigma 4, panjang gelombang 10, gamma 0,5), ukuran kotak ROI, dan ambang validasi adalah nilai awal yang disetel sendiri, bukan nilai persis dari jurnal.
