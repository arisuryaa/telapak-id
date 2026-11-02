# Telapak ID Web — Rencana Implementasi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memindahkan Telapak ID dari terminal/OpenCV ke website (Flask + React/Tailwind + MySQL) dengan kamera berpanduan, validasi tangan, FPS, timeline 8 langkah pemrosesan, dan halaman detail orang.

**Architecture:** Browser menjalankan MediaPipe Tasks Vision JS untuk overlay kerangka + kotak ROI, validasi live, dan FPS; saat valid, frame (tidak dicermin) dikirim ke Flask. Flask memakai `palm.py` (direfaktor tanpa mengubah matematika) untuk deteksi ulang, validasi ulang, ROI, CLAHE, Gabor, Competitive Code, gambar tiap langkah, dan pencocokan dengan data di MySQL via SQLAlchemy.

**Tech Stack:** Python 3.10.6, Flask 3.1, SQLAlchemy 2.0, PyMySQL, python-dotenv, mediapipe 0.10.14, opencv-contrib (dari mediapipe), numpy<2, pytest · Node 24, Vite, React, Tailwind 4 (`@tailwindcss/vite`), react-router 7, `@mediapipe/tasks-vision@0.10.21`, vitest.

**Spec:** [docs/superpowers/specs/2026-11-02-telapak-web-design.md](../specs/2026-11-02-telapak-web-design.md)

## Global Constraints

- Semua teks antarmuka, pesan galat API, dan README dalam **Bahasa Indonesia**.
- `mediapipe==0.10.14` (API `mp.solutions`), `numpy<2`, Python 3.10. **Jangan** cantumkan `opencv-python` di requirements (bentrok dengan `opencv-contrib-python` milik mediapipe).
- Matematika pengenalan tidak berubah: Gabor 21×21, sigma 4.0, lambd 10.0, gamma 0.5, psi 0, 6 arah, `k -= k.mean()`; CLAHE clipLimit 2.0 tile 4×4; ROI 128×128; jarak sudut dengan geser ±3; `jarak_ke_orang` = minimum ke 8 sampel.
- Foto tidak pernah disimpan ke disk atau database. Tidak ada riwayat scan.
- Semua aset runtime lokal (model + WASM MediaPipe di `frontend/public/mediapipe/`); tidak ada CDN saat runtime.
- Frame yang dikirim ke server **tidak dicermin**; video di layar dicermin dengan CSS `scale-x-[-1]` (overlay ikut dicermin dengan cara yang sama).
- Label MediaPipe pada frame tidak dicermin: `"Left"` → tangan **kanan**, `"Right"` → tangan **kiri** (berlaku di browser dan server).
- Batas default 0.38, rentang 0.10–0.50. Pendaftaran = 8 sampel valid, jeda ±0.8 s. Foto otomatis setelah valid ±1 s.
- Status orang: `mahasiswa`, `dosen`, `staf`, `tamu`. Sisi: `kiri`, `kanan`.
- `DATABASE_URL` dari `backend/.env`, default `mysql+pymysql://root:@localhost:3306/telapak_id`.
- Commit message diakhiri baris: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Perintah backend dijalankan dari folder `backend/` (`python -m pytest -q`, `python app.py`); frontend dari `frontend/`.

## Review Focus

1. **MySQL Laragon belum dinyalakan** → `python app.py` mencetak pesan jelas ("MySQL tidak bisa dihubungi, nyalakan Laragon…") dan keluar, bukan traceback. Tes: Task 4 `test_engine_mysql_mati`.
2. **Scan saat belum ada yang terdaftar** → langkah 1–7 tetap tampil, hasil `tidak_dikenal` dengan pesan "Belum ada yang terdaftar". Tes: Task 5 `test_scan_galeri_kosong`.
3. **Isian form tidak wajar** (nama kosong, umur bukan angka/≤0/>120, status di luar daftar, tanpa persetujuan) → 400 dengan pesan. Tes: Task 5 `test_simpan_orang_input_salah`.
4. **Tangan yang sama didaftarkan lagi** → 409 `perlu_konfirmasi`; dengan `ganti: true` data lama diganti. Tes: Task 5 `test_simpan_telapak_duplikat`.
5. **Izin kamera ditolak / kamera tidak ada** → pesan jelas di area kamera, bukan layar hitam. Cek manual: Task 7 Step 6.

---

## Struktur file

```
.gitignore
backend/
  .env.example
  requirements.txt
  palm.py            # inti CV (dipindah dari root, direfaktor: keluaran antara)
  validasi.py        # aturan jari terbuka, arah telapak, sisi, kualitas ROI
  pipeline.py        # baca frame + analisis() berurutan, menandai tahap gagal
  langkah.py         # susun 8 langkah (gambar data URL + angka + teks)
  db.py              # model SQLAlchemy + fungsi data
  app.py             # Flask API
  tests/
    fixtures/landmark_uji.json, roi_uji.npy, kode_asli.npy
    test_palm.py test_validasi.py test_pipeline.py test_db.py test_app.py
frontend/
  package.json vite.config.js index.html
  scripts/siapkan-mediapipe.mjs
  src/main.jsx App.jsx index.css
  src/lib/validasi.js validasi.test.js api.js
  src/hooks/useHandTracker.js
  src/components/KameraTangan.jsx GrafikJarak.jsx
  src/pages/Scan.jsx Hasil.jsx DetailOrang.jsx Daftar.jsx DataTerdaftar.jsx
README.md
```
Dihapus di Task 11: `palm.py` (root), `daftar.py`, `scan.py`, `hapus.py`, `requirements.txt` (root), `__pycache__/`.

---

### Task 1: Repo awal + refaktor `palm.py` ke `backend/`

**Files:**
- Create: `.gitignore`, `backend/palm.py`, `backend/requirements.txt`, `backend/tests/test_palm.py`, `backend/tests/fixtures/roi_uji.npy`, `backend/tests/fixtures/kode_asli.npy`

