import { useState } from "react";
import { Link, useNavigate } from "react-router";
import PalmCamera from "../components/PalmCamera.jsx";
import ProcessingPanel from "../components/ProcessingPanel.jsx";
import { scan } from "../lib/api.js";

const BATAS_DEFAULT = 0.38;

function batasTersimpan() {
  try {
    const v = Number(localStorage.getItem("batas"));
    return v >= 0.1 && v <= 0.5 ? v : BATAS_DEFAULT;
  } catch {
    return BATAS_DEFAULT;
  }
}

export default function Scan() {
  const navigate = useNavigate();
  const [batas, setBatas] = useState(batasTersimpan);
  const [memproses, setMemproses] = useState(false);
  const [foto, setFoto] = useState(null);
  const [galat, setGalat] = useState(null);

  function ubahBatas(e) {
    const v = Number(e.target.value);
    setBatas(v);
    try {
      localStorage.setItem("batas", String(v));
    } catch {
      // private mode: the slider still works, it just will not be remembered
    }
  }

  async function onAmbil(frame) {
    setFoto(frame);
    setMemproses(true);
    setGalat(null);
    try {
      const hasil = await scan(frame, batas);
      navigate("/hasil", { state: { hasil } });
    } catch (err) {
      setGalat(err.message);
      setMemproses(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Scan telapak</h1>
          <p className="text-sm text-slate-600">Letakkan telapak di dalam kamera. Foto diambil otomatis.</p>
        </div>
        <div className="text-sm">
          <label className="flex items-center gap-3">
            <span className="whitespace-nowrap">Batas kecocokan {batas.toFixed(2)}</span>
            <input
              type="range"
              min="0.1"
              max="0.5"
              step="0.01"
              value={batas}
              onChange={ubahBatas}
              className="w-40"
            />
          </label>
          <p className="mt-1 max-w-xs text-xs text-slate-500">
            Dikenali jika jarak terkecil di bawah batas. Lebih kecil = lebih ketat.
          </p>
        </div>
      </div>

      {/* Keep the camera mounted (hidden) so it does not reload the model after an error. */}
      <div className={memproses ? "hidden" : ""}>
        <PalmCamera mode="sekali" onAmbil={onAmbil} aktif={!memproses} />
      </div>
      {memproses && (
        <ProcessingPanel
          foto={foto}
          judul="Memproses foto…"
          keterangan="Foto sudah diambil. Tangan boleh diturunkan."
        />
      )}
      {galat && (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {galat}{" "}
          <span className="text-slate-600">Silakan coba lagi.</span>
        </p>
      )}
      <p className="text-sm text-slate-500">
        Belum terdaftar? <Link to="/daftar" className="underline">Daftar di sini</Link>.
      </p>
    </div>
  );
}
