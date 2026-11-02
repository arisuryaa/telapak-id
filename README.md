# Pengenalan Identitas dari Pola Telapak Tangan (Computer Vision)

Prototipe pembelajaran: seseorang **mendaftarkan telapak tangannya**, lalu sistem **mengenalinya kembali** lewat webcam. Tidak ada pelatihan model dan tidak ada dataset yang dibutuhkan untuk menjalankan demo.

---

## 1. Isi folder

| File | Fungsi |
|---|---|
| `palm.py` | Inti sistem: potong ROI telapak, hitung Competitive Code, hitung jarak |
| `daftar.py` | Mendaftarkan seseorang (8 sampel otomatis, hanya kode yang disimpan) |
| `scan.py` | Mengenali telapak dari kamera |
| `hapus.py` | Menghapus data terdaftar |
| `requirements.txt` | Daftar pustaka |
| `README.md` | Dokumen ini |

Folder `data_terdaftar/` dibuat otomatis saat ada yang mendaftar. Isinya file `.npy` berupa **kode angka**, bukan foto.

## 2. Cara menjalankan

```
pip install -r requirements.txt
python daftar.py        # daftar: isi nama, kiri/kanan, persetujuan (y), lalu tahan telapak
python scan.py          # scan: tombol + / - mengubah batas, ESC keluar
python hapus.py semua   # hapus semua data setelah demo
python hapus.py nama_tangan   # hapus satu orang, mis. pak_budi_kanan
```

Catatan:
- `mediapipe` dikunci ke **0.10.14**. Versi lebih baru tidak lagi menyertakan antarmuka `mp.solutions` yang dipakai kode ini. Gunakan Python 3.10 atau 3.11.
- Pesan `INFO` dan `WARNING` dari MediaPipe saat program mulai **bukan error** dan boleh diabaikan. Untuk menyembunyikannya, tambahkan di paling atas `palm.py`:
  ```python
  import os
  os.environ["GLOG_minloglevel"] = "2"
  os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
  ```
- Program menunggu input di prompt `Nama ...:` walau ada pesan log di belakangnya. Ketik nama lalu Enter.

## 3. Proses computer vision

| # | Tahap | Alat | Keterangan |
|---|---|---|---|
| 1 | Akuisisi citra | `cv2.VideoCapture` | Ambil frame webcam |
| 2 | Deteksi tangan | MediaPipe Hands | 21 titik tangan (model siap pakai) |
| 3 | Normalisasi posisi | `getRotationMatrix2D`, `warpAffine` | Putar gambar sampai telapak tegak (dari titik pangkal telunjuk dan kelingking) |
| 4 | Ekstraksi ROI | slicing, `cvtColor`, `resize` | Kotak tengah telapak, grayscale, 128x128 |
| 5 | Peningkatan citra | CLAHE, normalisasi | Pertegas garis tipis, samakan terang-gelap |
| 6 | Ekstraksi ciri | `getGaborKernel`, `filter2D`, `argmin` | 6 filter Gabor (6 arah), tiap piksel diberi angka 0-5 = **Competitive Code** |
| 7 | Pencocokan | NumPy | Jarak sudut antar dua kode, toleransi geser +-3 piksel |

Alur: **frame kamera -> titik tangan -> diluruskan -> ROI grayscale -> kontras dipertegas -> peta arah garis (kode) -> jarak ke yang terdaftar -> nama atau "tidak dikenal".**

Pengelompokan untuk laporan: tahap 2-4 = *preprocessing*, tahap 5-6 = *feature extraction*, tahap 7 = *matching*.

### Kenapa tidak memakai Canny?
Canny mencari tepi, sehingga satu garis tipis sering terbelah menjadi dua tepi sejajar, dan hasilnya hanya "ada tepi / tidak" tanpa informasi **arah**. Filter Gabor menghasilkan arah garis di tiap titik, yang dipakai untuk pencocokan, dan sesuai dengan metode di jurnal palmprint. Canny boleh ditampilkan sebagai pembanding visual (`cv2.Canny(roi, 30, 90)`) tetapi tidak ikut menentukan hasil pengenalan.

## 4. Bagaimana sistem membedakan orang

Garis tangan **tidak mengandung nama**. Sistem menyimpan **kode angka** (peta arah garis) bersama nama yang diketik saat mendaftar.

1. **Daftar**: 8 sampel telapak -> 8 kode -> disimpan di bawah satu nama.
2. **Scan**: hitung kode baru, bandingkan dengan semua orang terdaftar. Jarak ke satu orang = jarak ke sampel pendaftarannya yang **paling mirip**.
3. **Keputusan**: ambil orang dengan jarak terkecil. Jika jaraknya masih di atas **batas**, jawabannya "tidak dikenal".

