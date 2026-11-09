import { useEffect, useRef, useState } from "react";
import { HandLandmarker } from "@mediapipe/tasks-vision";
import { useHandTracker } from "../hooks/useHandTracker.js";
import { AMBANG, kotakRoi, periksa } from "../lib/validation.js";
import { log, logGalat } from "../lib/log.js";
import { ambilPengaturan } from "../lib/api.js";
import { IkonCentang, IkonTangan, Kartu } from "./ui.jsx";

const tanda = (ok) => (ok ? "✔" : "✖");

const WARNA_OK = "#2f6bef";
const WARNA_BELUM = "#f0a20b";

const CHECKS = [
  ["terdeteksi", "Tangan terlihat di kamera"],
  ["jari", "Kelima jari terbuka"],
  ["menghadap", "Telapak menghadap kamera"],
  ["jarak", "Jarak tangan pas"],
  ["diam", "Tangan diam"],
];

// mode "sekali": one photo, then stop. mode "beruntun": a photo every AMBANG.jedaMs while valid.
// onAmbil(frameDataUrl, { sisi }) is called with an unmirrored JPEG of the frame.
// samping: extra content shown above the checklist. kilat: changes to a new number > 0 to
// flash the camera border (the parent bumps it when a sample is accepted).
// pesanTahan: text shown while every check passes and the photo is about to be taken.
export default function PalmCamera({ mode = "sekali", onAmbil, aktif = true, samping, kilat = 0, pesanTahan }) {
  const videoRef = useRef(null);
  const overlayRef = useRef(null);
  const ambilRef = useRef(null);
  const { hasil, fps, siap, galat: galatModel } = useHandTracker(videoRef);

  const [kameraGalat, setKameraGalat] = useState(null);
  const [status, setStatus] = useState(() => periksa(null, null, null, 640, 480));
  const [sibuk, setSibuk] = useState(false);
  const [roiSkala, setRoiSkala] = useState(1);
  const [tahan, setTahan] = useState(0); // 0..1, how far the current hold is toward the next photo

  const prevLm = useRef(null);
  const kunciLogTerakhir = useRef("");
  const tahanMulai = useRef(null);
  const siklus = useRef(null); // { mulai, durasi } of the hold that ends in the next photo
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
      siklus.current = null;
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
        const warna = p.semua ? WARNA_OK : WARNA_BELUM;
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
        ctx.fillStyle = "#ffffff";
        for (const pt of lm) {
          ctx.beginPath();
          ctx.arc(pt.x * w, pt.y * h, 4.5, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }
        if (p.semua) {
          const { titik } = kotakRoi(lm, w, h, roiSkala);
          ctx.beginPath();
          titik.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
          ctx.closePath();
          ctx.fillStyle = "rgba(47,107,239,0.18)";
          ctx.fill();
          ctx.stroke();
        }
      }
    }

    if (!aktif || !siap || !video || selesai.current) {
      setTahan(0);
      return;
    }
    if (sibukRef.current) {
      setTahan(1);
      return;
    }
    if (!p.semua) {
      tahanMulai.current = null;
      siklus.current = null;
      setTahan(0);
      return;
    }
    const kini = performance.now();
    tahanMulai.current ??= kini;
    siklus.current ??= { mulai: kini, durasi: AMBANG.tahanMs };
    setTahan(Math.round(Math.min(1, (kini - siklus.current.mulai) / siklus.current.durasi) * 50) / 50);
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
          const kini2 = performance.now();
          berikutnya.current = kini2 + AMBANG.jedaMs;
          siklus.current = { mulai: kini2, durasi: AMBANG.jedaMs };
        }
      });
  }, [hasil, aktif, siap, roiSkala]);

  const galat = kameraGalat ?? galatModel;
  const memuat = !siap && !galat;
  const siapAmbil = aktif && siap && status.semua;
  const pesan = memuat
    ? "Menyiapkan kamera dan model tangan…"
    : sibuk
      ? "Memproses foto…"
      : siapAmbil
        ? (pesanTahan ?? "Tahan posisi ini…")
        : status.pesan;
  const gagalPertama = CHECKS.find(([kunci]) => !status[kunci])?.[0];

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_20rem]">
      <div className="relative aspect-video overflow-hidden rounded-[28px] bg-ink shadow-float">
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

        {/* Where to put the hand, until one is seen. */}
        {!galat && !memuat && !status.terdeteksi && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="flex aspect-[3/4] h-3/5 items-center justify-center rounded-[40px] border-2 border-dashed border-white/50">
              <IkonTangan className="h-1/2 w-1/2 text-white/40" />
            </div>
          </div>
        )}

        {kilat > 0 && <div key={kilat} className="animasi-kilat pointer-events-none absolute inset-0 rounded-[28px]" />}

        <div className="absolute top-3 right-3 rounded-full bg-black/50 px-2.5 py-1 text-xs font-semibold text-white tabular-nums backdrop-blur">
          {fps} FPS
        </div>

        {galat ? (
          <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-sm font-medium text-white">
            {galat}
          </div>
        ) : (
          <div className="absolute inset-x-0 bottom-4 flex justify-center px-4">
            <div
              aria-live="polite"
              className={`min-w-0 max-w-full overflow-hidden rounded-2xl px-4 py-2.5 text-center text-sm font-semibold shadow-lg backdrop-blur ${
                siapAmbil || sibuk ? "bg-brand text-white" : "bg-white/95 text-ink"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                {memuat && <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-brand/30 border-t-brand" />}
                {!memuat && !siapAmbil && !sibuk && <span className="h-2 w-2 shrink-0 rounded-full bg-warn-bar" />}
                <span className="truncate">{pesan}</span>
              </span>
              {siapAmbil && (
                <span className="mt-2 block h-1.5 w-full min-w-48 overflow-hidden rounded-full bg-white/30">
                  <span
                    className="block h-full rounded-full bg-white transition-[width] duration-100"
                    style={{ width: `${tahan * 100}%` }}
                  />
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      <Kartu className="flex flex-col gap-5 p-5">
        {samping}
        <div>
          <h3 className="mb-3 text-sm font-bold text-ink">Syarat foto</h3>
          <ul className="space-y-1.5 text-sm">
            {CHECKS.map(([kunci, teks]) => {
              const ok = status[kunci];
              const sekarang = !memuat && kunci === gagalPertama;
              return (
                <li
                  key={kunci}
                  className={`flex items-center gap-3 rounded-xl px-2.5 py-1.5 ${
                    sekarang ? "bg-warn-soft font-semibold text-ink" : ok ? "text-ink" : "text-muted"
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${
                      ok ? "bg-brand text-white" : sekarang ? "border-2 border-warn-bar" : "border-2 border-line"
                    }`}
                  >
                    {ok && <IkonCentang className="h-3 w-3" />}
                  </span>
                  {teks}
                </li>
              );
            })}
          </ul>
        </div>
        <p className="text-xs leading-relaxed text-muted">
          Foto diambil otomatis saat semua syarat terpenuhi dan tangan ditahan sekitar 1 detik.
        </p>
        <details className="text-xs text-muted">
          <summary className="cursor-pointer font-semibold select-none hover:text-ink">Info teknis</summary>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 tabular-nums">
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
      </Kartu>
    </div>
  );
}
