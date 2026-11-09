import { describe, expect, test } from "vitest";
import data from "../../../backend/tests/fixtures/landmarks_test.json";
import {
  batasVertikal,
  jariTerbuka,
  kotakRoi,
  menghadapKamera,
  periksa,
  sisiDariLabel,
} from "./validation.js";

const W = data.lebar;
const H = data.tinggi;

function lm(nama) {
  return data[nama].map(([x, y]) => ({ x: x / W, y: y / H, z: 0 }));
}

describe("validation", () => {
  // MediaPipe Tasks labels the real hand (no mirror assumption), unlike the Python backend.
  test("label to side", () => {
    expect(sisiDariLabel("Right")).toBe("kanan");
    expect(sisiDariLabel("Left")).toBe("kiri");
  });

  test("open hand passes, fist is rejected", () => {
    expect(jariTerbuka(lm("terbuka_kanan"), W, H)).toBe(true);
    expect(jariTerbuka(lm("kepal_kanan"), W, H)).toBe(false);
  });

  test("palm versus back of hand", () => {
    expect(menghadapKamera(lm("terbuka_kanan"), "kanan", W, H)).toBe(true);
    expect(menghadapKamera(lm("punggung_kanan"), "kanan", W, H)).toBe(false);
  });

  test("fist gives the open-fingers message", () => {
    const p = periksa(lm("kepal_kanan"), "Right", lm("kepal_kanan"), W, H);
    expect(p.semua).toBe(false);
    expect(p.pesan).toBe("Buka semua jari");
  });

  test("open and still hand passes every check", () => {
    const p = periksa(lm("terbuka_kanan"), "Right", lm("terbuka_kanan"), W, H);
    expect(p.semua).toBe(true);
    expect(p.sisi).toBe("kanan");
    expect(p.silang).toBeLessThan(0);
  });

  // The reported bug: right palm was rejected and the back of the right hand passed.
  test("back of right hand is rejected with the real Tasks label", () => {
    const p = periksa(lm("punggung_kanan"), "Right", lm("punggung_kanan"), W, H);
    expect(p.menghadap).toBe(false);
    expect(p.pesan).toBe("Tunjukkan telapak tangan, bukan punggung tangan");
  });

  test("no hand gives the placement message", () => {
    expect(periksa(null, null, null, W, H).pesan).toBe("Letakkan telapak di depan kamera");
  });
});

describe("ROI box size", () => {
  const sisiKotak = (t) => Math.hypot(t[1][0] - t[0][0], t[1][1] - t[0][1]);

  test("default box is one palm width wide", () => {
    const { titik } = kotakRoi(lm("terbuka_kanan"), W, H);
    expect(sisiKotak(titik)).toBeCloseTo(Math.hypot(360 - 272, 300 - 312), 5);
  });

  const tengah = (p, q) => [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];

  test("1.3x box is 1.3 times wider, its top rises and its bottom stays put", () => {
    const a = kotakRoi(lm("terbuka_kanan"), W, H).titik;
    const b = kotakRoi(lm("terbuka_kanan"), W, H, 1.3).titik;
    expect(sisiKotak(b)).toBeCloseTo(1.3 * sisiKotak(a), 5);
    // same bottom edge (the wrist), same horizontal centre
    expect(tengah(b[2], b[3])[0]).toBeCloseTo(tengah(a[2], a[3])[0], 5);
    expect(tengah(b[2], b[3])[1]).toBeCloseTo(tengah(a[2], a[3])[1], 5);
    // top edge is higher: the box is taller than the 1.0x one
    const tinggi = (t) => Math.hypot(...tengah(t[0], t[1]).map((v, i) => v - tengah(t[2], t[3])[i]));
    expect(tinggi(b)).toBeGreaterThan(tinggi(a));
  });

  test("vertical edges follow the same rule as the server", () => {
    expect(batasVertikal(1.0)).toEqual([0.15, 1.15]);
    expect(batasVertikal(0.8)[0]).toBeCloseTo(0.25, 10);
    expect(batasVertikal(0.8)[1]).toBeCloseTo(1.05, 10);
    expect(batasVertikal(1.3)).toEqual([0, 1.15]);
    expect(batasVertikal(1.5)).toEqual([0, 1.15]); // never above the finger-base line, never below the wrist
  });

  test("a box that leaves the frame fails the distance check", () => {
    // Hand moved far right: the 1.0x box still fits, the 1.5x box is wider and crosses the right edge.
    const kanan = lm("terbuka_kanan").map((p) => ({ ...p, x: p.x + 250 / W }));
    expect(periksa(kanan, "Right", kanan, W, H, 1.0).jarak).toBe(true);
    expect(periksa(kanan, "Right", kanan, W, H, 1.5).jarak).toBe(false);
  });
});
