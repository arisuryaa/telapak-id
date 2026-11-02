import { Navigate, useLocation, useNavigate } from "react-router";
import DistanceChart from "../components/DistanceChart.jsx";

const PIXELATED = new Set([4, 5, 6, 7]); // small maps: keep them sharp, not blurred

function Langkah({ langkah }) {
  const kecil = PIXELATED.has(langkah.no);
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center gap-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white">
          {langkah.no}
        </span>
        <h2 className="font-semibold">{langkah.judul}</h2>
      </div>
      <p className="mb-3 text-sm text-slate-600">{langkah.penjelasan}</p>

      {langkah.no === 8 ? (
        <DistanceChart jarak={langkah.jarak} batas={langkah.angka.batas} />
      ) : langkah.gambar.length > 1 ? (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
          {langkah.gambar.map((g) => (
            <figure key={g.label} className="text-center text-xs text-slate-600">
              <img src={g.src} alt={g.label} className="w-full rounded bg-slate-200 pixelated" />
              <figcaption className="mt-1">{g.label}</figcaption>
            </figure>
          ))}
        </div>
      ) : (
        langkah.gambar.map((g) => (
          <img
            key={g.label}
            src={g.src}
            alt={g.label}
            className={`max-h-80 rounded bg-slate-200 ${kecil ? "pixelated" : ""}`}
          />
        ))
      )}

      {langkah.legenda && (
        <div className="mt-3 flex flex-wrap gap-3 text-xs">
          {langkah.legenda.map((l) => (
            <span key={l.arah} className="flex items-center gap-1">
              <span className="inline-block h-3 w-3 rounded" style={{ backgroundColor: l.warna }} />
              {l.arah}
            </span>
          ))}
        </div>
      )}

      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
        {Object.entries(langkah.angka).map(([k, v]) => (
          <div key={k} className="flex gap-1">
            <dt className="text-slate-500">{k}:</dt>
            <dd className="font-mono">{String(v)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function KotakHasil({ hasil, batas, jarak }) {
  const navigate = useNavigate();
  const terdekat = jarak[0];

  if (hasil.status === "dikenali") {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-green-300 bg-green-50 p-4">
        <div>
          <p className="text-lg font-semibold text-green-800">{hasil.pesan}</p>
          <p className="text-sm text-green-700">Tangan {hasil.sisi}, jarak {hasil.jarak.toFixed(3)} (batas {batas.toFixed(2)})</p>
        </div>
        <button
          type="button"
          onClick={() => navigate(`/orang/${hasil.orang_id}`, { state: { sisi: hasil.sisi, jarak: hasil.jarak } })}
          className="rounded-lg bg-green-700 px-4 py-2 text-sm font-medium text-white hover:bg-green-800"
        >
          Lihat detail
        </button>
      </div>
    );
  }

  const warna = hasil.status === "gagal"
    ? "border-red-300 bg-red-50 text-red-800"
    : "border-orange-300 bg-orange-50 text-orange-800";
  return (
    <div className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${warna}`}>
      <div>
        <p className="text-lg font-semibold">{hasil.pesan}</p>
        {terdekat && (
          <p className="text-sm">Terdekat: {terdekat.nama} ({terdekat.sisi}), jarak {terdekat.jarak.toFixed(3)}</p>
        )}
      </div>
      <button
        type="button"
        onClick={() => navigate("/")}
        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
      >
        Scan ulang
      </button>
    </div>
  );
}

export default function Result() {
  const { state } = useLocation();
  if (!state?.hasil) return <Navigate to="/" replace />;

  const { langkah, jarak, batas, hasil } = state.hasil;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Hasil pemrosesan</h1>
      <KotakHasil hasil={hasil} batas={batas} jarak={jarak} />
      {langkah.map((l) => (
        <Langkah key={l.no} langkah={l} />
      ))}
    </div>
  );
}
