// "kanan (1.3×), kiri (1×)": each enrolled hand with the ROI box size it was made with.
export function formatTangan(orang) {
  return orang.tangan
    .map((sisi) => `${sisi} (${orang.skala_tangan?.[sisi] ?? 1}×)`)
    .join(", ");
}
