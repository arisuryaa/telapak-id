import { Link, Navigate, useLocation, useNavigate } from "react-router";
import DistanceChart from "../components/DistanceChart.jsx";
import { IkonCentang, IkonSilang, Kartu, tombol } from "../components/ui.jsx";

const PIXELATED = new Set([4, 5, 6, 7]); // small maps: keep them sharp, not blurred

function Langkah({ langkah, terakhir }) {
  const kecil = PIXELATED.has(langkah.no);
  return (
    <li className="relative grid grid-cols-[2.5rem_1fr] gap-4">
      {/* The timeline rail joining one step to the next. */}
      {!terakhir && <span className="absolute top-11 bottom-[-1.25rem] left-5 w-0.5 -translate-x-1/2 bg-line" aria-hidden="true" />}
      <span className="relative z-10 flex h-10 w-10 items-center justify-center rounded-full bg-brand text-sm font-bold text-white shadow-float">
        {langkah.no}
      </span>
      <Kartu className="min-w-0 p-5">
        <h2 className="text-lg font-bold tracking-tight text-ink">{langkah.judul}</h2>
        <p className="mt-1 mb-4 text-sm text-muted">{langkah.penjelasan}</p>

        {langkah.no === 8 ? (
          <DistanceChart jarak={langkah.jarak} batas={langkah.angka.batas} />
        ) : langkah.gambar.length > 1 ? (
          <div className={`grid gap-3 ${langkah.gambar.length === 2 ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-3 sm:grid-cols-6"}`}>
            {langkah.gambar.map((g) => (
              <figure key={g.label} className="text-center text-xs text-muted">
                <img src={g.src} alt={g.label} className={`w-full rounded-xl bg-lilac ${kecil && !g.halus ? "pixelated" : ""}`} />
                <figcaption className="mt-1.5 font-medium">{g.label}</figcaption>
              </figure>
            ))}
          </div>
        ) : (
          langkah.gambar.map((g) => (
            <img
              key={g.label}
              src={g.src}
              alt={g.label}
              className={`max-h-80 rounded-2xl bg-lilac ${kecil ? "pixelated" : ""}`}
            />
          ))
        )}

        {langkah.legenda && (
          <div className="mt-4 flex flex-wrap gap-3 text-xs text-muted">
            {langkah.legenda.map((l) => (
              <span key={l.arah} className="flex items-center gap-1.5">
                <span className="inline-block h-3 w-3 rounded" style={{ backgroundColor: l.warna }} />
                {l.arah}
              </span>
            ))}
          </div>
        )}

        <dl className="mt-4 flex flex-wrap gap-2 text-xs">
          {Object.entries(langkah.angka).map(([k, v]) => (
            <div key={k} className="flex gap-1.5 rounded-full bg-canvas px-3 py-1">
              <dt className="text-muted">{k}</dt>
              <dd className="font-semibold text-ink tabular-nums">{String(v)}</dd>
            </div>
          ))}
        </dl>
      </Kartu>
    </li>
  );
}

const GAYA_HASIL = {
  dikenali: { ikon: "bg-ok text-white", latar: "bg-ok-soft" },
  tidak_dikenal: { ikon: "bg-warn-bar text-white", latar: "bg-warn-soft" },
  gagal: { ikon: "bg-err text-white", latar: "bg-err-soft" },
};

function KotakHasil({ hasil, batas, jarak }) {
  const navigate = useNavigate();
  const terdekat = jarak[0];
  const dikenali = hasil.status === "dikenali";
  const gaya = GAYA_HASIL[hasil.status] ?? GAYA_HASIL.gagal;

  return (
    <Kartu className="overflow-hidden">
      <div className={`flex flex-wrap items-center gap-5 p-6 sm:p-8 ${gaya.latar}`}>
        <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full ${gaya.ikon}`}>
          {dikenali ? <IkonCentang className="h-7 w-7" /> : <IkonSilang className="h-7 w-7" />}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">{hasil.pesan}</p>
          <p className="mt-1 text-sm text-muted">
            {dikenali
              ? `Tangan ${hasil.sisi}, jarak ${hasil.jarak.toFixed(3)} (batas ${batas.toFixed(2)})`
              : terdekat
                ? `Paling mirip: ${terdekat.nama} (tangan ${terdekat.sisi}), jarak ${terdekat.jarak.toFixed(3)}`
                : "Belum ada data terdaftar untuk dibandingkan."}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {dikenali && (
            <button
              type="button"
              onClick={() => navigate(`/orang/${hasil.orang_id}`, { state: { sisi: hasil.sisi, jarak: hasil.jarak } })}
              className={tombol.utama}
            >
              Lihat detail
            </button>
          )}
          <Link to="/" className={dikenali ? tombol.kedua : tombol.utama}>Scan ulang</Link>
        </div>
      </div>
    </Kartu>
  );
}

export default function Result() {
  const { state } = useLocation();
  if (!state?.hasil) return <Navigate to="/" replace />;

  const { langkah, jarak, batas, hasil } = state.hasil;
  return (
    <div className="space-y-10">
      <KotakHasil hasil={hasil} batas={batas} jarak={jarak} />
      <section className="space-y-5">
        <div>
          <h2 className="text-2xl font-extrabold tracking-tight text-ink">Cara sistem sampai ke jawaban ini</h2>
          <p className="mt-1 text-muted">Gambar di bawah adalah data asli dari setiap tahap pemrosesan foto tadi.</p>
        </div>
        <ol className="space-y-5">
          {langkah.map((l, i) => (
            <Langkah key={l.no} langkah={l} terakhir={i === langkah.length - 1} />
          ))}
        </ol>
      </section>
    </div>
  );
}
