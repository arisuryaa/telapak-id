# Desain: Telapak ID versi Web

Tanggal: 2026-11-02
Status: disetujui pemilik proyek (2026-11-02)

## 1. Maksud dan alasan

Telapak ID adalah tugas akhir mata kuliah: pengenalan identitas dari pola telapak tangan dengan computer vision klasik (filter Gabor + Competitive Code, tanpa training). Versi sekarang berjalan di terminal + jendela OpenCV ([palm.py](../../../palm.py), [register.py](../../../register.py), [scan.py](../../../scan.py), [delete.py](../../../delete.py)), dan menyimpan kode di file `.npy`.

Versi web ini dibuat untuk **presentasi ke dosen**. Dua pesan yang harus sampai:

1. Telapak tangan bisa menjadi **alternatif cara mengenali orang**.
2. **Alur pemrosesan terlihat**: dari satu foto sampai nama orang, langkah demi langkah, dengan gambar asli dari tiap tahap. Ini juga supaya pemilik proyek sendiri memahami alurnya.

## 2. Sasaran

- Aplikasi web: daftar, scan, lihat langkah pemrosesan, lihat detail orang, kelola data.
- Data orang dan kode telapak disimpan di **MySQL** (bukan file `.npy`).
- Kamera di browser menampilkan **kerangka tangan + kotak ROI yang mengikuti tangan** (opsi C), **FPS**, dan **daftar validasi**.
- Tangan yang tidak valid (terutama **mengepal**) ditolak dan tidak diproses.
- Setelah foto diambil: halaman **timeline 8 langkah** dengan gambar, lalu **halaman detail** orang yang dikenali.

## 3. Bukan sasaran

- Login / autentikasi pengguna.
- Deploy online; aplikasi berjalan di laptop (localhost) saat demo.
- Riwayat scan. Hasil scan hanya tampil saat itu lalu hilang.
- Menyimpan foto telapak. Yang disimpan hanya kode angka.
- Deep learning (Jalur 2 di README tetap sebagai "pengembangan").
- Mengubah metode pengenalan (Gabor, Competitive Code, jarak sudut tetap seperti di `palm.py`).

## 4. Anti-sasaran (gagal walau secara teknis jalan)

- **Gambar langkah yang tidak jujur.** Gambar di halaman Hasil harus berasal dari data yang benar-benar dipakai untuk mencocokkan, bukan ilustrasi atau pemrosesan terpisah.
- **Tangan mengepal atau punggung tangan masih bisa menghasilkan "Dikenali".**
- **Terlalu rumit untuk dijelaskan.** Pemilik proyek harus bisa menjelaskan tiap bagian ke dosen. Hindari lapisan atau pustaka yang tidak perlu.
- **Demo gagal karena internet.** Semua bagian (termasuk model MediaPipe di browser) harus jalan tanpa internet setelah instalasi.

## 5. Batasan

- Windows 11, Python 3.10.6, `mediapipe==0.10.14` (API `mp.solutions`), `numpy<2`.
- Hapus `opencv-python` dari requirements: `mediapipe` sudah membawa `opencv-contrib-python`, dan keduanya bentrok di modul `cv2`.
- Node 24 tersedia.
- MySQL 8 dari **Laragon** di laptop (default Laragon: user `root`, tanpa password, port 3306).
- Antarmuka dan teks dalam **Bahasa Indonesia**.
- Prinsip privasi tetap: persetujuan sebelum daftar, hanya kode yang disimpan, data bisa dihapus.

## 6. Keputusan dari pemilik proyek

| Hal | Keputusan |
|---|---|
| Platform | Website |
| Frontend | **React + Tailwind** |
| Database | **MySQL di Laragon** (laptop sendiri) |
| Garis panduan kamera | **Opsi C**: kerangka 21 titik + kotak ROI mengikuti tangan; hijau = valid, merah = tidak. **Tanpa siluet**; saat tangan belum ada, layar polos + pesan teks |
| Langkah pemrosesan | Muncul **setelah foto diambil**, bukan live |
| Tampilan langkah | **Opsi A: timeline** satu halaman panjang (scroll) |
| Detail orang | Di halaman terpisah; isi **nama, umur, status** |
| Status | Peran orang (mahasiswa / dosen / staf / tamu) |
| Riwayat scan | **Tidak** |
| Peta halaman | Disetujui (bagian 8) |

## 7. Arsitektur (keputusan Claude)

```
Browser (React + Tailwind, Vite)
  ├─ kamera (getUserMedia)
  ├─ MediaPipe Tasks Vision JS (HandLandmarker) → kerangka, ROI, validasi, FPS
  └─ saat valid: kirim frame JPEG ke backend
        │  HTTP JSON (/api/...)
Backend (Python Flask)
  ├─ palm.py (dipakai ulang; MediaPipe Python → ROI → CLAHE → Gabor → kode)
  ├─ pembuat gambar tiap langkah (base64 PNG)
  └─ SQLAlchemy + PyMySQL → MySQL (Laragon)
```

