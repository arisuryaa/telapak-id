import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import PalmCamera from "../components/PalmCamera.jsx";
import ProcessingPanel from "../components/ProcessingPanel.jsx";
import { IkonCentang, IkonTangan, JudulHalaman, Kartu, Pesan, input, tombol } from "../components/ui.jsx";
import { daftarOrang, sampel, simpanOrang } from "../lib/api.js";
import { formatTangan } from "../lib/format.js";

const JUMLAH = 8;
const STATUS = [
  ["mahasiswa", "Mahasiswa"],
  ["dosen", "Dosen"],
  ["staf", "Staf"],
  ["tamu", "Tamu"],
];
const LANGKAH = ["Isi data diri", "Ambil 8 sampel", "Selesai"];

function Stepper({ aktif }) {
  return (
    <ol className="flex flex-wrap items-center gap-2 text-sm">
      {LANGKAH.map((teks, i) => {
        const selesai = i < aktif;
        const sekarang = i === aktif;
        return (
          <li key={teks} className="flex items-center gap-2">
            <span
              className={`flex items-center gap-2 rounded-full py-1.5 pr-4 pl-1.5 font-semibold ${
                sekarang ? "bg-white text-ink shadow-card" : selesai ? "text-brand" : "text-muted"
              }`}
              aria-current={sekarang ? "step" : undefined}
            >
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                  selesai ? "bg-brand text-white" : sekarang ? "bg-brand text-white" : "bg-lilac text-muted"
                }`}
              >
                {selesai ? <IkonCentang className="h-3.5 w-3.5" /> : i + 1}
              </span>
              {teks}
            </span>
            {i < LANGKAH.length - 1 && <span className={`h-px w-6 ${selesai ? "bg-brand" : "bg-line"}`} />}
          </li>
        );
      })}
    </ol>
  );
}

// Eight arcs around the count. Each accepted sample fills the next arc.
function DialSampel({ jumlah, total = JUMLAH }) {
  const r = 58;
  const pusat = 70;
  const celah = 7; // degrees between arcs
  const busur = (i) => {
    const mulai = ((i * 360) / total - 90 + celah / 2) * (Math.PI / 180);
    const akhir = (((i + 1) * 360) / total - 90 - celah / 2) * (Math.PI / 180);
    const x1 = pusat + r * Math.cos(mulai);
    const y1 = pusat + r * Math.sin(mulai);
    const x2 = pusat + r * Math.cos(akhir);
    const y2 = pusat + r * Math.sin(akhir);
    return `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`;
  };
  const penuh = jumlah >= total;

  return (
    <div className="relative mx-auto h-[140px] w-[140px]" role="img" aria-label={`${jumlah} dari ${total} sampel diambil`}>
      <svg viewBox="0 0 140 140" className="h-full w-full">
        {Array.from({ length: total }, (_, i) => {
          const terisi = i < jumlah;
          const berikut = i === jumlah;
          return (
            <path
              key={`${i}-${terisi}`}
              d={busur(i)}
              fill="none"
              strokeLinecap="round"
              strokeWidth="12"
              className={terisi ? "animasi-isi" : undefined}
              stroke={terisi ? "#2f6bef" : berikut ? "#b9cbfa" : "#e6e8fb"}
            />
          );
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {penuh ? (
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand text-white">
            <IkonCentang className="h-6 w-6" />
          </span>
        ) : (
          <>
            <span className="text-4xl leading-none font-extrabold tracking-tight text-ink tabular-nums">
              {jumlah}
              <span className="text-lg font-bold text-muted">/{total}</span>
            </span>
            <span className="mt-1 text-xs font-semibold text-muted">sampel</span>
          </>
        )}
      </div>
    </div>
  );
}

function PilihanTangan({ nilai, onUbah, terdaftar }) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold text-ink">Tangan yang didaftarkan</legend>
      <div className="grid grid-cols-2 gap-3">
        {["kiri", "kanan"].map((s) => {
          const dipilih = nilai === s;
          return (
            <label
              key={s}
              className={`relative flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 px-3 py-4 text-sm font-semibold transition-colors has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-brand/45 ${
                dipilih ? "border-brand bg-brand-soft text-brand" : "border-line bg-white text-muted hover:border-brand/40"
              }`}
            >
              <input
                type="radio"
                name="sisi"
                value={s}
                checked={dipilih}
                onChange={() => onUbah(s)}
                className="sr-only"
              />
              <IkonTangan cermin={s === "kiri"} className="h-9 w-9" />
              Tangan {s}
              {terdaftar.includes(s) && (
                <span className="absolute top-2 right-2 rounded-full bg-warn-soft px-2 py-0.5 text-[11px] font-semibold text-warn">
                  terdaftar
                </span>
              )}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

const CARA_KERJA = [
  ["Kamera menyala", "Izinkan akses kamera saat browser bertanya."],
  ["Tunjukkan telapak", "Buka kelima jari, telapak menghadap kamera, kira-kira 30–50 cm dari layar."],
  ["Tahan diam sekitar 10 detik", "8 foto diambil otomatis satu per satu. Tidak perlu menekan tombol apa pun."],
];

function CaraKerja({ sisi }) {
  return (
    <Kartu className="p-6">
      <h2 className="text-lg font-bold tracking-tight text-ink">Yang akan terjadi</h2>
      <p className="mt-1 text-sm text-muted">
        Sistem butuh 8 foto tangan {sisi} supaya bisa mengenalimu lagi walau posisi tangan sedikit berbeda.
      </p>
      <ol className="mt-5 space-y-4">
        {CARA_KERJA.map(([judul, isi], i) => (
          <li key={judul} className="flex gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft text-sm font-bold text-brand">
              {i + 1}
            </span>
            <div>
              <p className="text-sm font-semibold text-ink">{judul}</p>
              <p className="text-sm text-muted">{isi}</p>
            </div>
          </li>
        ))}
      </ol>
      <div className="mt-6 flex items-center gap-1.5" aria-hidden="true">
        {Array.from({ length: JUMLAH }, (_, i) => (
          <span key={i} className="h-2 flex-1 rounded-full bg-lilac" />
        ))}
      </div>
      <p className="mt-2 text-xs text-muted">Foto tidak disimpan. Yang disimpan hanya kode pola garis telapak.</p>
    </Kartu>
  );
}

export default function Register() {
  const [daftar, setDaftar] = useState([]);
  const [pilihan, setPilihan] = useState("baru"); // "baru" or the id of an existing person
  const [form, setForm] = useState({ nama: "", umur: "", status: "mahasiswa", sisi: "kanan", persetujuan: false, ganti: false });
  const [tahap, setTahap] = useState("form"); // "form" | "ambil" | "selesai"
  const [jumlah, setJumlah] = useState(0);
  const [ditolak, setDitolak] = useState(null);
  const [galat, setGalat] = useState(null);
  const [menyimpan, setMenyimpan] = useState(false);
  const [gagalSimpan, setGagalSimpan] = useState(false);
  const [tersimpan, setTersimpan] = useState(null);
  const sampelRef = useRef([]);
  const sisiRef = useRef([]);

  useEffect(() => {
    daftarOrang().then(setDaftar).catch((err) => setGalat(err.message));
  }, []);

  const orangLama = daftar.find((o) => String(o.id) === pilihan) ?? null;
  const tanganTerdaftar = orangLama?.tangan ?? [];
  const bentrok = tanganTerdaftar.includes(form.sisi);
  const nama = orangLama?.nama ?? form.nama.trim();

  function ubah(kunci, nilai) {
    setForm((f) => ({ ...f, [kunci]: nilai }));
  }

  function reset() {
    sampelRef.current = [];
    sisiRef.current = [];
    setJumlah(0);
    setDitolak(null);
    setGagalSimpan(false);
  }

  function mulai(e) {
    e.preventDefault();
    setGalat(null);
    if (pilihan === "baru") {
      const umur = Number(form.umur);
      if (!form.nama.trim()) return setGalat("Isi nama dulu.");
      if (!Number.isInteger(umur) || umur < 1 || umur > 120) return setGalat("Umur harus angka 1–120.");
    }
    if (bentrok && !form.ganti) {
      return setGalat(`Centang "Ganti data lama" untuk mendaftarkan ulang tangan ${form.sisi} milik ${orangLama.nama}.`);
    }
    if (!form.persetujuan) return setGalat("Centang persetujuan penyimpanan data dulu.");
    reset();
    setTahap("ambil");
  }

  function batal() {
    reset();
    setGalat(null);
    setTahap("form");
  }

  async function onAmbil(frame) {
    if (sampelRef.current.length >= JUMLAH) return;
    try {
      const s = await sampel(frame);
      if (!s.valid) {
        setDitolak(s.pesan);
        return;
      }
      // Reject the wrong hand now, instead of failing after all 8 samples.
      if (s.sisi !== form.sisi) {
        setDitolak(`Itu tangan ${s.sisi}. Tunjukkan tangan ${form.sisi}.`);
        return;
      }
      setDitolak(null);
      sampelRef.current.push(s.kode);
      sisiRef.current.push(s.sisi);
      setJumlah(sampelRef.current.length);
      if (sampelRef.current.length === JUMLAH) {
        await selesaikan();
      }
    } catch (err) {
      setDitolak(err.message);
    }
  }

  async function selesaikan() {
    setMenyimpan(true);
    setGalat(null);
    try {
      const r = await simpanOrang({
        orang_id: pilihan === "baru" ? undefined : Number(pilihan),
        nama: form.nama.trim(),
        umur: Number(form.umur),
        status: form.status,
        sisi: form.sisi,
        persetujuan: true,
        kode: sampelRef.current,
        sisi_terdeteksi: sisiRef.current,
        ganti: bentrok && form.ganti,
      });
      setTersimpan(r.orang);
      setTahap("selesai");
    } catch (err) {
      setGalat(err.message);
      setGagalSimpan(true);
    } finally {
      setMenyimpan(false);
    }
  }

  function daftarTanganLain() {
    const lain = form.sisi === "kanan" ? "kiri" : "kanan";
    setDaftar((d) => (tersimpan ? [...d.filter((o) => o.id !== tersimpan.id), tersimpan] : d));
    setPilihan(String(tersimpan.id));
    setForm((f) => ({ ...f, sisi: lain, ganti: false, persetujuan: false }));
    setTersimpan(null);
    reset();
    setTahap("form");
  }

  const indeksLangkah = tahap === "form" ? 0 : tahap === "ambil" ? 1 : 2;

  return (
    <div className="space-y-8">
      <div className="space-y-5">
        <Stepper aktif={indeksLangkah} />
        {tahap === "form" && (
          <JudulHalaman
            judul="Daftarkan telapak tangan"
            keterangan="Isi data diri, lalu tunjukkan telapak ke kamera. Prosesnya kurang dari satu menit."
          />
        )}
        {tahap === "ambil" && (
          <JudulHalaman
            judul={`Tunjukkan telapak tangan ${form.sisi}`}
            keterangan={`Untuk ${nama}. Tahan tangan diam di depan kamera sampai lingkaran terisi penuh.`}
          >
            <button type="button" onClick={batal} disabled={menyimpan} className={tombol.kedua}>
              Batal
            </button>
          </JudulHalaman>
        )}
      </div>

      {tahap === "selesai" && tersimpan && (
        <Kartu className="mx-auto max-w-xl p-8 text-center">
          <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-ok-soft text-ok">
            <IkonCentang className="h-8 w-8" />
          </span>
          <h1 className="mt-5 text-3xl font-extrabold tracking-tight text-ink">Telapak terdaftar</h1>
          <p className="mt-2 text-muted">
            Tangan {form.sisi} milik <span className="font-semibold text-ink">{tersimpan.nama}</span> sudah tersimpan
            dengan {JUMLAH} sampel. Sekarang coba scan untuk memastikan sistem mengenalimu.
          </p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Link to="/" className={tombol.utama}>Coba scan sekarang</Link>
            {!tersimpan.tangan?.includes(form.sisi === "kanan" ? "kiri" : "kanan") && (
              <button type="button" onClick={daftarTanganLain} className={tombol.kedua}>
                Daftarkan tangan {form.sisi === "kanan" ? "kiri" : "kanan"}
              </button>
            )}
          </div>
        </Kartu>
      )}

      {tahap === "ambil" && (
        <div className="space-y-4">
          {/* The hand must stay in view for all 8 samples; once saving starts it is no longer needed. */}
          <div className={menyimpan ? "hidden" : ""}>
            <PalmCamera
              mode="beruntun"
              onAmbil={onAmbil}
              aktif={!menyimpan && !gagalSimpan && jumlah < JUMLAH}
              kilat={jumlah}
              pesanTahan={`Tahan… mengambil sampel ${Math.min(jumlah + 1, JUMLAH)} dari ${JUMLAH}`}
              samping={
                <div className="space-y-4 text-center">
                  <DialSampel jumlah={jumlah} />
                  <div>
                    <p className="text-sm font-bold text-ink">
                      {jumlah === 0
                        ? "Belum ada sampel"
                        : jumlah < JUMLAH
                          ? `Bagus, ${JUMLAH - jumlah} lagi`
                          : "Semua sampel terkumpul"}
                    </p>
                    <p className="mt-1 text-xs leading-relaxed text-muted">
                      Tidak perlu menekan tombol. Selama tangan diam dan syarat di bawah terpenuhi, sampel diambil sendiri.
                    </p>
                  </div>
                  {ditolak && (
                    <Pesan jenis="peringatan" className="text-left text-xs">
                      Sampel tadi tidak dipakai: {ditolak}
                    </Pesan>
                  )}
                </div>
              }
            />
          </div>
          {menyimpan && (
            <ProcessingPanel judul="Menyimpan data…" keterangan={`${JUMLAH} sampel sudah diambil. Tangan boleh diturunkan.`} />
          )}
          {galat && (
            <Pesan jenis="galat" className="flex flex-wrap items-center justify-between gap-3">
              <span>Gagal menyimpan: {galat}</span>
              {gagalSimpan && (
                <button type="button" onClick={() => { reset(); setGalat(null); }} className={tombol.utama}>
                  Ulangi pengambilan
                </button>
              )}
            </Pesan>
          )}
        </div>
      )}

      {tahap === "form" && (
        <div className="grid items-start gap-6 lg:grid-cols-[1fr_24rem]">
          <Kartu className="p-6 sm:p-8">
            <form onSubmit={mulai} className="space-y-6" noValidate>
              <label className="block space-y-2 text-sm">
                <span className="font-semibold text-ink">Siapa yang didaftarkan?</span>
                <select
                  value={pilihan}
                  onChange={(e) => { setPilihan(e.target.value); ubah("ganti", false); }}
                  className={input}
                >
                  <option value="baru">Orang baru</option>
                  {daftar.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.nama} (sudah terdaftar: {formatTangan(o)})
                    </option>
                  ))}
                </select>
              </label>

              {pilihan === "baru" && (
                <div className="space-y-4">
                  <label className="block space-y-2 text-sm">
                    <span className="font-semibold text-ink">Nama lengkap</span>
                    <input
                      value={form.nama}
                      onChange={(e) => ubah("nama", e.target.value)}
                      maxLength={100}
                      placeholder="Contoh: Ayu Lestari"
                      autoComplete="name"
                      className={input}
                    />
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <label className="block space-y-2 text-sm">
                      <span className="font-semibold text-ink">Umur</span>
                      <input
                        type="number"
                        min="1"
                        max="120"
                        inputMode="numeric"
                        value={form.umur}
                        onChange={(e) => ubah("umur", e.target.value)}
                        placeholder="21"
                        className={input}
                      />
                    </label>
                    <label className="block space-y-2 text-sm">
                      <span className="font-semibold text-ink">Status</span>
                      <select value={form.status} onChange={(e) => ubah("status", e.target.value)} className={input}>
                        {STATUS.map(([nilai, teks]) => (
                          <option key={nilai} value={nilai}>{teks}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                </div>
              )}

              <div className="space-y-3">
                <PilihanTangan
                  nilai={form.sisi}
                  onUbah={(s) => { ubah("sisi", s); ubah("ganti", false); }}
                  terdaftar={tanganTerdaftar}
                />
                {bentrok && (
                  <label className="flex items-start gap-3 rounded-2xl bg-warn-soft p-4 text-sm">
                    <input
                      type="checkbox"
                      checked={form.ganti}
                      onChange={(e) => ubah("ganti", e.target.checked)}
                      className="mt-0.5 h-4 w-4 accent-brand"
                    />
                    <span className="text-ink">
                      <span className="font-semibold">Ganti data lama.</span> Tangan {form.sisi} milik {orangLama.nama}{" "}
                      sudah terdaftar. Data lamanya akan diganti dengan sampel baru.
                    </span>
                  </label>
                )}
              </div>

              <label className="flex items-start gap-3 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={form.persetujuan}
                  onChange={(e) => ubah("persetujuan", e.target.checked)}
                  className="mt-0.5 h-4 w-4 accent-brand"
                />
                <span>Saya setuju kode pola telapak saya disimpan untuk keperluan demo. Foto tidak disimpan.</span>
              </label>

              {galat && <Pesan jenis="galat">{galat}</Pesan>}

              <button type="submit" className={`${tombol.utama} w-full py-3.5 text-base sm:w-auto`}>
                Nyalakan kamera dan mulai
              </button>
            </form>
          </Kartu>
          <CaraKerja sisi={form.sisi} />
        </div>
      )}
    </div>
  );
}
