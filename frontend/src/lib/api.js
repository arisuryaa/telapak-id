// Thin wrapper around the Flask API. Errors carry the server's Indonesian message.

async function kirim(path, opsi = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opsi,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    // 204 No Content and plain-text errors have no JSON body
  }
  if (!res.ok) {
    const err = new Error(data?.pesan ?? `Permintaan gagal (${res.status})`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const scan = (frame, batas) =>
  kirim("/api/scan", { method: "POST", body: JSON.stringify({ frame, batas }) });

export const sampel = (frame) =>
  kirim("/api/sampel", { method: "POST", body: JSON.stringify({ frame }) });

export const simpanOrang = (body) =>
  kirim("/api/orang", { method: "POST", body: JSON.stringify(body) });

export const daftarOrang = () => kirim("/api/orang");

export const ambilOrang = (id) => kirim(`/api/orang/${id}`);

export const hapusOrang = (id) => kirim(`/api/orang/${id}`, { method: "DELETE" });

export const hapusSemua = () => kirim("/api/orang", { method: "DELETE" });
