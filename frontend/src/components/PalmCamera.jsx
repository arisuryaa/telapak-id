import { useEffect, useRef, useState } from "react";
import { HandLandmarker } from "@mediapipe/tasks-vision";
import { useHandTracker } from "../hooks/useHandTracker.js";
import { AMBANG, kotakRoi, periksa } from "../lib/validation.js";
import { log, logGalat } from "../lib/log.js";
import { ambilPengaturan } from "../lib/api.js";

const tanda = (ok) => (ok ? "✔" : "✖");

const CHECKS = [
  ["terdeteksi", "Tangan terdeteksi"],
  ["jari", "Kelima jari terbuka"],
  ["menghadap", "Telapak menghadap kamera"],
  ["jarak", "Jarak pas"],
  ["diam", "Tangan diam"],
];

// mode "sekali": one photo, then stop. mode "beruntun": a photo every AMBANG.jedaMs while valid.
// onAmbil(frameDataUrl, { sisi }) is called with an unmirrored JPEG of the frame.
export default function PalmCamera({ mode = "sekali", onAmbil, aktif = true }) {
  const videoRef = useRef(null);
  const overlayRef = useRef(null);
  const ambilRef = useRef(null);
  const { hasil, fps, siap, galat: galatModel } = useHandTracker(videoRef);

  const [kameraGalat, setKameraGalat] = useState(null);
  const [status, setStatus] = useState(() => periksa(null, null, null, 640, 480));
  const [sibuk, setSibuk] = useState(false);
  const [roiSkala, setRoiSkala] = useState(1);

  const prevLm = useRef(null);
  const kunciLogTerakhir = useRef("");
  const tahanMulai = useRef(null);
  const berikutnya = useRef(0);
  const selesai = useRef(false);
  const sibukRef = useRef(false);
  const onAmbilRef = useRef(onAmbil);
  const modeRef = useRef(mode);
  useEffect(() => {
    onAmbilRef.current = onAmbil;
    modeRef.current = mode;
  }, [onAmbil, mode]);

  // The server decides the ROI box size; draw and check the same box here.
  useEffect(() => {
    ambilPengaturan()
      .then((p) => setRoiSkala(p.roi_skala))
      .catch((err) => logGalat(`pengaturan gagal dimuat, memakai kotak 1×: ${err.message}`));
  }, []);

  // Open the camera once; release it on unmount.
  useEffect(() => {
    let stream = null;
    let batal = false;
    navigator.mediaDevices
      .getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" } })
      .then((s) => {
        if (batal) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
        stream = s;
        const { width, height } = s.getVideoTracks()[0]?.getSettings() ?? {};
        log(`kamera aktif ${width}×${height}`);
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch((err) => {
        logGalat(`kamera gagal: ${err.name}: ${err.message}`);
        if (!batal) {
          setKameraGalat("Kamera tidak bisa dibuka. Izinkan akses kamera di browser lalu muat ulang halaman.");
        }
      });
    return () => {
      batal = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // Each time the parent turns capturing back on, allow a new capture.
  useEffect(() => {
    if (aktif) {
      selesai.current = false;
      tahanMulai.current = null;
    }
  }, [aktif]);

  // Every detection: check the hand, draw the overlay, and capture when it has held still long enough.
  useEffect(() => {
    const video = videoRef.current;
    const w = video?.videoWidth || 640;
    const h = video?.videoHeight || 480;
    const lm = hasil?.lm ?? null;
    const p = periksa(lm, hasil?.label ?? null, prevLm.current, w, h, roiSkala);
    prevLm.current = lm;
    setStatus(p);

    // Log only when the label or a check result changes, not on every frame.
    const kunciLog = [p.label, p.sisi, p.jari, p.menghadap, p.jarak, p.diam].join("|");
    if (kunciLog !== kunciLogTerakhir.current) {
      kunciLogTerakhir.current = kunciLog;
      log(
        lm
          ? `tangan label=${p.label} sisi=${p.sisi} silang=${p.silang.toFixed(0)} ` +
            `jari=${tanda(p.jari)} menghadap=${tanda(p.menghadap)} jarak=${tanda(p.jarak)} ` +
            `diam=${tanda(p.diam)} → ${p.pesan}`
          : "tangan tidak terdeteksi",
      );
    }

    const canvas = overlayRef.current;
    if (canvas) {
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, w, h);
      if (lm) {
        const warna = p.semua ? "#22c55e" : "#ef4444";
        ctx.strokeStyle = warna;
        ctx.fillStyle = warna;
        ctx.lineWidth = 3;
        // MediaPipe connections are objects: { start, end }, not pairs.
        for (const { start, end } of HandLandmarker.HAND_CONNECTIONS) {
          ctx.beginPath();
          ctx.moveTo(lm[start].x * w, lm[start].y * h);
          ctx.lineTo(lm[end].x * w, lm[end].y * h);
          ctx.stroke();
        }
        for (const pt of lm) {
          ctx.beginPath();
          ctx.arc(pt.x * w, pt.y * h, 4, 0, Math.PI * 2);
          ctx.fill();
        }
        if (p.semua) {
          const { titik } = kotakRoi(lm, w, h, roiSkala);
          ctx.beginPath();
          titik.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
          ctx.closePath();
          ctx.fillStyle = "rgba(34,197,94,0.15)";
          ctx.fill();
          ctx.stroke();
        }
      }
    }

    if (!aktif || !siap || !video || sibukRef.current || selesai.current) return;
    if (!p.semua) {
      tahanMulai.current = null;
      return;
    }
    const kini = performance.now();
    tahanMulai.current ??= kini;
    const cukupTahan = kini - tahanMulai.current >= AMBANG.tahanMs;
    if (!cukupTahan || kini < berikutnya.current) return;

    const kanvas = ambilRef.current ?? (ambilRef.current = document.createElement("canvas"));
    kanvas.width = w;
    kanvas.height = h;
    kanvas.getContext("2d").drawImage(video, 0, 0, w, h);
    const frame = kanvas.toDataURL("image/jpeg", 0.92);
    log(`foto diambil ${w}×${h} sisi=${p.sisi} (${Math.round(frame.length / 1024)} KB)`);
    sibukRef.current = true;
    setSibuk(true);
    Promise.resolve(onAmbilRef.current?.(frame, { sisi: p.sisi }))
      .finally(() => {
        sibukRef.current = false;
        setSibuk(false);
        if (modeRef.current === "sekali") {
          selesai.current = true;
        } else {
          berikutnya.current = performance.now() + AMBANG.jedaMs;
        }
      });
  }, [hasil, aktif, siap, roiSkala]);

  const galat = kameraGalat ?? galatModel;
  const pesan = !siap && !galat
    ? "Memuat model tangan…"
    : sibuk ? "Memproses…" : status.pesan;

  return (
    <div className="grid gap-4 md:grid-cols-[1fr_16rem]">
      <div className="relative aspect-video overflow-hidden rounded-xl bg-slate-900">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="h-full w-full object-cover -scale-x-100"
        />
        <canvas
          ref={overlayRef}
          className="pointer-events-none absolute inset-0 h-full w-full object-cover -scale-x-100"
        />
        <div className="absolute top-2 right-2 rounded bg-black/60 px-2 py-0.5 font-mono text-xs text-green-300">
          {fps} FPS
        </div>
        {galat ? (
          <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-white">
            {galat}
          </div>
        ) : (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-black/70 px-3 py-1 text-xs font-semibold text-white">
            {pesan}
          </div>
        )}
      </div>

      <aside className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold">Syarat foto</h3>
        <ul className="space-y-1.5 text-sm">
          {CHECKS.map(([kunci, teks]) => (
            <li key={kunci} className={status[kunci] ? "text-green-700" : "text-slate-500"}>
              <span className="mr-2 font-bold">{status[kunci] ? "✔" : "✖"}</span>
              {teks}
            </li>
          ))}
        </ul>
        <details className="mt-3 text-xs text-slate-600">
          <summary className="cursor-pointer select-none">Info teknis</summary>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 font-mono">
            <dt>label</dt>
            <dd>{status.label ?? "-"}</dd>
            <dt>sisi</dt>
            <dd>{status.sisi ?? "-"}</dd>
            <dt>silang</dt>
            <dd>{status.silang?.toFixed(0) ?? "-"}</dd>
            <dt>kotak</dt>
            <dd>{roiSkala}× lebar telapak</dd>
          </dl>
          <p className="mt-1">Tangan kanan: telapak jika silang &lt; 0. Tangan kiri: telapak jika silang &gt; 0.</p>
        </details>
        <p className="mt-3 text-xs text-slate-500">
          Foto diambil otomatis jika semua syarat terpenuhi dan tangan ditahan sekitar 1 detik.
        </p>
      </aside>
    </div>
  );
}
