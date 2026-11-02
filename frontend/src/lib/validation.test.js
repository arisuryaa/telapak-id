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
  test("label to side", () => {
    expect(sisiDariLabel("Left")).toBe("kanan");
    expect(sisiDariLabel("Right")).toBe("kiri");
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
    const p = periksa(lm("kepal_kanan"), "Left", lm("kepal_kanan"), W, H);
    expect(p.semua).toBe(false);
    expect(p.pesan).toBe("Buka semua jari");
  });

  test("open and still hand passes every check", () => {
    const p = periksa(lm("terbuka_kanan"), "Left", lm("terbuka_kanan"), W, H);
    expect(p.semua).toBe(true);
    expect(p.sisi).toBe("kanan");
  });

  test("no hand gives the placement message", () => {
    expect(periksa(null, null, null, W, H).pesan).toBe("Letakkan telapak di depan kamera");
  });
});
