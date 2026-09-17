import { apiCall } from './http';

export const detaillantAPI = {
  register: (payload) => apiCall('/detaillant/register', { method: 'POST', body: JSON.stringify(payload) }),
  profile: () => apiCall('/detaillant/profile'),
  updateProfile: (payload) => apiCall('/detaillant/profile', { method: 'PUT', body: JSON.stringify(payload) }),
  checkout: (originUrl) => apiCall('/detaillant/subscription/checkout', { method: 'POST', body: JSON.stringify({ origin_url: originUrl }) }),
  activate: (sessionId) => apiCall('/detaillant/subscription/activate', { method: 'POST', body: JSON.stringify({ session_id: sessionId }) }),
  creditsCheckout: (pack, originUrl) => apiCall('/detaillant/credits/checkout', { method: 'POST', body: JSON.stringify({ pack, origin_url: originUrl }) }),
  creditsActivate: (sessionId) => apiCall('/detaillant/credits/activate', { method: 'POST', body: JSON.stringify({ session_id: sessionId }) }),
  catalog: () => apiCall('/detaillant/catalog'),
  myOffers: () => apiCall('/detaillant/offers'),
  createOffer: (payload) => apiCall('/detaillant/offers', { method: 'POST', body: JSON.stringify(payload) }),
  adminOffers: (status) => apiCall(`/admin/detaillant/offers${status ? `?status=${status}` : ''}`),
  adminReview: (offerId, action, note) => apiCall(`/admin/detaillant/offers/${offerId}/review`, { method: 'POST', body: JSON.stringify({ action, note }) }),
};