**Interfaces:**
- Produces (`backend/palm.py`):
  - `UKURAN = 128`, `GABOR = {"ukuran": 21, "sigma": 4.0, "lambd": 10.0, "gamma": 0.5, "arah": 6}`
  - `deteksi_tangan(frame_bgr) -> tuple[list, str] | None` — (21 landmark ber-atribut `.x .y` ternormalisasi, label MediaPipe `"Left"|"Right"`). Memakai `mp.solutions.hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.6)`.
  - `ambil_roi_detail(frame_bgr, lm) -> dict | None` — kunci `rot` (BGR diputar), `kotak` (x1, y1, x2, y2 di frame diputar), `sudut` (float, derajat), `roi` (uint8 128×128).
  - `ambil_roi(frame_bgr, lm) -> np.ndarray | None` — pembungkus, `ambil_roi_detail(...)["roi"]`.
  - `hitung_kode_detail(roi_gray) -> dict` — kunci `clahe` (uint8 128×128, hasil CLAHE sebelum normalisasi), `respons` (float32 6×128×128), `kode` (uint8 128×128).
  - `hitung_kode(roi_gray) -> np.ndarray`, `jarak_kode(a, b, geser=3) -> float`, `jarak_ke_orang(kode, daftar_kode) -> float` — perilaku sama persis dengan versi lama.

- [ ] **Step 1: Siapkan repo.** Buat `.gitignore` berisi `__pycache__/`, `*.pyc`, `node_modules/`, `frontend/dist/`, `frontend/public/mediapipe/`, `.env`, `data_terdaftar/`, `.superpowers/`, `.pytest_cache/`. Commit kode lama apa adanya di `master` (`git add .gitignore README.md *.py requirements.txt docs && git commit -m "chore: kode awal versi terminal"`), lalu `git checkout -b web`.

- [ ] **Step 2: Buat fixture emas dari `palm.py` lama** (sebelum dipindah). Dari root repo:

```bash
mkdir -p backend/tests/fixtures
python -c "import numpy as np, cv2, palm; rng=np.random.default_rng(0); r=cv2.GaussianBlur(rng.integers(0,256,(128,128),dtype=np.uint8),(5,5),0); np.save('backend/tests/fixtures/roi_uji.npy', r); np.save('backend/tests/fixtures/kode_asli.npy', palm.hitung_kode(r))"
```
Expected: dua file `.npy` tercipta.

- [ ] **Step 3: Tulis tes yang gagal** `backend/tests/test_palm.py`:

```python
FIX = Path(__file__).parent / "fixtures"

def test_kode_sama_dengan_versi_lama():
    roi = np.load(FIX / "roi_uji.npy")
    assert np.array_equal(palm.hitung_kode(roi), np.load(FIX / "kode_asli.npy"))

def test_kode_detail_konsisten():
    roi = np.load(FIX / "roi_uji.npy")
    d = palm.hitung_kode_detail(roi)
    assert d["respons"].shape == (6, 128, 128) and d["clahe"].dtype == np.uint8
    assert np.array_equal(d["kode"], palm.hitung_kode(roi))

def test_jarak_diri_nol_acak_setengah():
    rng = np.random.default_rng(1)
    a = rng.integers(0, 6, (128, 128), dtype=np.uint8)
    b = rng.integers(0, 6, (128, 128), dtype=np.uint8)
    assert palm.jarak_kode(a, a) == 0.0
    assert 0.40 < palm.jarak_kode(a, b) < 0.55

def test_roi_dari_landmark_tiruan():
    # tangan kanan terbuka dari fixtures/landmark_uji.json dibuat di Task 2;
    # di sini cukup titik 0, 5, 17 pada frame 640x480
    lm = titik_tiruan({0: (320, 420), 5: (360, 300), 17: (272, 312)}, 640, 480)
    d = palm.ambil_roi_detail(np.zeros((480, 640, 3), np.uint8), lm)
    assert d["roi"].shape == (128, 128) and isinstance(d["sudut"], float)

def test_roi_none_jika_terlalu_kecil():
    lm = titik_tiruan({0: (320, 420), 5: (330, 300), 17: (310, 300)}, 640, 480)
    assert palm.ambil_roi(np.zeros((480, 640, 3), np.uint8), lm) is None
```
`titik_tiruan(dict_px, w, h)` adalah helper di file tes: list 21 `SimpleNamespace(x, y, z=0)` ternormalisasi (titik yang tidak disebut = titik 0).

- [ ] **Step 4: Jalankan** `cd backend && python -m pytest tests/test_palm.py -q` → FAIL (`ModuleNotFoundError: palm`).

- [ ] **Step 5: Buat `backend/palm.py`** dengan antarmuka di atas: salin isi `palm.py` lama, pecah `ambil_roi` dan `hitung_kode` menjadi versi `_detail` yang mengembalikan nilai antara, ganti `cari_landmark` dengan `deteksi_tangan` (ambil label dari `hasil.multi_handedness[0].classification[0].label`). `backend/requirements.txt`: `mediapipe==0.10.14`, `numpy<2`, `flask==3.1.1`, `sqlalchemy>=2.0,<2.1`, `pymysql`, `cryptography`, `python-dotenv`, `pytest`. Jalankan `pip install -r requirements.txt`.

- [ ] **Step 6: Jalankan** `python -m pytest tests/test_palm.py -q` → 5 passed.

- [ ] **Step 7: Commit** `feat(backend): pindah palm.py dan keluarkan nilai antara tanpa ubah rumus`.

---

### Task 2: `validasi.py` — aturan tangan dan kualitas ROI

**Files:**
- Create: `backend/validasi.py`, `backend/tests/test_validasi.py`, `backend/tests/fixtures/landmark_uji.json`

**Interfaces:**
- Produces:
  - `AMBANG = {"rasio_jari": 1.1, "rasio_jempol": 0.7, "terang_min": 40, "terang_max": 215, "tajam_min": 20.0}`
  - `sisi_dari_label(label: str) -> str` — `"Left"`→`"kanan"`, `"Right"`→`"kiri"`.
  - `jari_terbuka(lm, w: int, h: int) -> bool` — untuk pasangan (ujung, PIP) = (8,6), (12,10), (16,14), (20,18): `|ujung−0| > rasio_jari × |PIP−0|`; ibu jari: `|4−5| > rasio_jempol × |5−17|`. Semua dalam piksel (`x*w`, `y*h`).
  - `menghadap_kamera(lm, sisi: str, w: int, h: int) -> bool` — `z = cross(p5−p0, p17−p0)` (koordinat gambar, y ke bawah); telapak jika (`sisi=="kanan"` dan `z<0`) atau (`sisi=="kiri"` dan `z>0`).
  - `kualitas_roi(roi_gray) -> str | None` — `None` = lolos; rata-rata < `terang_min` → `"Foto terlalu gelap, tambah cahaya"`; > `terang_max` → `"Foto terlalu terang"`; `cv2.Laplacian(roi, cv2.CV_64F).var() < tajam_min` → `"Foto kurang jelas, tahan tangan lebih diam"`.

