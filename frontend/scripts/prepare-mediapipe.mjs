// Copies the MediaPipe WASM files and downloads the hand model into public/,
// so the app runs without internet access during a demo.
import { cpSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "public", "mediapipe");
const wasmSrc = join(root, "node_modules", "@mediapipe", "tasks-vision", "wasm");
const modelUrl =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";
const modelOut = join(out, "hand_landmarker.task");

try {
  mkdirSync(out, { recursive: true });
  if (existsSync(wasmSrc)) {
    cpSync(wasmSrc, join(out, "wasm"), { recursive: true });
  }
  if (!existsSync(modelOut)) {
    const res = await fetch(modelUrl);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    writeFileSync(modelOut, Buffer.from(await res.arrayBuffer()));
  }
  console.log("MediaPipe assets ready in public/mediapipe");
} catch (err) {
  // Do not fail npm install; the app will show a camera error until this is fixed.
  console.warn(`Could not prepare MediaPipe assets (${err.message}). Run "npm run prepare-mediapipe" with internet access.`);
}
