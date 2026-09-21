// En dev, Vite hace proxy de /api hacia el backend (ver vite.config.js), así
// que dejamos la base vacía y usamos rutas relativas. En producción, define
// VITE_API_URL si el backend vive en otro dominio.
const API_URL = import.meta.env.VITE_API_URL || "";

// Las imágenes de producto vienen de la API como rutas relativas
// (/media/products/...) servidas por el propio backend. En dev el proxy de
// Vite las resuelve igual que /api; en producción hay que anteponerles el
// origen real del backend.
export function mediaUrl(path) {
  if (!path) return path;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_URL}${path}`;
}

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  supermarkets: () => request("/api/supermarkets"),
  categories: () => request("/api/categories"),
  offersToday: ({ period = "today", supermarket } = {}) => {
    const params = new URLSearchParams({ period });
    if (supermarket) params.set("supermarket", supermarket);
    return request(`/api/offers/today?${params.toString()}`);
  },
  compareCategory: (slug) => request(`/api/compare/${slug}`),
  listPurchases: (userEmail) =>
    request(`/api/purchases?user_email=${encodeURIComponent(userEmail)}`),
  createPurchase: (payload) =>
    request("/api/purchases", { method: "POST", body: JSON.stringify(payload) }),
  deletePurchase: (id, userEmail) =>
    request(`/api/purchases/${id}?user_email=${encodeURIComponent(userEmail)}`, {
      method: "DELETE",
    }),
  insights: (userEmail) =>
    request(`/api/insights?user_email=${encodeURIComponent(userEmail)}`),
  scrapeNow: () => request("/api/admin/scrape-now", { method: "POST" }),
};
