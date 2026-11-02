import { useEffect, useRef, useState } from "react";
import { HandLandmarker } from "@mediapipe/tasks-vision";
import { useHandTracker } from "../hooks/useHandTracker.js";
import { AMBANG, kotakRoi, periksa } from "../lib/validation.js";

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

  const prevLm = useRef(null);
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
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch(() => {
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
    const p = periksa(lm, hasil?.label ?? null, prevLm.current, w, h);
    prevLm.current = lm;
    setStatus(p);

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
          const { titik } = kotakRoi(lm, w, h);
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
  }, [hasil, aktif, siap]);

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
        <p className="mt-3 text-xs text-slate-500">
          Foto diambil otomatis jika semua syarat terpenuhi dan tangan ditahan sekitar 1 detik.
        </p>
      </aside>
    </div>
  );
}