- [ ] **Step 1: Buat fixture** `landmark_uji.json`: `{"lebar": 640, "tinggi": 480, "terbuka_kanan": [[x,y]×21], "kepal_kanan": [...], "punggung_kanan": [...]}` dalam piksel. `punggung_kanan` = `terbuka_kanan` dengan `x → 640 − x`.

| titik | terbuka_kanan | kepal_kanan |
|---|---|---|
| 0 | 320,420 | 320,420 |
| 1–4 | 365,400 · 395,370 · 418,342 · 440,318 | 365,400 · 390,375 · 385,345 · 362,328 |
| 5–8 | 360,300 · 366,245 · 369,210 · 372,180 | 360,300 · 368,265 · 360,290 · 352,315 |
| 9–12 | 330,290 · 331,230 · 332,192 · 333,160 | 330,290 · 334,255 · 328,282 · 325,310 |
| 13–16 | 300,295 · 296,240 · 293,205 · 291,178 | 300,295 · 300,262 · 296,288 · 294,312 |
| 17–20 | 272,312 · 262,268 · 256,242 · 251,220 | 272,312 · 270,282 · 268,302 · 268,322 |

File ini juga dipakai tes frontend (Task 6).

- [ ] **Step 2: Tulis tes yang gagal** `test_validasi.py` (helper memuat fixture menjadi list `SimpleNamespace(x=px/640, y=py/480)`):

```python
def test_sisi_dari_label():
    assert sisi_dari_label("Left") == "kanan" and sisi_dari_label("Right") == "kiri"

def test_tangan_terbuka_lolos():
    assert jari_terbuka(lm("terbuka_kanan"), 640, 480)

def test_tangan_mengepal_ditolak():
    assert not jari_terbuka(lm("kepal_kanan"), 640, 480)

def test_telapak_vs_punggung():
    assert menghadap_kamera(lm("terbuka_kanan"), "kanan", 640, 480)
    assert not menghadap_kamera(lm("punggung_kanan"), "kanan", 640, 480)
    assert menghadap_kamera(lm("punggung_kanan"), "kiri", 640, 480)

def test_kualitas_roi():
    assert kualitas_roi(np.full((128, 128), 10, np.uint8)) == "Foto terlalu gelap, tambah cahaya"
    assert kualitas_roi(np.full((128, 128), 250, np.uint8)) == "Foto terlalu terang"
    assert kualitas_roi(np.full((128, 128), 128, np.uint8)) == "Foto kurang jelas, tahan tangan lebih diam"
    assert kualitas_roi(np.load(FIX / "roi_uji.npy")) is None
```

- [ ] **Step 3: Jalankan** `python -m pytest tests/test_validasi.py -q` → FAIL (import).
- [ ] **Step 4: Implementasi** `validasi.py` sesuai antarmuka.
- [ ] **Step 5: Jalankan** → 5 passed. Jika `roi_uji.npy` gagal `tajam_min`, turunkan tes ke ROI bertekstur lain, bukan menaikkan ambang tanpa alasan.
- [ ] **Step 6: Commit** `feat(backend): validasi jari terbuka, arah telapak, kualitas ROI`.

---

### Task 3: `pipeline.py` + `langkah.py`

**Files:**
- Create: `backend/pipeline.py`, `backend/langkah.py`, `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: Task 1 `palm.*`, Task 2 `validasi.*`.
- Produces (`pipeline.py`):
  - `baca_frame(data_url: str) -> np.ndarray | None` — terima `data:image/...;base64,...` atau base64 polos; `None` jika gagal didekode.
  - `@dataclass Analisis`: `frame`, `lm=None`, `label=None`, `sisi=None`, `roi_detail=None`, `kode_detail=None`, `tahap: int = 1`, `gagal: str | None = None`. `kode` property → `kode_detail["kode"]` atau `None`.
  - `analisis(frame_bgr, deteksi=palm.deteksi_tangan) -> Analisis` — urutan dan pesan gagal persis:
    1. `deteksi` None → `gagal="Tangan tidak terdeteksi"`, `tahap=1`
    2. `tahap=2`; `not jari_terbuka` → `"Buka semua jari"`; `not menghadap_kamera` → `"Tunjukkan telapak tangan, bukan punggung tangan"`; `ambil_roi_detail` None → `"Tangan terlalu dekat/jauh atau keluar dari bingkai"`
    3. `tahap=4`; `kualitas_roi` tidak None → pesan itu
    4. `tahap=7`; `kode_detail = hitung_kode_detail(roi)`
- Produces (`langkah.py`):
  - `WARNA_KODE = ["#ef4444", "#f59e0b", "#22c55e", "#06b6d4", "#3b82f6", "#a855f7"]` (arah 0°…150°)
  - `ke_data_url(img: np.ndarray, fmt: str = ".png") -> str`
  - `susun_langkah(a: Analisis, jarak: list | None = None, batas: float | None = None) -> list[dict]` — tiap langkah `{"no", "judul", "penjelasan", "gambar": [{"label", "src"}], "angka": {str: str|number}}`; langkah 1..`a.tahap` (lewati 3 bila roi_detail None); langkah 8 hanya bila `jarak is not None`. Langkah 7 punya kunci tambahan `"legenda": [{"arah": "0°", "warna": "#ef4444"}, ...]`.

| no | judul | gambar | angka |
|---|---|---|---|
| 1 | Foto dari kamera | frame (JPEG) | resolusi "W×H" |
| 2 | Deteksi tangan | frame + 21 titik & garis (`mp.solutions.hands.HAND_CONNECTIONS`) | titik 21, sisi |
| 3 | Diluruskan | `rot` + persegi `kotak` | sudut putar (°, 1 desimal) |
| 4 | ROI grayscale | `roi` | ukuran "128×128" |
| 5 | CLAHE + normalisasi | `clahe` | rata-rata, simpangan (dari `clahe`) |
| 6 | Filter Gabor 6 arah | 6 gambar `respons[j]` min-max → 0–255, label "0°"…"150°" | `GABOR` |
| 7 | Competitive Code | kode → warna `WARNA_KODE` | jumlah arah 6 |
| 8 | Pencocokan | — (grafik di frontend) | jarak terkecil, batas |

Penjelasan 1–2 kalimat per langkah ditulis builder (Bahasa Indonesia, untuk dosen).

- [ ] **Step 1: Tulis tes yang gagal** `test_pipeline.py`. Detektor palsu: `lambda f: (lm("terbuka_kanan"), "Left")`, frame = `np.random.default_rng(0)` noise 480×640×3 di-blur (agar ROI bertekstur).

```python
def test_baca_frame_rusak():
    assert baca_frame("data:image/jpeg;base64,bukan-gambar") is None

