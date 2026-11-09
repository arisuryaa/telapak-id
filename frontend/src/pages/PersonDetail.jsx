import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router";
import { IkonCentang, Kartu, Pesan, tombol } from "../components/ui.jsx";
import { ambilOrang } from "../lib/api.js";
import { formatTangan } from "../lib/format.js";

const inisial = (nama) =>
  nama
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((k) => k[0].toUpperCase())
    .join("");

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
      .catch((err) => !batal && setGalat(err.status === 404 ? "Orang ini tidak ditemukan. Mungkin datanya sudah dihapus." : err.message));
    return () => {
      batal = true;
    };
  }, [id]);

  if (galat) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <Pesan jenis="galat">{galat}</Pesan>
        <Link to="/" className={tombol.kedua}>Kembali ke scan</Link>
      </div>
    );
  }
  if (!orang) return <p className="text-muted">Memuat…</p>;

  const rincian = [
    ["Umur", `${orang.umur} tahun`],
    ["Status", orang.status],
    ["Tangan terdaftar", formatTangan(orang)],
  ];

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Kartu className="overflow-hidden">
        <div className="flex flex-wrap items-center gap-5 p-6 sm:p-8">
          <span className="flex h-20 w-20 shrink-0 items-center justify-center rounded-3xl bg-brand text-2xl font-extrabold text-white shadow-float">
            {inisial(orang.nama)}
          </span>
          <div className="min-w-0">
            <h1 className="text-3xl font-extrabold tracking-tight text-ink">{orang.nama}</h1>
            <p className="mt-1 text-muted capitalize">{orang.status}</p>
          </div>
        </div>
        <dl className="grid border-t border-line sm:grid-cols-3">
          {rincian.map(([k, v]) => (
            <div key={k} className="border-line px-6 py-4 sm:border-r sm:last:border-r-0 sm:px-8">
              <dt className="text-xs font-semibold text-muted">{k}</dt>
              <dd className="mt-1 font-semibold text-ink capitalize">{v}</dd>
            </div>
          ))}
        </dl>
        {state?.sisi && (
          <div className="flex items-center gap-3 border-t border-line bg-ok-soft px-6 py-4 text-sm font-medium text-ok sm:px-8">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ok text-white">
              <IkonCentang className="h-3.5 w-3.5" />
            </span>
            Cocok dengan tangan {state.sisi} pada scan terakhir, jarak {state.jarak.toFixed(3)}.
          </div>
        )}
      </Kartu>
      <Link to="/" className={tombol.utama}>Scan lagi</Link>
    </div>
  );
}
