import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import PalmCamera from "../components/PalmCamera.jsx";
import ProcessingPanel from "../components/ProcessingPanel.jsx";
import { JudulHalaman, Pesan } from "../components/ui.jsx";
import { ambilPengaturan, scan } from "../lib/api.js";

// Used until the server answers, and if it cannot be reached. These are the Gabor values the app started with.
const CADANGAN = { metode: "gabor", metode_nama: "Gabor", batas_default: 0.38, batas_min: 0.1, batas_maks: 0.5 };

// Each method has its own distance scale, so the remembered threshold is kept per method.
function batasTersimpan(p) {
  try {
    const v = Number(localStorage.getItem(`batas_${p.metode}`));
    return v >= p.batas_min && v <= p.batas_maks ? v : p.batas_default;
  } catch {
    return p.batas_default;
  }
}

export default function Scan() {
  const navigate = useNavigate();
  const [pengaturan, setPengaturan] = useState(null);
  const [batas, setBatas] = useState(null);
  const [memproses, setMemproses] = useState(false);
  const [foto, setFoto] = useState(null);
  const [galat, setGalat] = useState(null);

  useEffect(() => {
    ambilPengaturan()
      .then((p) => {
        setPengaturan(p);
        setBatas(batasTersimpan(p));
      })
      .catch(() => {
        setPengaturan(CADANGAN);
        setBatas(CADANGAN.batas_default);
      });
  }, []);

  const p = pengaturan ?? CADANGAN;
  const nilai = batas ?? p.batas_default;

  function ubahBatas(e) {
    const v = Number(e.target.value);
    setBatas(v);
    try {
      localStorage.setItem(`batas_${p.metode}`, String(v));
    } catch {
      // private mode: the slider still works, it just will not be remembered
    }
  }

  async function onAmbil(frame) {
    setFoto(frame);
    setMemproses(true);
    setGalat(null);
    try {
      const hasil = await scan(frame, nilai);
      navigate("/hasil", { state: { hasil } });
    } catch (err) {
      setGalat(err.message);
      setMemproses(false);
    }
  }

  const persen = ((nilai - p.batas_min) / (p.batas_maks - p.batas_min)) * 100;

  return (
    <div className="space-y-8">
      <JudulHalaman
        judul="Siapa pemilik telapak ini?"
        keterangan="Tunjukkan telapak tangan ke kamera. Foto diambil otomatis, lalu sistem mencocokkannya dengan data terdaftar."
      >
        <label className="w-full max-w-xs rounded-2xl border border-white bg-white/80 p-4 text-sm shadow-card sm:w-72">
          <span className="flex items-baseline justify-between">
            <span className="font-semibold text-ink">Batas kecocokan</span>
            <span className="text-base font-bold text-brand tabular-nums">{nilai.toFixed(2)}</span>
          </span>
          <input
            type="range"
            min={p.batas_min}
            max={p.batas_maks}
            step="0.01"
            value={nilai}
            onChange={ubahBatas}
            className="mt-3 h-2 w-full cursor-pointer appearance-none rounded-full accent-brand"
            style={{ background: `linear-gradient(to right, #2f6bef ${persen}%, #e6e8fb ${persen}%)` }}
          />
          <span className="mt-2 flex justify-between text-xs text-muted">
            <span>Lebih ketat</span>
            <span>Lebih longgar</span>
          </span>
          <span className="mt-2 block text-xs text-muted">Metode pengenalan: {p.metode_nama}</span>
        </label>
      </JudulHalaman>

      {/* Keep the camera mounted (hidden) so it does not reload the model after an error. */}
      <div className={memproses ? "hidden" : ""}>
        <PalmCamera mode="sekali" onAmbil={onAmbil} aktif={!memproses} pesanTahan="Tahan posisi ini…" />
      </div>
      {memproses && (
        <ProcessingPanel
          foto={foto}
          judul="Mencocokkan telapak…"
          keterangan="Foto sudah diambil. Tangan boleh diturunkan."
        />
      )}
      {galat && (
        <Pesan jenis="galat">
          {galat} Tunjukkan telapak sekali lagi untuk mencoba ulang.
        </Pesan>
      )}
      <p className="text-sm text-muted">
        Belum terdaftar?{" "}
        <Link to="/daftar" className="font-semibold text-brand hover:underline">Daftarkan telapakmu</Link>
      </p>
    </div>
  );
}
