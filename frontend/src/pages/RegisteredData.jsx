import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
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

  if (!daftar) {
    return galat ? <p className="text-red-700">{galat}</p> : <p className="text-slate-500">Memuat…</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Data terdaftar</h1>
        {daftar.length > 0 && (
          <button
            type="button"
            onClick={hapusKeseluruhan}
            className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
          >
            Hapus semua
          </button>
        )}
      </div>

      {galat && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{galat}</p>}

      {daftar.length === 0 ? (
        <p className="text-slate-600">
          Belum ada yang terdaftar. <Link to="/daftar" className="underline">Daftar sekarang</Link>.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-2 font-medium">Nama</th>
                <th className="px-4 py-2 font-medium">Umur</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Tangan</th>
                <th className="px-4 py-2 font-medium">Tanggal daftar</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {daftar.map((o) => (
                <tr key={o.id} className="border-t border-slate-100">
                  <td className="px-4 py-2">
                    <Link to={`/orang/${o.id}`} className="underline">{o.nama}</Link>
                  </td>
                  <td className="px-4 py-2">{o.umur}</td>
                  <td className="px-4 py-2 capitalize">{o.status}</td>
                  <td className="px-4 py-2">{formatTangan(o)}</td>
                  <td className="px-4 py-2">
                    {new Date(o.dibuat_pada).toLocaleDateString("id-ID", {
                      day: "numeric", month: "long", year: "numeric",
                    })}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => hapus(o)}
                      className="rounded-md px-2 py-1 text-red-700 hover:bg-red-50"
                    >
                      Hapus
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