- **Deteksi live di browser** supaya FPS tinggi (frame tidak dikirim terus ke server). FPS yang ditampilkan = FPS loop deteksi di browser.
- **Pemrosesan pengenalan tetap di server dengan `palm.py`**, baik untuk daftar maupun scan, supaya ROI dan kode selalu dibuat dengan cara yang sama. Server mendeteksi ulang landmark pada frame yang dikirim (browser hanya untuk panduan dan validasi).
- Model `hand_landmarker.task` dan file WASM MediaPipe disimpan lokal di folder `public/` frontend, tidak diambil dari CDN saat runtime.
- Saat development: Flask di port 5000, Vite dev server dengan proxy `/api` ke Flask.
- Konfigurasi database lewat file `.env` (`DATABASE_URL=mysql+pymysql://root:@localhost:3306/telapak_id`). Tabel dibuat otomatis saat backend mulai; database `telapak_id` dibuat otomatis jika belum ada.

### Struktur folder (usulan)

```
backend/   app.py, palm.py, validation.py, steps.py, db.py, requirements.txt, tests/
frontend/  (Vite + React + Tailwind) src/pages/{Scan,Hasil,DetailOrang,Daftar,DataTerdaftar}.jsx
docs/
README.md
```

File lama `register.py`, `scan.py`, `delete.py` dihapus karena digantikan web; `palm.py` dipindah ke `backend/`. Data `.npy` lama tidak dimigrasi (cukup daftar ulang). (Keputusan Claude.)

## 8. Halaman

### 1. Scan (`/`)
- Video kamera dengan overlay opsi C. FPS di pojok kanan atas.
- Daftar validasi di samping (lihat bagian 9), tiap butir centang hijau / silang merah.
- Pesan status di bawah video (mis. "Letakkan telapak di depan kamera", "Buka semua jari", "Tahan...").
- Jika semua validasi lolos selama **±1 detik berturut-turut**, frame diambil otomatis dan dikirim ke `/api/scan`, lalu pindah ke Hasil.
- Slider **batas** (default 0,38, rentang 0,10–0,50), menggantikan tombol +/−. Nilai diingat di browser dan dikirim bersama permintaan scan.

### 2. Hasil (`/hasil`)
Timeline vertikal 8 langkah. Tiap langkah: nomor, judul, gambar, penjelasan 1–2 kalimat, dan angka penting.

| # | Langkah | Gambar | Angka |
|---|---|---|---|
| 1 | Foto dari kamera | frame asli | resolusi |
| 2 | Deteksi tangan | frame + 21 titik dan kerangka | jumlah titik |
| 3 | Diluruskan | frame setelah diputar + kotak ROI | sudut putar (°) |
| 4 | ROI grayscale | ROI 128×128 | ukuran |
| 5 | CLAHE + normalisasi | ROI setelah CLAHE | rata-rata / simpangan |
| 6 | Filter Gabor 6 arah | 6 peta respons (0°, 30°, …, 150°) | parameter filter |
| 7 | Competitive Code | peta kode berwarna (6 warna = 6 arah) + legenda | — |
| 8 | Pencocokan | grafik batang jarak ke tiap orang terdaftar + garis batas | jarak terkecil, batas |

Kotak hasil di bawah:
- **Dikenali** (jarak terkecil < batas): nama + jarak + tombol "Lihat detail".
- **Tidak dikenal**: jarak terdekat + tombol "Scan ulang".
- Jika ROI gagal cek kualitas di server: pesan alasannya + tombol "Scan ulang" (langkah yang sudah dihitung tetap ditampilkan sampai titik gagal).

Data hasil hanya ada di memori browser; me-refresh halaman Hasil boleh kembali ke Scan.

### 3. Detail orang (`/orang/:id`)
Nama, umur, status, tangan yang cocok (kiri/kanan) dan jaraknya (dari scan barusan, jika datang dari Hasil). Tombol "Scan lagi".

### 4. Daftar (`/daftar`)
1. Form: nama, umur (angka), status (pilihan: mahasiswa / dosen / staf / tamu), tangan (kiri/kanan), centang persetujuan (wajib).
2. Bisa memilih **orang yang sudah terdaftar** untuk menambah tangan satunya. Jika tangan yang sama sudah ada, minta konfirmasi untuk mengganti.
3. Kamera dengan overlay dan validasi yang sama seperti Scan. Mengambil **8 sampel** otomatis, jeda ±0,8 detik, progres "3/8".
4. Server memproses tiap sampel. Sampel yang gagal di server (tangan tidak terdeteksi / ROI buruk) diulang sampai terkumpul 8 sampel valid. Baru setelah 8 lengkap, data disimpan.
5. Selesai: pesan sukses + tautan ke Scan.

### 5. Data terdaftar (`/data`)
Tabel: nama, umur, status, tangan terdaftar, tanggal daftar. Tombol hapus per orang (dengan konfirmasi) dan "Hapus semua" (dengan konfirmasi). Menggantikan `delete.py`.