Skala jarak: 0 = identik, sekitar 0.5 = pola acak. Batas yang baik **harus disetel dari pengujian sendiri** (lihat bagian 7), bukan ditebak.

Perbandingan dengan wajah: konsepnya sama (kode + nama, cocokkan saat scan), hanya bagian tubuhnya yang berbeda. Telapak tidak merekam wajah.

## 5. Jalur 1 (klasik) vs Jalur 2 (deep learning)

| | Jalur 1 (dipakai di sini) | Jalur 2 (pengembangan) |
|---|---|---|
| Cara kerja | Rumus tetap: filter Gabor + jarak | CNN belajar dari contoh |
| Dataset besar | Tidak perlu | Perlu |
| Training / GPU | Tidak perlu | Perlu (Colab/Kaggle cukup) |
| Pendaftaran orang baru | Simpan kode | Simpan embedding |
| Akurasi | Baik di kondisi terkontrol | Umumnya lebih tinggi dan lebih tahan variasi |

## 6. Apakah dataset dibutuhkan?

**Untuk menjalankan demo: tidak.** Sistem tidak dilatih dari apa pun. Hanya data orang yang didaftarkan lewat `daftar.py` yang dipakai, dan itu hanya disimpan.

Dataset baru berguna untuk **evaluasi (opsional)**, yaitu mendapat angka akurasi yang lebih kuat daripada mencoba dengan beberapa teman:

- **11k Hands** (Afifi, 2019): 11.076 foto tangan, 190 orang, sisi punggung dan telapak, ada kolom `id` dan `aspectOfHand` di `HandInfo.csv`. Hanya pakai foto **palmar** (telapak). Halaman proyek: `https://sites.google.com/view/11khands`, kode: `https://github.com/mahmoudnafifi/11K-Hands`. Ada juga salinan di Kaggle ("Hands and Palm Images Dataset").
- **IIT Delhi Touchless Palmprint v1.0**: perlu mengisi formulir aplikasi lewat `https://www4.comp.polyu.edu.hk/~csajaykr/IITD/Database_Palm.htm`; tidak untuk komersial.
- **Tongji, CASIA, PolyU**: biasanya perlu menghubungi atau menyetujui perjanjian dari pembuatnya.

Ketersediaan dan lisensi dataset dapat berubah; periksa halaman resminya. Dataset dipakai sesuai syarat penggunaannya (umumnya akademik).

Dataset juga diperlukan jika nanti membangun **Jalur 2** (deep learning) dan untuk membandingkan kedua jalur.

## 7. Cara menyetel batas dan menguji sistem

Parameter filter Gabor di `palm.py` adalah nilai awal yang masuk akal, **bukan hasil penyetelan**, dan sistem belum diuji pada data skala besar.

1. Daftarkan 2-3 orang (atau tangan kiri dan kanan Anda sendiri).
2. Scan tangan **yang sama** beberapa kali, catat jaraknya.
3. Scan tangan **orang lain / yang belum terdaftar**, catat jaraknya.
4. Atur batas dengan `+` / `-` ke titik di antara kedua rentang.
5. Uji juga: tangan kiri vs kanan orang yang sama harus tidak dikenali sebagai satu orang.

Tabel hasil (isi dari pengujian nyata):

| Skenario | Jumlah percobaan | Benar | Jarak rata-rata |
|---|---|---|---|
| Tangan sama (terdaftar) | [ ] | [ ] | [ ] |
| Orang lain (terdaftar) | [ ] | [ ] | [ ] |
| Belum terdaftar | [ ] | [ ] | [ ] |

Jika hasil kurang baik, urutan perbaikan: (1) cahaya merata dan latar polos, (2) periksa pratinjau ROI di pojok kiri atas, pastikan yang terpotong adalah tengah telapak dengan garis terlihat, (3) daftar dan scan di tempat serta kamera yang sama.

## 8. Narasi presentasi

### Judul
**Pengenalan Identitas Berdasarkan Pola Telapak Tangan dengan Computer Vision**

### Masalah
Kita sering membuktikan identitas (membuka ponsel, masuk ruangan, transaksi). Kata sandi, kartu, dan PIN bisa lupa, hilang, dipinjam, atau dicuri. **Biometrik** memakai ciri tubuh yang tidak perlu diingat atau dibawa. Proyek ini membahas satu alternatif: telapak tangan.

