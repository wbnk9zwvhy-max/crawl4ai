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
  productHistory: (productId) => request(`/api/products/${productId}/history`),
  similarProducts: (productId) => request(`/api/products/${productId}/similar`),
  shoppingList: (userEmail) =>
    request(`/api/shopping-list?user_email=${encodeURIComponent(userEmail)}`),
  addShoppingListItem: (userEmail, categorySlug) =>
    request("/api/shopping-list", {
      method: "POST",
      body: JSON.stringify({ user_email: userEmail, category_slug: categorySlug }),
    }),
  removeShoppingListItem: (id, userEmail) =>
    request(`/api/shopping-list/${id}?user_email=${encodeURIComponent(userEmail)}`, {
      method: "DELETE",
    }),
  analyzeReceipt: async (file) => {
    const form = new FormData();
    form.append("file", file);
    // Sin cabecera Content-Type manual: el navegador la fija con el
    // boundary correcto del multipart al usar FormData.
    const res = await fetch(`${API_URL}/api/receipts/analyze`, { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail || `${res.status} ${res.statusText}`);
    }
    return res.json();
  },
  confirmReceipt: (payload) =>
    request("/api/receipts/confirm", { method: "POST", body: JSON.stringify(payload) }),
  favorites: (userEmail) => request(`/api/favorites?user_email=${encodeURIComponent(userEmail)}`),
  addFavorite: (userEmail, categorySlug) =>
    request("/api/favorites", {
      method: "POST",
      body: JSON.stringify({ user_email: userEmail, category_slug: categorySlug }),
    }),
  removeFavorite: (userEmail, categorySlug) =>
    request(`/api/favorites/${categorySlug}?user_email=${encodeURIComponent(userEmail)}`, {
      method: "DELETE",
    }),
  priceAlerts: (userEmail) =>
    request(`/api/price-alerts?user_email=${encodeURIComponent(userEmail)}`),
  watchProduct: (userEmail, productId) =>
    request("/api/price-alerts", {
      method: "POST",
      body: JSON.stringify({ user_email: userEmail, product_id: productId }),
    }),
  unwatchProduct: (userEmail, productId) =>
    request(`/api/price-alerts/${productId}?user_email=${encodeURIComponent(userEmail)}`, {
      method: "DELETE",
    }),
  spending: (userEmail) => request(`/api/spending?user_email=${encodeURIComponent(userEmail)}`),
  reorderSuggestions: (userEmail) =>
    request(`/api/reorder-suggestions?user_email=${encodeURIComponent(userEmail)}`),
  vapidPublicKey: () => request("/api/push/vapid-public-key"),
  subscribePush: (payload) =>
    request("/api/push/subscribe", { method: "POST", body: JSON.stringify(payload) }),
  unsubscribePush: (userEmail, endpoint) =>
    request("/api/push/subscribe", {
      method: "DELETE",
      body: JSON.stringify({ user_email: userEmail, endpoint }),
    }),
  testPush: (userEmail) =>
    request(`/api/push/test?user_email=${encodeURIComponent(userEmail)}`, { method: "POST" }),
};
