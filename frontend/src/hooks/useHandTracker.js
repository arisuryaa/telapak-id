import { useEffect, useState } from "react";
import { FilesetResolver, HandLandmarker } from "@mediapipe/tasks-vision";

// Runs MediaPipe Hands on the live <video> in the browser and reports the
// latest landmarks, the detection rate (FPS), and whether the model is ready.
export function useHandTracker(videoRef) {
  const [hasil, setHasil] = useState(null);
  const [fps, setFps] = useState(0);
  const [siap, setSiap] = useState(false);
  const [galat, setGalat] = useState(null);

  useEffect(() => {
    let aktif = true;
    let landmarker = null;
    let frameId = null;
    let terakhirWaktuVideo = -1;
    let hitungan = 0;
    let waktuAwalFps = performance.now();

    async function muat() {
      try {
        const fileset = await FilesetResolver.forVisionTasks("/mediapipe/wasm");
        const opsi = {
          runningMode: "VIDEO",
          numHands: 1,
          minHandDetectionConfidence: 0.6,
          minTrackingConfidence: 0.6,
        };
        try {
          landmarker = await HandLandmarker.createFromOptions(fileset, {
            ...opsi,
            baseOptions: { modelAssetPath: "/mediapipe/hand_landmarker.task", delegate: "GPU" },
          });
        } catch {
          // Some browsers have no WebGL GPU support; fall back to the CPU.
          landmarker = await HandLandmarker.createFromOptions(fileset, {
            ...opsi,
            baseOptions: { modelAssetPath: "/mediapipe/hand_landmarker.task", delegate: "CPU" },
          });
        }
        if (!aktif) return;
        setSiap(true);
        frameId = requestAnimationFrame(loop);
      } catch (err) {
        if (aktif) setGalat(`Model tangan gagal dimuat: ${err.message}`);
      }
    }

    function loop() {
      if (!aktif) return;
      const video = videoRef.current;
      if (landmarker && video && video.readyState >= 2 && video.currentTime !== terakhirWaktuVideo) {
        terakhirWaktuVideo = video.currentTime;
        const res = landmarker.detectForVideo(video, performance.now());
        const lm = res.landmarks?.[0] ?? null;
        const label = res.handedness?.[0]?.[0]?.categoryName ?? null;
        setHasil(lm ? { lm, label } : null);

        hitungan += 1;
        const sekarang = performance.now();
        if (sekarang - waktuAwalFps >= 500) {
          setFps(Math.round((hitungan * 1000) / (sekarang - waktuAwalFps)));
          hitungan = 0;
          waktuAwalFps = sekarang;
        }
      }
      frameId = requestAnimationFrame(loop);
    }

    muat();

    return () => {
      aktif = false;
      if (frameId !== null) cancelAnimationFrame(frameId);
      landmarker?.close();
    };
  }, [videoRef]);

  return { hasil, fps, siap, galat };
}