def test_baca_frame_bolak_balik():
    url = ke_data_url(frame_uji(), ".jpg")
    assert baca_frame(url).shape == (480, 640, 3)

def test_tanpa_tangan():
    a = analisis(frame_uji(), deteksi=lambda f: None)
    assert (a.tahap, a.gagal) == (1, "Tangan tidak terdeteksi")
    assert [l["no"] for l in susun_langkah(a)] == [1]

def test_kepal_ditolak_di_server():
    a = analisis(frame_uji(), deteksi=lambda f: (lm("kepal_kanan"), "Left"))
    assert (a.tahap, a.gagal, a.kode) == (2, "Buka semua jari", None)

def test_punggung_ditolak_di_server():
    a = analisis(frame_uji(), deteksi=lambda f: (lm("punggung_kanan"), "Left"))
    assert a.gagal == "Tunjukkan telapak tangan, bukan punggung tangan"

def test_lengkap_tujuh_langkah_dan_kode_jujur():
    a = analisis(frame_uji(), deteksi=lambda f: (lm("terbuka_kanan"), "Left"))
    assert a.gagal is None and a.sisi == "kanan"
    assert np.array_equal(a.kode, palm.hitung_kode(a.roi_detail["roi"]))
    ls = susun_langkah(a, jarak=[], batas=0.38)
    assert [l["no"] for l in ls] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert len(ls[5]["gambar"]) == 6 and len(ls[6]["legenda"]) == 6
    assert all(g["src"].startswith("data:image/") for l in ls for g in l["gambar"])
```

- [ ] **Step 2: Jalankan** `python -m pytest tests/test_pipeline.py -q` → FAIL.
- [ ] **Step 3: Implementasi** `pipeline.py` dan `langkah.py` sesuai antarmuka. Frame (langkah 1–3) di-encode JPEG kualitas 85; sisanya PNG.
- [ ] **Step 4: Jalankan** → 6 passed; lalu `python -m pytest -q` → semua lolos.
- [ ] **Step 5: Commit** `feat(backend): analisis bertahap dan gambar 8 langkah`.

---

### Task 4: `db.py` — model dan fungsi data

**Files:**
- Create: `backend/db.py`, `backend/tests/test_db.py`, `backend/.env.example`

**Interfaces:**
- Produces:
  - `STATUS = ("mahasiswa", "dosen", "staf", "tamu")`, `SISI = ("kiri", "kanan")`
  - `class DatabaseTidakTersedia(Exception)`, `class TelapakSudahAda(Exception)`
  - Model `Orang` (`id`, `nama` String(100), `umur` Integer, `status` Enum(STATUS), `dibuat_pada` DateTime default now, relasi `telapak` cascade `"all, delete-orphan"`) dan `Telapak` (`id`, `orang_id` FK `ondelete="CASCADE"`, `sisi` Enum(SISI), `kode` = `LargeBinary().with_variant(mysql.LONGBLOB(), "mysql")` — **wajib**, BLOB biasa MySQL hanya 64 KB sedangkan kode 128 KB; `dibuat_pada`; `UniqueConstraint("orang_id", "sisi")`).
  - `buat_engine(url: str) -> Engine` — untuk URL MySQL: hubungkan ke server tanpa nama database, `CREATE DATABASE IF NOT EXISTS <nama> CHARACTER SET utf8mb4`, lalu `create_all`. `OperationalError` → `DatabaseTidakTersedia("MySQL tidak bisa dihubungi di <host>:<port>. Nyalakan MySQL di Laragon lalu jalankan ulang.")`.
  - `kode_ke_bytes(kode: np.ndarray) -> bytes`, `bytes_ke_kode(b: bytes) -> np.ndarray` (uint8, `(-1, 128, 128)`)
  - `tambah_orang(s, nama, umur, status) -> Orang`
  - `simpan_telapak(s, orang_id, sisi, kode, ganti=False) -> Telapak` — sudah ada & `ganti=False` → `TelapakSudahAda`; `ganti=True` → kode diganti.
  - `muat_galeri(s) -> list[dict]` — `{"telapak_id", "orang_id", "nama", "sisi", "kode": ndarray (8,128,128)}`
  - `orang_ke_dict(o) -> dict` — `{"id", "nama", "umur", "status", "tangan": [sisi terurut], "dibuat_pada": ISO}`
  - `daftar_orang(s) -> list[dict]`, `ambil_orang(s, id) -> dict | None`, `hapus_orang(s, id) -> bool`, `hapus_semua(s) -> int` (jumlah orang)

- [ ] **Step 1: Tulis tes yang gagal** (`engine = buat_engine("sqlite://")`, `Session = sessionmaker(engine)`):

```python
def test_simpan_muat_kode_utuh(): # tambah_orang + simpan_telapak; muat_galeri()[0]["kode"] == kode asli (8,128,128)
def test_duplikat_dan_ganti():    # simpan sisi sama → TelapakSudahAda; ganti=True → kode baru terbaca
def test_dua_tangan_satu_orang(): # kiri & kanan → ambil_orang(...)["tangan"] == ["kanan", "kiri"]
def test_hapus_kaskade():         # hapus_orang → muat_galeri() == [] ; hapus_semua mengembalikan jumlah
def test_engine_mysql_mati():
    with pytest.raises(DatabaseTidakTersedia, match="Laragon"):
        buat_engine("mysql+pymysql://root:@127.0.0.1:1/telapak_id")
