// Horizontal bars: distance to each enrolled hand, with the threshold marked.
// Bars under the threshold are green (recognized); the rest are grey.
const SKALA_MAKS = 0.5;

export default function DistanceChart({ jarak, batas }) {
  if (jarak.length === 0) {
    return <p className="text-sm text-slate-500">Belum ada data untuk dibandingkan.</p>;
  }
  const garisBatas = `${(batas / SKALA_MAKS) * 100}%`;

  return (
    <div className="relative space-y-2 pt-2">
      <div
        className="absolute top-0 bottom-0 w-px bg-slate-700"
        style={{ left: garisBatas }}
        title={`Batas ${batas.toFixed(2)}`}
      />
      {jarak.map((d) => {
        const lebar = `${Math.min(1, d.jarak / SKALA_MAKS) * 100}%`;
        const dikenali = d.jarak < batas;
        return (
          <div key={d.telapak_id} className="text-sm">
            <div className="mb-0.5 flex justify-between">
              <span>{d.nama} ({d.sisi})</span>
              <span className="font-mono">{d.jarak.toFixed(3)}</span>
            </div>
            <div className="h-3 rounded bg-slate-200">
              <div
                className={`h-3 rounded ${dikenali ? "bg-green-500" : "bg-slate-400"}`}
                style={{ width: lebar }}
              />
            </div>
          </div>
        );
      })}
      <div className="flex justify-between pt-1 font-mono text-xs text-slate-500">
        <span>0</span>
        <span>batas {batas.toFixed(2)}</span>
        <span>{SKALA_MAKS}</span>
      </div>
    </div>
  );
}
