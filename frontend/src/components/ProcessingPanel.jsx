// Shown in place of the live camera while the server works on a captured photo.
// The photo is mirrored like the live view, so it looks the same as a moment ago.
export default function ProcessingPanel({ foto, judul, keterangan }) {
  return (
    <div className="relative aspect-video overflow-hidden rounded-xl bg-slate-900">
      {foto && (
        <img src={foto} alt="Foto yang diambil" className="h-full w-full object-cover opacity-40 -scale-x-100" />
      )}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center text-white">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-white/30 border-t-white" />
        <p className="text-lg font-semibold">{judul}</p>
        {keterangan && <p className="text-sm text-white/80">{keterangan}</p>}
      </div>
    </div>
  );
}
