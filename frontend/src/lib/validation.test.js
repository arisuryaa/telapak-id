import { describe, expect, test } from "vitest";
import data from "../../../backend/tests/fixtures/landmarks_test.json";
import {
  jariTerbuka,
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