```
Tulis assertion lengkap sesuai komentar.

- [ ] **Step 2: Jalankan** `python -m pytest tests/test_db.py -q` → FAIL.
- [ ] **Step 3: Implementasi** `db.py`. `.env.example`: `DATABASE_URL=mysql+pymysql://root:@localhost:3306/telapak_id`.
- [ ] **Step 4: Jalankan** → 5 passed.
- [ ] **Step 5: Commit** `feat(backend): model MySQL orang dan telapak`.

---

### Task 5: `app.py` — Flask API

**Files:**
- Create: `backend/app.py`, `backend/tests/test_app.py`

**Interfaces:**
- Consumes: Task 3 `baca_frame`, `analisis`, `susun_langkah`; Task 4 seluruh `db.*`; `palm.jarak_ke_orang`.
- Produces: `create_app(database_url: str | None = None, deteksi=palm.deteksi_tangan) -> Flask` (`database_url` None → `os.environ["DATABASE_URL"]` via `load_dotenv()`, fallback default). Blok `if __name__ == "__main__":` menangkap `DatabaseTidakTersedia`, mencetak pesannya, `sys.exit(1)`; jika berhasil `app.run(port=5000)`.

| Metode | Path | Body | Respons |
|---|---|---|---|
| POST | `/api/scan` | `{frame, batas}` | 200 `{"langkah", "jarak": [{"telapak_id","orang_id","nama","sisi","jarak"}] urut naik, "batas", "hasil": {"status": "dikenali"\|"tidak_dikenal"\|"gagal", "pesan", "orang_id"?, "nama"?, "sisi"?, "jarak"?}}` |
| POST | `/api/sampel` | `{frame}` | 200 `{"valid", "pesan", "sisi", "kode"}` (`kode` = base64 dari `kode.tobytes()`, 16384 byte) |
| POST | `/api/orang` | `{orang_id?, nama?, umur?, status?, sisi, persetujuan, kode: [8], sisi_terdeteksi: [8], ganti?}` | 201 `{"orang"}` · 400 · 404 · 409 `{"pesan","perlu_konfirmasi": true}` |
| GET | `/api/orang` | — | `[orang_ke_dict]` |
| GET | `/api/orang/<id>` | — | dict · 404 |
| DELETE | `/api/orang/<id>` | — | 204 · 404 |
| DELETE | `/api/orang` | — | `{"dihapus": n}` |

Aturan:
- Semua galat berbentuk `{"pesan": "..."}`. Frame tak terbaca → 400 `"Gambar tidak valid"`.
- `batas` dijepit ke [0.10, 0.50], default 0.38. Hasil `gagal` → `pesan = a.gagal`, `jarak = []`, tanpa langkah 8. Galeri kosong → `tidak_dikenal`, `"Belum ada yang terdaftar"`. Jarak terkecil `< batas` → `dikenali` (`pesan` "Dikenali sebagai <nama>"), selain itu `tidak_dikenal` (`"Tidak dikenal"`).
- `/api/orang` validasi berurutan: `persetujuan is True` ("Pendaftaran butuh persetujuan"); `sisi` ∈ SISI; jika tanpa `orang_id`: `nama` tidak kosong ≤100, `umur` int 1–120, `status` ∈ STATUS; `kode` tepat 8 dan tiap item 16384 byte ("Data sampel tidak lengkap"); mayoritas `sisi_terdeteksi` == `sisi`, jika beda → 400 `"Tangan yang terdeteksi adalah tangan <x>, bukan <sisi>"`. `orang_id` tak dikenal → 404. Orang baru + `TelapakSudahAda` tidak mungkin terjadi; orang lama → 409 kecuali `ganti`. Orang baru dibuat dalam transaksi yang sama dengan telapaknya (gagal = tidak ada yang tersimpan).

- [ ] **Step 1: Tulis tes yang gagal.** Fixture `client` = `create_app("sqlite://", deteksi=detektor_palsu).test_client()`; detektor palsu bisa diganti per tes (mis. variabel global berisi nama landmark fixture atau `None`). Frame = data URL JPEG dari `frame_uji()` (Task 3).

```python
def test_scan_galeri_kosong(client):
    r = client.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()
    assert r["hasil"]["status"] == "tidak_dikenal"
    assert r["hasil"]["pesan"] == "Belum ada yang terdaftar"
    assert [l["no"] for l in r["langkah"]][:7] == [1, 2, 3, 4, 5, 6, 7]

def test_daftar_lalu_dikenali(client):
    s = client.post("/api/sampel", json={"frame": FRAME}).get_json()
    assert s["valid"] and s["sisi"] == "kanan"
    body = {"nama": "dewa", "umur": 21, "status": "mahasiswa", "sisi": "kanan",
            "persetujuan": True, "kode": [s["kode"]] * 8, "sisi_terdeteksi": ["kanan"] * 8}
    assert client.post("/api/orang", json=body).status_code == 201
    r = client.post("/api/scan", json={"frame": FRAME, "batas": 0.38}).get_json()
    assert r["hasil"]["status"] == "dikenali" and r["hasil"]["nama"] == "dewa"
    assert r["hasil"]["jarak"] == 0.0 and r["langkah"][-1]["no"] == 8

def test_kepal_tidak_pernah_dikenali(client):  # daftarkan dulu, lalu detektor → kepal_kanan
    # hasil.status == "gagal", pesan "Buka semua jari"; /api/sampel → valid False

def test_simpan_orang_input_salah(client):
    # masing-masing → 400: persetujuan False; nama ""; umur "dua puluh"; umur 0; umur 121;
    # status "presiden"; kode 7 item; sisi_terdeteksi mayoritas "kiri" untuk sisi "kanan"

def test_simpan_telapak_duplikat(client):
    # daftar orang, lalu POST lagi dengan orang_id & sisi sama → 409 perlu_konfirmasi True;
    # dengan ganti True → 201; GET /api/orang/<id> tangan == ["kanan"]

def test_frame_rusak(client):
    assert client.post("/api/scan", json={"frame": "xx"}).status_code == 400

def test_hapus(client):
    # DELETE /api/orang/<id> → 204, GET → 404; DELETE /api/orang → {"dihapus": n}
```
Tulis assertion lengkap sesuai komentar.

