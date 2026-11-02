import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import PalmCamera from "../components/PalmCamera.jsx";
import { daftarOrang, sampel, simpanOrang } from "../lib/api.js";

const JUMLAH = 8;
const STATUS = [
  ["mahasiswa", "Mahasiswa"],
  ["dosen", "Dosen"],
  ["staf", "Staf"],
  ["tamu", "Tamu"],
];
const inputClass = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";

export default function Register() {
  const [daftar, setDaftar] = useState([]);
  const [pilihan, setPilihan] = useState("baru"); // "baru" or the id of an existing person
  const [form, setForm] = useState({ nama: "", umur: "", status: "mahasiswa", sisi: "kanan", persetujuan: false });
  const [tahap, setTahap] = useState("form"); // "form" | "ambil" | "selesai"
  const [ganti, setGanti] = useState(false);
  const [jumlah, setJumlah] = useState(0);
  const [pesan, setPesan] = useState(null);
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
  const bentrok = orangLama?.tangan.includes(form.sisi) ?? false;

  function ubah(kunci, nilai) {
    setForm((f) => ({ ...f, [kunci]: nilai }));
  }

  function reset() {
    sampelRef.current = [];
    sisiRef.current = [];
    setJumlah(0);
    setPesan(null);
    setGagalSimpan(false);
  }

  function mulai(e) {
    e.preventDefault();
    setGalat(null);
    if (!form.persetujuan) {
      setGalat("Centang persetujuan terlebih dahulu.");
      return;
    }
    if (pilihan === "baru") {
      const umur = Number(form.umur);
      if (!form.nama.trim()) return setGalat("Nama wajib diisi.");
      if (!Number.isInteger(umur) || umur < 1 || umur > 120) return setGalat("Umur harus angka 1–120.");
    }
    if (bentrok && !window.confirm(`Tangan ${form.sisi} milik ${orangLama.nama} sudah terdaftar. Ganti?`)) {
      return;
    }
    reset();
    setGanti(bentrok);
    setTahap("ambil");
  }

  function tampilkanPesan(teks) {
    setPesan(teks);
    setTimeout(() => setPesan(null), 2000);
  }

  async function onAmbil(frame) {
    if (sampelRef.current.length >= JUMLAH) return;
    try {
      const s = await sampel(frame);
      if (!s.valid) {
        tampilkanPesan(s.pesan);
        return;
      }
      sampelRef.current.push(s.kode);
      sisiRef.current.push(s.sisi);
      setJumlah(sampelRef.current.length);
      if (sampelRef.current.length === JUMLAH) {
        await selesaikan();
      }
    } catch (err) {
      tampilkanPesan(err.message);
    }
  }

  async function selesaikan() {
    setMenyimpan(true);
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
        ganti,
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

  if (tahap === "selesai" && tersimpan) {
    return (
      <div className="space-y-3 rounded-xl border border-green-300 bg-green-50 p-6">
        <p className="text-lg font-semibold text-green-800">
          Tersimpan: {tersimpan.nama} (tangan {form.sisi})
        </p>
        <Link to="/" className="inline-block underline">Coba scan</Link>
      </div>
    );
  }

  if (tahap === "ambil") {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-semibold">
            Tahan telapak… {jumlah}/{JUMLAH}
          </h1>
          <button
            type="button"
            onClick={() => { reset(); setTahap("form"); }}
            disabled={menyimpan}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-200 disabled:opacity-50"
          >
            Batal
          </button>
        </div>
        <PalmCamera
          mode="beruntun"
          onAmbil={onAmbil}
          aktif={!menyimpan && !gagalSimpan && jumlah < JUMLAH}
        />
        {menyimpan && <p className="text-sm text-slate-600">Menyimpan…</p>}
        {pesan && <p className="text-sm text-orange-700">{pesan}</p>}
        {galat && (
          <div className="flex flex-wrap items-center gap-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <span>{galat}</span>
            {gagalSimpan && (
              <button
                type="button"
                onClick={() => { reset(); setGalat(null); }}
                className="rounded-lg bg-slate-900 px-3 py-1.5 text-white hover:bg-slate-700"
              >
                Ulangi pengambilan
              </button>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={mulai} className="max-w-lg space-y-4 rounded-xl border border-slate-200 bg-white p-6">
      <h1 className="text-xl font-semibold">Daftar telapak</h1>

      <label className="block space-y-1 text-sm">
        <span className="font-medium">Orang</span>
        <select value={pilihan} onChange={(e) => setPilihan(e.target.value)} className={inputClass}>
          <option value="baru">Orang baru</option>
          {daftar.map((o) => (
            <option key={o.id} value={o.id}>
              {o.nama} (sudah terdaftar: {o.tangan.join(", ")})
            </option>
          ))}
        </select>
      </label>

      {pilihan === "baru" && (
        <>
          <label className="block space-y-1 text-sm">
            <span className="font-medium">Nama</span>
            <input
              value={form.nama}
              onChange={(e) => ubah("nama", e.target.value)}
              maxLength={100}
              className={inputClass}
            />
          </label>
          <div className="grid grid-cols-2 gap-4">
            <label className="block space-y-1 text-sm">
              <span className="font-medium">Umur</span>
              <input
                type="number"
                min="1"
                max="120"
                value={form.umur}
                onChange={(e) => ubah("umur", e.target.value)}
                className={inputClass}
              />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="font-medium">Status</span>
              <select value={form.status} onChange={(e) => ubah("status", e.target.value)} className={inputClass}>
                {STATUS.map(([nilai, teks]) => (
                  <option key={nilai} value={nilai}>{teks}</option>
                ))}
              </select>
            </label>
          </div>
        </>
      )}

      <fieldset className="space-y-2 text-sm">
        <legend className="font-medium">Tangan</legend>
        <div className="flex gap-6">
          {["kiri", "kanan"].map((s) => (
            <label key={s} className="flex items-center gap-2">
              <input
                type="radio"
                name="sisi"
                value={s}
                checked={form.sisi === s}
                onChange={() => ubah("sisi", s)}
              />
              {s === "kiri" ? "Kiri" : "Kanan"}
            </label>
          ))}
        </div>
        {bentrok && (
          <p className="text-orange-700">Tangan {form.sisi} sudah terdaftar. Kamu bisa menggantinya.</p>
        )}
      </fieldset>

      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.persetujuan}
          onChange={(e) => ubah("persetujuan", e.target.checked)}
          className="mt-1"
        />
        <span>Saya setuju data kode telapak saya disimpan untuk keperluan demo. Foto tidak disimpan.</span>
      </label>

      {galat && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{galat}</p>}

      <button
        type="submit"
        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
      >
        Mulai pengambilan 8 sampel
      </button>
    </form>
  );
}
