// Shared visual building blocks so every page speaks the same design language.

export const tombol = {
  utama:
    "inline-flex items-center justify-center gap-2 rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-white shadow-float transition-colors hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-50",
  kedua:
    "inline-flex items-center justify-center gap-2 rounded-full border border-line bg-white px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:border-brand/40 hover:bg-brand-soft disabled:cursor-not-allowed disabled:opacity-50",
  bahaya:
    "inline-flex items-center justify-center gap-2 rounded-full bg-err px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-err/90 disabled:opacity-50",
  teks:
    "inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-semibold text-brand hover:bg-brand-soft",
};

export const input =
  "w-full rounded-2xl border border-transparent bg-lilac px-4 py-3 text-sm text-ink placeholder:text-muted/70 transition-colors focus:border-brand focus:bg-white focus:outline-none";

export function Kartu({ className = "", children, ...rest }) {
  return (
    <div className={`rounded-3xl border border-white bg-white shadow-card ${className}`} {...rest}>
      {children}
    </div>
  );
}

export function JudulHalaman({ judul, keterangan, children }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">{judul}</h1>
        {keterangan && <p className="mt-2 text-base text-muted">{keterangan}</p>}
      </div>
      {children}
    </div>
  );
}

const GAYA_PESAN = {
  galat: "bg-err-soft text-err",
  peringatan: "bg-warn-soft text-warn",
  sukses: "bg-ok-soft text-ok",
  info: "bg-brand-soft text-brand-strong",
};

export function Pesan({ jenis = "info", className = "", children }) {
  return (
    <div role={jenis === "galat" ? "alert" : "status"} className={`rounded-2xl px-4 py-3 text-sm font-medium ${GAYA_PESAN[jenis]} ${className}`}>
      {children}
    </div>
  );
}

// Simple open-palm glyph. `cermin` flips it to draw a left hand.
export function IkonTangan({ cermin = false, className = "h-6 w-6" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={cermin ? { transform: "scaleX(-1)" } : undefined}
      aria-hidden="true"
    >
      <path d="M18 11V6a2 2 0 0 0-4 0v5" />
      <path d="M14 10V4a2 2 0 0 0-4 0v6" />
      <path d="M10 10.5V6a2 2 0 0 0-4 0v8" />
      <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15" />
    </svg>
  );
}

export function IkonCentang({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

export function IkonSilang({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className={className} aria-hidden="true">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}