- [ ] **Step 2: Jalankan** `python -m pytest tests/test_app.py -q` → FAIL.
- [ ] **Step 3: Implementasi** `app.py`.
- [ ] **Step 4: Jalankan** `python -m pytest -q` → semua lolos.
- [ ] **Step 5: Cek manual MySQL mati:** dengan Laragon mati, `python app.py` → mencetak pesan "…Nyalakan MySQL di Laragon…" dan keluar kode 1 (tanpa traceback).
- [ ] **Step 6: Commit** `feat(backend): API scan, sampel, dan kelola orang`.

---

### Task 6: Kerangka frontend + `validasi.js`

**Files:**
- Create: `frontend/` (Vite React), `frontend/vite.config.js`, `frontend/scripts/siapkan-mediapipe.mjs`, `frontend/src/index.css`, `frontend/src/App.jsx`, `frontend/src/main.jsx`, `frontend/src/lib/validasi.js`, `frontend/src/lib/validasi.test.js`, halaman kosong `frontend/src/pages/*.jsx`

**Interfaces:**
- Consumes: `backend/tests/fixtures/landmark_uji.json` (impor JSON relatif di tes).
- Produces (`src/lib/validasi.js`), paralel dengan Python:
  - `AMBANG = { rasioJari: 1.1, rasioJempol: 0.7, lebarMin: 0.12, lebarMax: 0.45, gerakMax: 0.012, tahanMs: 1000, jedaMs: 800 }`
  - `sisiDariLabel(label) -> "kanan"|"kiri"`, `jariTerbuka(lm, w, h) -> bool`, `menghadapKamera(lm, sisi, w, h) -> bool` (rumus sama dengan Task 2)
  - `kotakRoi(lm, w, h) -> { titik: [[x,y]×4], didalam: bool }` — geometri `palm.ambil_roi` di frame asli: `c=(p5+p17)/2`, `s=|p17−p5|`, `u=(p17−p5)/s`, `n` tegak lurus `u` mengarah ke p0; sudut = `c ± u·s/2 + n·0.15s` dan `c ± u·s/2 + n·1.15s`; `didalam` = keempat sudut di dalam [0,w]×[0,h]. (Pendekatan; server tetap penentu.)
  - `rataGerak(lmA, lmB) -> number` (rata-rata jarak ternormalisasi 21 titik; `Infinity` jika `lmB` null)
  - `periksa(lm, label, lmSebelum, w, h) -> { terdeteksi, jari, menghadap, jarak, diam, semua, sisi, pesan }` — `jarak` = lebar |5−17|/w di [lebarMin, lebarMax] **dan** `kotakRoi.didalam`. `pesan` sesuai butir gagal pertama: "Letakkan telapak di depan kamera" · "Buka semua jari" · "Tunjukkan telapak tangan, bukan punggung tangan" · "Atur jarak tangan ke kamera" · "Tahan tangan agar diam" · (semua lolos) "Tahan..."

- [ ] **Step 1: Buat proyek.** `npm create vite@latest frontend -- --template react`, lalu di `frontend/`: `npm i react-router@7 @mediapipe/tasks-vision@0.10.21` dan `npm i -D tailwindcss@4 @tailwindcss/vite@4 vitest`. `vite.config.js`: plugin `react()` + `tailwindcss()`, `server.proxy = { "/api": "http://127.0.0.1:5000" }`, `test.environment = "node"`. `index.css`: `@import "tailwindcss";`. Script `package.json`: `"test": "vitest run"`, `"siapkan-mediapipe": "node scripts/siapkan-mediapipe.mjs"`, `"postinstall": "node scripts/siapkan-mediapipe.mjs"`.
- [ ] **Step 2: `siapkan-mediapipe.mjs`** menyalin `node_modules/@mediapipe/tasks-vision/wasm/*` ke `public/mediapipe/wasm/` dan mengunduh `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task` ke `public/mediapipe/hand_landmarker.task` bila belum ada. Jalankan `npm run siapkan-mediapipe` → kedua aset ada.
- [ ] **Step 3: `App.jsx`**: `BrowserRouter` dengan navigasi atas "Scan · Daftar · Data terdaftar" (`NavLink`) dan rute `/` Scan, `/hasil` Hasil, `/orang/:id` DetailOrang, `/daftar` Daftar, `/data` DataTerdaftar (halaman sementara berisi judul).
- [ ] **Step 4: Tulis tes yang gagal** `validasi.test.js` dengan fixture yang sama (dinormalisasi /640, /480):

```js
test("label → sisi", () => { expect(sisiDariLabel("Left")).toBe("kanan"); expect(sisiDariLabel("Right")).toBe("kiri") })
test("terbuka lolos, kepal ditolak", () => {
  expect(jariTerbuka(lm("terbuka_kanan"), 640, 480)).toBe(true)
  expect(jariTerbuka(lm("kepal_kanan"), 640, 480)).toBe(false)
})
test("telapak vs punggung", () => {
  expect(menghadapKamera(lm("terbuka_kanan"), "kanan", 640, 480)).toBe(true)
  expect(menghadapKamera(lm("punggung_kanan"), "kanan", 640, 480)).toBe(false)
})
test("periksa kepal → pesan buka jari", () => {
  const p = periksa(lm("kepal_kanan"), "Left", lm("kepal_kanan"), 640, 480)
  expect(p.semua).toBe(false); expect(p.pesan).toBe("Buka semua jari")
})
test("periksa terbuka diam → semua lolos", () => {
  const p = periksa(lm("terbuka_kanan"), "Left", lm("terbuka_kanan"), 640, 480)
  expect(p.semua).toBe(true); expect(p.sisi).toBe("kanan")
})
test("tanpa tangan", () => { expect(periksa(null, null, null, 640, 480).pesan).toBe("Letakkan telapak di depan kamera") })
```
Catatan: kotak ROI `terbuka_kanan` (s≈89, ke bawah 1.15s≈102 dari y≈306) harus di dalam 640×480 dan lebar 89/640≈0.139 ∈ [0.12, 0.45].