Navigasi atas sederhana: Scan · Daftar · Data terdaftar.

## 9. Validasi tangan

Di browser (live, dari landmark MediaPipe JS):

| Butir | Aturan (nilai awal, boleh disetel) |
|---|---|
| Tangan terdeteksi | HandLandmarker mengembalikan 1 tangan |
| Kelima jari terbuka | Untuk telunjuk–kelingking: jarak ujung jari ke pergelangan > 1,1 × jarak sendi PIP ke pergelangan. Ibu jari: ujung jauh dari pangkal telunjuk. **Inilah yang menolak tangan mengepal** |
| Telapak menghadap kamera | Arah perkalian silang (titik 0→5) × (titik 0→17) dibandingkan dengan sisi tangan (handedness) untuk membedakan telapak dan punggung tangan |
| Jarak pas | Lebar telapak (titik 5–17) dalam rentang piksel tertentu, dan kotak ROI tidak keluar dari frame |
| Tangan diam | Pergeseran rata-rata landmark antar frame di bawah ambang |

Di server (setelah frame diterima):
- Landmark terdeteksi lagi dan ROI bisa dipotong (`ambil_roi` tidak `None`).
- **Garis cukup jelas**: kecerahan ROI dalam rentang wajar dan ketajaman (variance of Laplacian) di atas ambang. Jika gagal → pesan "Foto kurang jelas, ulangi".

## 10. Database

```
orang   : id (PK), nama, umur (int), status (enum: mahasiswa/dosen/staf/tamu), dibuat_pada
telapak : id (PK), orang_id (FK → orang, ON DELETE CASCADE), sisi (enum: kiri/kanan),
          kode (LONGBLOB: 8 × 128 × 128 uint8), dibuat_pada
          UNIQUE (orang_id, sisi)
```

Saat scan, backend memuat semua baris `telapak` dan membandingkan seperti `scan.py` sekarang (jarak ke orang = jarak ke sampel paling mirip, `jarak_ke_orang`). Hasil per baris telapak dilaporkan sebagai "nama (kiri/kanan)" di grafik langkah 8.

## 11. API (garis besar)

| Metode | Path | Isi |
|---|---|---|
| POST | `/api/scan` | frame (base64 JPEG) + batas → semua gambar langkah, jarak per entri, hasil |
| POST | `/api/sampel` | frame → valid/tidak + alasan + kode (untuk pendaftaran) |
| POST | `/api/orang` | data orang + sisi + 8 kode → simpan |
| GET | `/api/orang` | daftar orang + tangan terdaftar |
| GET | `/api/orang/<id>` | detail orang |
| DELETE | `/api/orang/<id>` | hapus satu orang |
| DELETE | `/api/orang` | hapus semua |

Bentuk persis payload diserahkan ke builder.

## 12. Keputusan tambahan (keputusan Claude, setelah pemeriksaan)

- **Validasi jari terbuka dan arah telapak diulang di server** pada landmark yang dideteksi server. Frame yang gagal memakai jalur "gagal → Scan ulang" yang sama dengan foto buram. Ini menjamin anti-sasaran (kepalan / punggung tangan tidak pernah "Dikenali") walau browser lolos.
- **`palm.py` direfaktor supaya mengembalikan gambar antara** (frame diputar, kotak ROI, hasil CLAHE, 6 respons Gabor) **tanpa mengubah matematikanya**. Gambar langkah = array yang sama dengan yang dipakai mencocokkan.
- **MediaPipe di server memakai `static_image_mode=True`**, karena tiap permintaan adalah foto tunggal. Ini pengaturan deteksi, bukan perubahan metode pengenalan.
- **Sisi tangan saat daftar dicek**: sisi yang dideteksi MediaPipe (suara terbanyak dari 8 sampel) harus sama dengan pilihan di form; jika beda, pendaftaran ditolak dengan pesan yang jelas.
- **Cermin**: video di browser ditampilkan seperti cermin (selfie), tetapi frame yang dikirim ke server **tidak dicerminkan**. Label kiri/kanan MediaPipe ditangani dengan aturan yang sama di browser dan server.

## 13. Diserahkan ke builder

- Bentuk payload API, cara kode dikirim antara `/api/sampel` dan `/api/orang`.
- Gaya visual Tailwind (bersih, cocok untuk presentasi; mendukung layar laptop/proyektor).
- Nilai ambang validasi yang tepat (nilai di bagian 9 adalah titik awal).
- Pewarnaan peta Competitive Code dan respons Gabor.
- Tes: tes otomatis untuk fungsi backend (validasi kualitas ROI, pipeline langkah, simpan/muat kode dari database, jarak). Tes frontend tidak wajib.
- README diperbarui: cara instal (pip, npm), menyalakan MySQL Laragon, menjalankan backend + frontend, dan penjelasan alur sesuai versi web.
- Menambahkan `.gitignore` (`__pycache__/`, `node_modules/`, `.env`, `registered_data/`, `.superpowers/`).
