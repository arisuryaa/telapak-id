import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { IkonTangan, JudulHalaman, Kartu, Pesan, tombol } from "../components/ui.jsx";
import { daftarOrang, hapusOrang, hapusSemua } from "../lib/api.js";
import { formatTangan } from "../lib/format.js";

export default function RegisteredData() {
  const [daftar, setDaftar] = useState(null);
  const [galat, setGalat] = useState(null);

  const muat = useCallback(() => {
    return daftarOrang()
      .then((data) => {
        setDaftar(data);
        setGalat(null);
      })
      .catch((err) => setGalat(err.message));
  }, []);

  useEffect(() => {
    muat();
  }, [muat]);

  async function hapus(orang) {
    if (!window.confirm(`Hapus data ${orang.nama}?`)) return;
    try {
      await hapusOrang(orang.id);
      await muat();
    } catch (err) {
      setGalat(err.message);
    }
  }

  async function hapusKeseluruhan() {
    if (!window.confirm("Hapus SEMUA data terdaftar?")) return;
    try {
      await hapusSemua();
      await muat();
    } catch (err) {
      setGalat(err.message);
    }
  }

  return (
    <div className="space-y-8">
      <JudulHalaman
        judul="Data terdaftar"
        keterangan={daftar ? `${daftar.length} orang terdaftar. Klik nama untuk melihat detailnya.` : undefined}
      >
        <div className="flex flex-wrap gap-3">
          {daftar?.length > 0 && (
            <button type="button" onClick={hapusKeseluruhan} className={tombol.kedua}>
              <span className="text-err">Hapus semua</span>
            </button>
          )}
          <Link to="/daftar" className={tombol.utama}>Daftarkan orang baru</Link>
        </div>
      </JudulHalaman>

      {galat && <Pesan jenis="galat">{galat}</Pesan>}

      {!daftar ? (
        !galat && <p className="text-muted">Memuat…</p>
      ) : daftar.length === 0 ? (
        <Kartu className="flex flex-col items-center px-6 py-14 text-center">
          <span className="flex h-16 w-16 items-center justify-center rounded-3xl bg-brand-soft text-brand">
            <IkonTangan className="h-8 w-8" />
          </span>
          <h2 className="mt-5 text-xl font-bold tracking-tight text-ink">Belum ada telapak terdaftar</h2>
          <p className="mt-1 max-w-sm text-sm text-muted">
            Daftarkan satu orang dulu supaya sistem punya data untuk dicocokkan saat scan.
          </p>
          <Link to="/daftar" className={`${tombol.utama} mt-6`}>Daftarkan telapak</Link>
        </Kartu>
      ) : (
        <Kartu className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted">
              <tr>
                <th className="px-6 pt-5 pb-3 font-semibold">Nama</th>
                <th className="px-4 pt-5 pb-3 font-semibold">Umur</th>
                <th className="px-4 pt-5 pb-3 font-semibold">Status</th>
                <th className="px-4 pt-5 pb-3 font-semibold">Tangan</th>
                <th className="px-4 pt-5 pb-3 font-semibold">Tanggal daftar</th>
                <th className="px-6 pt-5 pb-3"><span className="sr-only">Aksi</span></th>
              </tr>
            </thead>
            <tbody>
              {daftar.map((o) => (
                <tr key={o.id} className="border-t border-line transition-colors hover:bg-canvas/60">
                  <td className="px-6 py-3.5">
                    <Link to={`/orang/${o.id}`} className="font-semibold text-ink hover:text-brand">{o.nama}</Link>
                  </td>
                  <td className="px-4 py-3.5 tabular-nums">{o.umur}</td>
                  <td className="px-4 py-3.5">
                    <span className="rounded-full bg-brand-soft px-2.5 py-1 text-xs font-semibold text-brand capitalize">
                      {o.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-muted">{formatTangan(o)}</td>
                  <td className="px-4 py-3.5 text-muted">
                    {new Date(o.dibuat_pada).toLocaleDateString("id-ID", {
                      day: "numeric", month: "long", year: "numeric",
                    })}
                  </td>
                  <td className="px-6 py-3.5 text-right">
                    <button
                      type="button"
                      onClick={() => hapus(o)}
                      className="rounded-full px-3 py-1.5 text-sm font-semibold text-err hover:bg-err-soft"
                    >
                      Hapus
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Kartu>
      )}
    </div>
  );
}
