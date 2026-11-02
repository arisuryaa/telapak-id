// Client-side hand checks, mirrored from backend/validation.py.
// Landmarks are normalized (0..1); w and h are the frame size in pixels.

export const AMBANG = {
  rasioJari: 1.1,
  rasioJempol: 0.7,
  lebarMin: 0.12,
  lebarMax: 0.45,
  gerakMax: 0.012,
  tahanMs: 1000,
  jedaMs: 800,
};

// (fingertip, PIP joint) for index, middle, ring, little finger
const PASANGAN_JARI = [
  [8, 6],
  [12, 10],
  [16, 14],
  [20, 18],
];

const px = (lm, i, w, h) => ({ x: lm[i].x * w, y: lm[i].y * h });
const jarak = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

// MediaPipe Tasks (this browser library) reports the real hand on an unmirrored
// frame. The Python backend uses the legacy API, which assumes a mirrored image,
// so its mapping is the opposite ("Left" -> kanan). See backend/validation.py.
export const LABEL_KANAN = "Right";

export function sisiDariLabel(label) {
  return label === LABEL_KANAN ? "kanan" : "kiri";
}

// Cross product of wrist->index base and wrist->little base (image y points down).
// Its sign, together with the hand side, tells palm from back of hand.
export function silangTelapak(lm, w, h) {
  const p0 = px(lm, 0, w, h);
  const a = px(lm, 5, w, h);
  const b = px(lm, 17, w, h);
  return (a.x - p0.x) * (b.y - p0.y) - (a.y - p0.y) * (b.x - p0.x);
}

export function jariTerbuka(lm, w, h) {
  const p0 = px(lm, 0, w, h);
  for (const [ujung, pip] of PASANGAN_JARI) {
    if (jarak(px(lm, ujung, w, h), p0) <= AMBANG.rasioJari * jarak(px(lm, pip, w, h), p0)) {
      return false;
    }
  }
  const jempol = jarak(px(lm, 4, w, h), px(lm, 5, w, h));
  return jempol > AMBANG.rasioJempol * jarak(px(lm, 5, w, h), px(lm, 17, w, h));
}

export function menghadapKamera(lm, sisi, w, h) {
  const z = silangTelapak(lm, w, h);
  return sisi === "kanan" ? z < 0 : z > 0;
}

// Four corners of the palm ROI in frame pixels, mirroring palm.ambil_roi.
// skala grows the box around the same centre (1.0 = journal box, from the server's ROI_SKALA).
// `didalam` is false when any corner leaves the frame.
export function kotakRoi(lm, w, h, skala = 1) {
  const p5 = px(lm, 5, w, h);
  const p17 = px(lm, 17, w, h);
  const p0 = px(lm, 0, w, h);
  const c = { x: (p5.x + p17.x) / 2, y: (p5.y + p17.y) / 2 };
  const s = jarak(p5, p17);
  const u = { x: (p17.x - p5.x) / s, y: (p17.y - p5.y) / s };
  let n = { x: -u.y, y: u.x };
  if ((p0.x - c.x) * n.x + (p0.y - c.y) * n.y < 0) n = { x: -n.x, y: -n.y };

  const tambah = 0.5 * (skala - 1);
  const atas = 0.15 - tambah;
  const bawah = 1.15 + tambah;
  const titik = [];
  for (const [sign, k] of [[-1, atas], [1, atas], [1, bawah], [-1, bawah]]) {
    titik.push([
      c.x + sign * u.x * s * 0.5 * skala + n.x * k * s,
      c.y + sign * u.y * s * 0.5 * skala + n.y * k * s,
    ]);
  }
  const didalam = titik.every(([x, y]) => x >= 0 && x <= w && y >= 0 && y <= h);
  return { titik, didalam };
}

export function rataGerak(lmA, lmB) {
  if (!lmA || !lmB) return Infinity;
  let total = 0;
  for (let i = 0; i < lmA.length; i++) {
    total += Math.hypot(lmA[i].x - lmB[i].x, lmA[i].y - lmB[i].y);
  }
  return total / lmA.length;
}

export function periksa(lm, label, lmSebelum, w, h, skala = 1) {
  if (!lm) {
    return {
      terdeteksi: false, jari: false, menghadap: false, jarak: false,
      diam: false, semua: false, sisi: null, label: null, silang: null,
      pesan: "Letakkan telapak di depan kamera",
    };
  }
  const sisi = sisiDariLabel(label);
  const jari = jariTerbuka(lm, w, h);
  const menghadap = menghadapKamera(lm, sisi, w, h);
  const lebar = jarak(px(lm, 5, w, h), px(lm, 17, w, h)) / w;
  const jarakOk =
    lebar >= AMBANG.lebarMin && lebar <= AMBANG.lebarMax && kotakRoi(lm, w, h, skala).didalam;
  const diam = rataGerak(lm, lmSebelum) <= AMBANG.gerakMax;
  const semua = jari && menghadap && jarakOk && diam;

  let pesan = "Tahan...";
  if (!jari) pesan = "Buka semua jari";
  else if (!menghadap) pesan = "Tunjukkan telapak tangan, bukan punggung tangan";
  else if (!jarakOk) pesan = "Atur jarak tangan ke kamera";
  else if (!diam) pesan = "Tahan tangan agar diam";

  return {
    terdeteksi: true, jari, menghadap, jarak: jarakOk, diam, semua, sisi, label,
    silang: silangTelapak(lm, w, h), pesan,
  };
}