### Kenapa telapak tangan
Telapak memuat tiga garis utama, ratusan garis halus, dan lipatan kulit, dengan kombinasi yang berbeda antar orang. Telapak sudah lama diteliti sebagai biometrik, dengan banyak jurnal dan dataset publik. Dibanding wajah: tidak merekam wajah (lebih nyaman bagi privasi), areanya luas dan kaya ciri, dan cukup dengan kamera biasa tanpa menyentuh alat.

### Kegunaan
Kontrol akses (pintu lab/kantor), presensi tanpa titip absen, verifikasi transaksi, dan sebagai pelengkap PIN/kartu untuk keamanan berlapis. Untuk proyek ini yang ditunjukkan adalah pengenalan identitas sederhana: daftar lalu dikenali kembali. (Jika ingin menyebut produk komersial tertentu, verifikasi dulu sumber terbarunya.)

### Cara kerja (ringkas)
1. Kamera menemukan tangan; telapak diluruskan dan dipotong di bagian tengah.
2. Enam filter Gabor mencatat arah garis di tiap titik, menghasilkan peta angka (Competitive Code, Kong & Zhang 2004).
3. Peta baru dibandingkan dengan yang tersimpan; jarak kecil berarti orang yang sama, jarak besar berarti "tidak dikenal".

Tidak ada pelatihan model.

### Demo
1. Pendaftaran dengan persetujuan; hanya kode angka yang disimpan, bukan foto.
2. Scan: muncul nama dan nilai jarak.
3. Pembanding: telapak orang yang belum terdaftar menghasilkan "tidak dikenal".

Hasil pengujian: **[isi dari tabel bagian 7]**.

### Keterbatasan
- Bergantung pada cahaya, fokus, dan posisi tangan.
- Pengujian berskala kecil dengan webcam biasa; tidak bisa disamakan dengan angka jurnal (alat khusus, ribuan sampel).
- Luka, keringat berlebih, atau penuaan dapat memengaruhi hasil.
- Prototipe pembelajaran, belum layak sebagai pengaman utama.

### Privasi dan etika
Pola telapak adalah data biometrik: persetujuan sebelum mendaftar, simpan kode saja (bukan foto), data dapat dihapus kapan saja, dan seluruh data demo dihapus setelah presentasi.

### Penutup dan pengembangan
Dengan kamera biasa dan pengolahan citra klasik, pola telapak dapat membedakan orang. Pengembangan: evaluasi pada dataset publik (11k Hands) dan perbandingan dengan deep learning (Jalur 2).

## 9. Rujukan

Pastikan detail (halaman, tahun, DOI) diverifikasi di Google Scholar sebelum dikutip.

- Kong, A. W.-K., & Zhang, D. (2004). *Competitive Coding Scheme for Palmprint Verification*. ICPR 2004, hlm. 520-523. **(metode inti)**
- Zhang, D., Kong, A. W.-K., You, J., & Wong, M. (2003). *Online Palmprint Identification*. IEEE TPAMI, 25(9), 1041-1050.
- Kong, A. W.-K. (2007). *Palmprint Identification Based on Generalization of IrisCode*. Disertasi, University of Waterloo.
- Yue, F., Zuo, W., Zhang, D., & Wang, K. (2009). *Orientation selection using modified FCM for competitive code-based palmprint recognition*. Pattern Recognition, 42(11). (menyimpulkan competitive code dengan 6 orientasi sebagai pilihan optimal)
- Guo, Z., Zuo, W., Zhang, L., & Zhang, D. (2009). *A unified distance measurement for orientation coding in palmprint verification*. Neurocomputing.
- Afifi, M. (2019). *11K Hands: gender recognition and biometric identification using a large dataset of hand images*. Multimedia Tools and Applications. doi:10.1007/s11042-019-7424-8

Repo terkait (periksa lisensi dan tanggal pembaruan sebelum dipakai):
- `github.com/Leosocy/EDCC-Palmprint-Recognition` (implementasi berbasis competitive code, OpenCV)
- `github.com/Zi-YuanYang/CO3Net` (PyTorch, Jalur 2)

## 10. Catatan jujur tentang kode ini

- Perhitungan kode dan jarak sudah diuji dengan data sintetis (jarak diri sendiri 0, data acak sekitar 0.49).
- Pemotongan ROI diuji dengan titik tangan tiruan. Kinerja dengan tangan dan kamera sungguhan bergantung pada kondisi Anda.
- Parameter filter Gabor (ukuran 21x21, sigma 4, panjang gelombang 10, gamma 0.5) dan ukuran kotak ROI adalah nilai awal yang disetel sendiri, bukan nilai persis dari jurnal.
