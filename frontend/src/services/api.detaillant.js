import { apiCall, API, getAuthHeaders } from './http';

export const detaillantAPI = {
  register: (payload) => apiCall('/detaillant/register', { method: 'POST', body: JSON.stringify(payload) }),
  profile: () => apiCall('/detaillant/profile'),
  updateProfile: (payload) => apiCall('/detaillant/profile', { method: 'PUT', body: JSON.stringify(payload) }),
  checkout: (originUrl) => apiCall('/detaillant/subscription/checkout', { method: 'POST', body: JSON.stringify({ origin_url: originUrl }) }),
  activate: (sessionId) => apiCall('/detaillant/subscription/activate', { method: 'POST', body: JSON.stringify({ session_id: sessionId }) }),
  creditsCheckout: (pack, originUrl) => apiCall('/detaillant/credits/checkout', { method: 'POST', body: JSON.stringify({ pack, origin_url: originUrl }) }),
  creditsActivate: (sessionId) => apiCall('/detaillant/credits/activate', { method: 'POST', body: JSON.stringify({ session_id: sessionId }) }),
  sales: () => apiCall('/detaillant/sales'),
  relist: (reference) => apiCall(`/detaillant/sales/${reference}/relist`, { method: 'POST' }),
  uploadPhoto: async (file) => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API}/detaillant/photos`, {
      method: 'POST', credentials: 'include', headers: getAuthHeaders(), body: fd,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Échec du téléversement');
    return data;
  },
  detaillantReviews: () => apiCall('/detaillant/reviews'),
  reviewReply: (reviewId, reply) => apiCall(`/detaillant/reviews/${reviewId}/reply`, { method: 'POST', body: JSON.stringify({ reply }) }),
  shopsPublic: () => apiCall('/detaillant/shops/public'),
  catalogPublic: () => apiCall('/detaillant/catalog/public'),
  catalog: () => apiCall('/detaillant/catalog'),
  myOffers: () => apiCall('/detaillant/offers'),
  createOffer: (payload) => apiCall('/detaillant/offers', { method: 'POST', body: JSON.stringify(payload) }),
  adminOffers: (status) => apiCall(`/admin/detaillant/offers${status ? `?status=${status}` : ''}`),
  adminReview: (offerId, action, note) => apiCall(`/admin/detaillant/offers/${offerId}/review`, { method: 'POST', body: JSON.stringify({ action, note }) }),
  adminStats: () => apiCall('/admin/detaillant/stats'),
  adminCatalog: () => apiCall('/admin/detaillant/catalog'),
  adminUpsertProduct: (payload) => apiCall('/admin/detaillant/catalog', { method: 'POST', body: JSON.stringify(payload) }),
  adminToggleProduct: (sku, params) => apiCall(`/admin/detaillant/catalog/${sku}?${new URLSearchParams(params)}`, { method: 'PATCH' }),
};