- [ ] **Step 5: Jalankan** `npm test` → FAIL; implementasi `validasi.js`; `npm test` → 6 passed; `npm run build` → sukses.
- [ ] **Step 6: Commit** `feat(frontend): kerangka React/Tailwind dan aturan validasi`.

---

### Task 7: Kamera berpanduan + halaman Scan

**Files:**
- Create: `frontend/src/hooks/useHandTracker.js`, `frontend/src/components/KameraTangan.jsx`, `frontend/src/lib/api.js`
- Modify: `frontend/src/pages/Scan.jsx`

**Interfaces:**
- Consumes: Task 6 `validasi.js`; API Task 5.
- Produces:
  - `useHandTracker(videoRef) -> { hasil: { lm, label } | null, fps: number, siap: boolean, galat: string | null }` — `FilesetResolver.forVisionTasks("/mediapipe/wasm")`, `HandLandmarker.createFromOptions({ baseOptions: { modelAssetPath: "/mediapipe/hand_landmarker.task", delegate: "GPU" }, runningMode: "VIDEO", numHands: 1 })`, loop `requestAnimationFrame` + `detectForVideo`; `fps` = jumlah deteksi per detik terakhir, diperbarui tiap 0,5 s.
  - `<KameraTangan mode="sekali"|"beruntun" onAmbil={async (frameDataUrl, info) => …} aktif={bool} />` — `info = { sisi }`. Overlay canvas berukuran sama dengan video, keduanya dicermin CSS. Kerangka (`HandLandmarker.HAND_CONNECTIONS`) hijau bila `periksa().semua`, merah bila tidak; poligon `kotakRoi` hanya saat semua lolos. Badge FPS kanan atas, pil pesan di bawah video, daftar 5 butir validasi (✔/✖) di samping. Tanpa tangan → video polos + pesan. Ambil frame: `semua` bertahan `AMBANG.tahanMs` → gambar video ke canvas tersembunyi (tidak dicermin) → `toDataURL("image/jpeg", 0.92)` → `onAmbil`. `mode="sekali"`: berhenti setelah satu ambilan. `mode="beruntun"`: ambil lagi tiap `AMBANG.jedaMs` selama valid, menunggu `onAmbil` selesai dulu. `aktif=false` menghentikan pengambilan. Kamera: `getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" } })`; dilepas saat unmount.
  - `api.js`: `scan(frame, batas)`, `sampel(frame)`, `simpanOrang(body)`, `daftarOrang()`, `ambilOrang(id)`, `hapusOrang(id)`, `hapusSemua()` — melempar `Error(pesan)` dengan `err.status` dan `err.data` saat respons tidak OK.
  - `Scan.jsx`: `KameraTangan mode="sekali"`; slider batas 0.10–0.50 langkah 0.01, default 0.38, tersimpan di `localStorage["batas"]` (dalam try/catch). Setelah `onAmbil` → indikator "Memproses…" → `scan()` → `navigate("/hasil", { state: { hasil } })`. Galat API → tampilkan pesan + kamera aktif lagi.

- [ ] **Step 1: Implementasi** `api.js`, `useHandTracker.js`, `KameraTangan.jsx`, `Scan.jsx`.
- [ ] **Step 2: `npm run build`** → sukses; `npm test` → tetap lolos.
- [ ] **Step 3: Jalankan** `python app.py` (MySQL Laragon menyala) dan `npm run dev`, buka `http://localhost:5173`.
- [ ] **Step 4: Cek manual:** FPS tampil (≥15 di laptop); tangan terbuka → kerangka hijau + kotak ROI mengikuti; kepal → merah, "Buka semua jari", tidak ada foto; punggung tangan → "Tunjukkan telapak…"; tahan 1 s → pindah ke `/hasil`.
- [ ] **Step 5: Cek label sisi:** tampilkan sementara `info.sisi` di layar; angkat tangan **kanan** → harus "kanan". Jika terbalik, balik pemetaan di **kedua** `sisiDariLabel` dan `sisi_dari_label` beserta tesnya, lalu ulangi.
- [ ] **Step 6: Cek manual izin kamera:** blokir izin kamera di browser → area kamera menampilkan "Kamera tidak bisa dibuka. Izinkan akses kamera di browser lalu muat ulang halaman." (bukan layar hitam).
- [ ] **Step 7: Commit** `feat(frontend): kamera berpanduan, validasi live, FPS, halaman scan`.

---

### Task 8: Halaman Hasil (timeline) + Detail orang

**Files:**
- Create: `frontend/src/components/GrafikJarak.jsx`
- Modify: `frontend/src/pages/Hasil.jsx`, `frontend/src/pages/DetailOrang.jsx`

**Interfaces:**
- Consumes: respons `/api/scan` (Task 5) lewat `location.state.hasil`; `ambilOrang(id)`.
- Produces:
  - `<GrafikJarak jarak={[{nama, sisi, jarak, orang_id}]} batas={number} />` — batang horizontal per entri, label "nama (sisi)", skala 0–0.5, garis vertikal di `batas`, batang di bawah batas hijau, lainnya abu-abu.
  - `Hasil.jsx`: tanpa `location.state` → `<Navigate to="/" />`. Timeline vertikal: tiap langkah kartu bernomor dengan judul, gambar (langkah 6: grid 6 gambar berlabel; langkah 7: gambar + legenda warna), penjelasan, angka (pasangan kunci–nilai). Langkah 8 berisi `GrafikJarak`. Kotak hasil di bawah: `dikenali` → hijau, nama + jarak + tombol "Lihat detail" → `navigate("/orang/" + orang_id, { state: { sisi, jarak } })`; `tidak_dikenal` → oranye + pesan + "Scan ulang"; `gagal` → merah + pesan + "Scan ulang".
  - `DetailOrang.jsx`: muat `ambilOrang(id)`; tampil nama, umur, status, tangan terdaftar; jika `location.state` ada: "Cocok dengan tangan <sisi>, jarak <x>"; 404 → "Orang tidak ditemukan"; tombol "Scan lagi".

