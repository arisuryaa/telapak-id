// Shown in place of the live camera while the server works on a captured photo.
// The photo is mirrored like the live view, so it looks the same as a moment ago.
export default function ProcessingPanel({ foto, judul, keterangan }) {
  return (
    <div className="relative aspect-video overflow-hidden rounded-[28px] bg-ink shadow-float">
      {foto && (
        <img src={foto} alt="Foto yang diambil" className="h-full w-full object-cover opacity-35 -scale-x-100" />
      )}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-6 text-center text-white" role="status">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-white/20 border-t-brand" />
        <p className="text-xl font-bold tracking-tight">{judul}</p>
        {keterangan && <p className="text-sm text-white/75">{keterangan}</p>}
      </div>
    </div>
  );
}
