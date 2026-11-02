import { describe, expect, test } from "vitest";
import data from "../../../backend/tests/fixtures/landmarks_test.json";
import {
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

  test("1.3x box is 1.3 times wider around the same centre", () => {
    const a = kotakRoi(lm("terbuka_kanan"), W, H).titik;
    const b = kotakRoi(lm("terbuka_kanan"), W, H, 1.3).titik;
    expect(sisiKotak(b)).toBeCloseTo(1.3 * sisiKotak(a), 5);
    const pusat = (t) => [t.reduce((s, p) => s + p[0], 0) / 4, t.reduce((s, p) => s + p[1], 0) / 4];
    expect(pusat(b)[0]).toBeCloseTo(pusat(a)[0], 5);
    expect(pusat(b)[1]).toBeCloseTo(pusat(a)[1], 5);
  });

  test("a box that leaves the frame fails the distance check", () => {
    // Hand moved 60 px down: the 1.0x box still fits, the 1.5x box crosses the bottom edge.
    const rendah = lm("terbuka_kanan").map((p) => ({ ...p, y: p.y + 60 / H }));
    expect(periksa(rendah, "Right", rendah, W, H, 1.0).jarak).toBe(true);
    expect(periksa(rendah, "Right", rendah, W, H, 1.5).jarak).toBe(false);
  });
});
