import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router";
import { ambilOrang } from "../lib/api.js";

export default function PersonDetail() {
  const { id } = useParams();
  const { state } = useLocation();
  const [orang, setOrang] = useState(null);
  const [galat, setGalat] = useState(null);

  useEffect(() => {
    let batal = false;
    setOrang(null);
    setGalat(null);
    ambilOrang(id)
      .then((data) => !batal && setOrang(data))
      .catch((err) => !batal && setGalat(err.status === 404 ? "Orang tidak ditemukan" : err.message));
    return () => {
      batal = true;
    };
  }, [id]);

  if (galat) {
    return (
      <div className="space-y-3">
        <p className="text-red-700">{galat}</p>
        <Link to="/" className="underline">Kembali ke scan</Link>
      </div>
    );
  }
  if (!orang) return <p className="text-slate-500">Memuat…</p>;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h1 className="text-2xl font-semibold">{orang.nama}</h1>
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:max-w-md">
          <dt className="text-slate-500">Umur</dt>
          <dd>{orang.umur} tahun</dd>
          <dt className="text-slate-500">Status</dt>
          <dd className="capitalize">{orang.status}</dd>
          <dt className="text-slate-500">Tangan terdaftar</dt>
          <dd>{orang.tangan.join(", ")}</dd>
        </dl>
        {state?.sisi && (
          <p className="mt-5 rounded-lg bg-green-50 p-3 text-sm text-green-800">
            Cocok dengan tangan {state.sisi}, jarak {state.jarak.toFixed(3)}.
          </p>
        )}
      </div>
      <Link
        to="/"
        className="inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
      >
        Scan lagi
      </Link>
    </div>
  );
}
