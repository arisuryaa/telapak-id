// Horizontal bars: distance to each enrolled hand, with the threshold marked.
// Bars under the threshold are blue (recognized); the rest are grey.
// `maks` is the far end of the scale: 0.5 for Gabor, 1.0 for Canny (the server sends it with the result).
export default function DistanceChart({ jarak, batas, maks = 0.5 }) {
  if (jarak.length === 0) {
    return <p className="text-sm text-muted">Belum ada data terdaftar untuk dibandingkan.</p>;
  }
  const SKALA_MAKS = maks;
  const garisBatas = `${(batas / SKALA_MAKS) * 100}%`;

  return (
    <div className="space-y-3">
      <div className="relative space-y-3">
        <div
          className="absolute -top-1 -bottom-1 z-10 border-l-2 border-dashed border-ink/60"
          style={{ left: garisBatas }}
          title={`Batas ${batas.toFixed(2)}`}
        />
        {jarak.map((d) => {
          const lebar = `${Math.max(2, Math.min(1, d.jarak / SKALA_MAKS) * 100)}%`;
          const dikenali = d.jarak < batas;
          return (
            <div key={d.telapak_id} className="text-sm">
              <div className="mb-1 flex justify-between gap-3">
                <span className={dikenali ? "font-semibold text-ink" : "text-muted"}>
                  {d.nama} <span className="text-muted">(tangan {d.sisi})</span>
                </span>
                <span className="font-semibold tabular-nums">{d.jarak.toFixed(3)}</span>
              </div>
              <div className="h-3 rounded-full bg-lilac">
                <div
                  className={`h-3 rounded-full ${dikenali ? "bg-brand" : "bg-muted/35"}`}
                  style={{ width: lebar }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="relative h-4 text-xs text-muted tabular-nums">
        <span className="absolute left-0">0</span>
        <span className="absolute -translate-x-1/2 font-semibold text-ink" style={{ left: garisBatas }}>
          batas {batas.toFixed(2)}
        </span>
        <span className="absolute right-0">{SKALA_MAKS}</span>
      </div>
    </div>
  );
}