- [ ] **Step 1: Implementasi** ketiga file. Gambar langkah ditampilkan dengan `image-rendering: pixelated` untuk peta 128×128 agar tidak buram.
- [ ] **Step 2: `npm run build`** → sukses.
- [ ] **Step 3: Cek manual:** scan → timeline 8 langkah tampil berurutan dengan gambar asli; foto gelap/buram → kotak merah dengan langkah 1–4 dan pesan kualitas; refresh `/hasil` → kembali ke Scan; "Lihat detail" membuka data yang benar.
- [ ] **Step 4: Commit** `feat(frontend): timeline langkah pemrosesan dan halaman detail`.

---

### Task 9: Halaman Daftar

**Files:**
- Modify: `frontend/src/pages/Daftar.jsx`

**Interfaces:**
- Consumes: `KameraTangan mode="beruntun"`, `sampel`, `simpanOrang`, `daftarOrang`.
- Produces: alur dua tahap.
  1. **Form:** pilihan "Orang baru" atau nama orang yang sudah terdaftar (dari `daftarOrang()`). Orang baru: nama (wajib, ≤100), umur (`type=number`, 1–120), status (select 4 pilihan). Tangan kiri/kanan (radio). Centang persetujuan wajib. Jika orang lama sudah punya tangan itu → `window.confirm("Tangan <sisi> milik <nama> sudah terdaftar. Ganti?")`; batal = tetap di form; setuju = `ganti: true`.
  2. **Kamera:** progres "n/8". Tiap `onAmbil` → `sampel(frame)`; valid → simpan `kode` + `sisi` ke array; tidak valid → tampilkan pesan 2 detik, tidak dihitung. Saat 8 terkumpul → `aktif=false` → `simpanOrang({ ..., kode, sisi_terdeteksi, persetujuan: true, ganti })`. Sukses → "Tersimpan: <nama> (tangan <sisi>)" + tautan "Coba scan". Galat (400/409) → tampilkan pesan + tombol "Ulangi pengambilan" (mengosongkan sampel). Tombol "Batal" kapan saja → kembali ke form, tidak ada yang tersimpan.

- [ ] **Step 1: Implementasi** `Daftar.jsx`.
- [ ] **Step 2: `npm run build`** → sukses.
- [ ] **Step 3: Cek manual:** daftar orang baru tangan kanan → 8/8 → tersimpan, terlihat di HeidiSQL tabel `telapak` (kolom `kode` 131072 byte); pilih "kanan" tapi tunjukkan tangan kiri → ditolak dengan pesan sisi; tambah tangan kiri ke orang yang sama → berhasil; daftar ulang tangan yang sama → muncul konfirmasi ganti.
- [ ] **Step 4: Commit** `feat(frontend): halaman pendaftaran 8 sampel`.

---

### Task 10: Halaman Data terdaftar

**Files:**
- Modify: `frontend/src/pages/DataTerdaftar.jsx`

**Interfaces:**
- Consumes: `daftarOrang`, `hapusOrang`, `hapusSemua`.
- Produces: tabel nama, umur, status, tangan terdaftar ("kiri, kanan"), tanggal daftar (format `id-ID`). Tombol "Hapus" per baris (`window.confirm("Hapus data <nama>?")`) dan "Hapus semua" (`window.confirm("Hapus SEMUA data terdaftar?")`); tabel dimuat ulang setelah hapus. Kosong → "Belum ada yang terdaftar" + tautan ke Daftar.

- [ ] **Step 1: Implementasi.**
- [ ] **Step 2: `npm run build`** → sukses.
- [ ] **Step 3: Cek manual:** hapus satu orang → hilang dari tabel dan dari MySQL (termasuk baris `telapak`); hapus semua → tabel kosong.
- [ ] **Step 4: Commit** `feat(frontend): halaman kelola data terdaftar`.

---

### Task 11: Bersih-bersih, README, uji akhir

**Files:**
- Delete: `palm.py`, `daftar.py`, `scan.py`, `hapus.py`, `requirements.txt` (root), `__pycache__/`
- Modify: `README.md`

- [ ] **Step 1: Hapus file lama** (`git rm palm.py daftar.py scan.py hapus.py requirements.txt`). Folder `data_terdaftar/` dibiarkan (diabaikan git); sebutkan di README bahwa isinya tidak dipakai lagi dan boleh dihapus.
- [ ] **Step 2: Perbarui README** (Bahasa Indonesia), pertahankan bagian yang masih berlaku (latar belakang, metode, rujukan, privasi, narasi presentasi, tabel pengujian) dan ganti bagian teknis:
  - Isi folder (backend/frontend), kebutuhan (Python 3.10, Node, Laragon MySQL).
  - Instalasi: `cd backend && pip install -r requirements.txt && copy .env.example .env`; `cd frontend && npm install` (butuh internet sekali; mengunduh model MediaPipe).
  - Menjalankan: nyalakan MySQL di Laragon → `cd backend && python app.py` → `cd frontend && npm run dev` → buka `http://localhost:5173`.
  - Alur web (5 halaman) dan tabel tahap computer vision diperbarui: tambah validasi tangan (browser + server) dan cek kualitas ROI; jelaskan bahwa gambar timeline adalah data yang sama dengan yang dicocokkan.
  - Cara menyetel batas memakai slider; tabel hasil pengujian tetap kosong untuk diisi.
  - Menjalankan tes: `cd backend && python -m pytest -q`, `cd frontend && npm test`.
- [ ] **Step 3: Uji akhir lengkap:** `python -m pytest -q` (semua lolos), `npm test` (lolos), `npm run build` (sukses). Lalu skenario demo dari awal dengan database kosong: scan (tidak dikenal, "Belum ada yang terdaftar") → daftar 2 tangan → scan tangan terdaftar (dikenali, detail benar) → scan tangan belum terdaftar (tidak dikenal) → kepal (ditolak) → hapus semua.
- [ ] **Step 4: Commit** `docs: README versi web dan hapus skrip terminal lama`.
