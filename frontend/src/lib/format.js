const NAMA_METODE = { gabor: "Gabor", canny: "Canny" };

// "kanan (1.3×, Canny), kiri (1×, Gabor)": each enrolled hand with the ROI box size and the method it was made with.
export function formatTangan(orang) {
  return orang.tangan
    .map((sisi) => {
      const metode = orang.metode_tangan?.[sisi] ?? "gabor";
      return `${sisi} (${orang.skala_tangan?.[sisi] ?? 1}×, ${NAMA_METODE[metode] ?? metode})`;
    })
    .join(", ");
}
