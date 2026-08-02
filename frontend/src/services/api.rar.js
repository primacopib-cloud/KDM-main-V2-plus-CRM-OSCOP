// Règlement à Réception Pro — API client
import { apiCall, API, getAuthHeaders } from './http';

export const rarAPI = {
  paymentOptions: () => apiCall('/rar/payment-options'),
  myStatus: () => apiCall('/rar/my-status'),
  requestAccess: (message) => apiCall('/rar/request', { method: 'POST', body: JSON.stringify({ message }) }),
  activateViaPack: () => apiCall('/rar/activate-via-pack', { method: 'POST' }),
  checkoutContext: () => apiCall('/rar/checkout-context'),
  // Admin
  adminAccounts: () => apiCall('/rar/admin/accounts'),
  adminDecide: (payload) => apiCall('/rar/admin/decide', { method: 'POST', body: JSON.stringify(payload) }),
  adminUpdate: (payload) => apiCall('/rar/admin/update', { method: 'POST', body: JSON.stringify(payload) }),
  adminPaymentOptions: () => apiCall('/rar/admin/payment-options'),
  adminAddOption: (payload) => apiCall('/rar/admin/payment-options', { method: 'POST', body: JSON.stringify(payload) }),
  adminUpdateOption: (code, payload) => apiCall(`/rar/admin/payment-options/${code}`, { method: 'PUT', body: JSON.stringify(payload) }),
  adminDeleteOption: (code) => apiCall(`/rar/admin/payment-options/${code}`, { method: 'DELETE' }),
  adminProducts: () => apiCall('/rar/admin/products'),
  adminSetProduct: (productId, payload) => apiCall(`/rar/admin/products/${productId}`, { method: 'PUT', body: JSON.stringify(payload) }),
  // Livraison LOGI'SCOP (Lot E)
  myPendingDeliveries: () => apiCall('/rar/delivery/my-pending'),
  confirmDelivery: (orderId, payload) => apiCall(`/rar/delivery/${orderId}/confirm`, { method: 'POST', body: JSON.stringify(payload) }),
  deliveryProof: (orderId) => apiCall(`/rar/delivery/${orderId}/proof`),
  adminDeliveries: () => apiCall('/rar/delivery/admin/list'),
  adminStartDelivery: (orderId, carrierName) => apiCall(`/rar/delivery/${orderId}/start`, { method: 'POST', body: JSON.stringify({ carrier_name: carrierName }) }),
  adminMarkCollected: (orderId) => apiCall(`/admin/cod/orders/${orderId}/collected`, { method: 'POST', body: JSON.stringify({}) }),
  // Réserves & PDF
  adminReserves: () => apiCall('/rar/delivery/reserves/admin/list'),
  resolveReserve: (orderId, action, note) => apiCall(`/rar/delivery/reserves/${orderId}/resolve`, { method: 'POST', body: JSON.stringify({ action, note }) }),
  ceilingHistory: () => apiCall('/rar/delivery/ceiling-history'),
  carrierStats: () => apiCall('/rar/stats/admin/carrier-stats'),
  adminUnpaid: () => apiCall('/rar/stats/admin/unpaid'),
  reactivateAccount: (orgId) => apiCall('/rar/stats/admin/reactivate', { method: 'POST', body: JSON.stringify({ org_id: orgId }) }),
  downloadUnpaidCsv: async () => {
    const r = await fetch(`${API}/rar/stats/admin/unpaid/export`, { credentials: 'include', headers: getAuthHeaders() });
    if (!r.ok) throw new Error('Export indisponible');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url; a.download = 'impayes-rar.csv'; a.click();
    URL.revokeObjectURL(url);
  },
  setCarrierBlocked: (carrier, blocked, reason = '') => apiCall('/rar/stats/admin/blocked-carriers', { method: 'POST', body: JSON.stringify({ carrier, blocked, reason }) }),
  carrierBlockLog: () => apiCall('/rar/stats/admin/carrier-block-log'),
  downloadBlockLogCsv: async () => {
    const r = await fetch(`${API}/rar/stats/admin/carrier-block-log/export`, { credentials: 'include', headers: getAuthHeaders() });
    if (!r.ok) throw new Error('Export indisponible');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url; a.download = 'journal-ecartements-transporteurs.csv'; a.click();
    URL.revokeObjectURL(url);
  },
  carrierScores: () => apiCall('/rar/stats/carrier-scores'),
  alertHistory: () => apiCall('/rar/stats/alert-history'),
  getAlertThreshold: () => apiCall('/rar/stats/alert-threshold'),
  setAlertThreshold: (cents) => apiCall('/rar/stats/alert-threshold', { method: 'PUT', body: JSON.stringify({ threshold_cents: cents }) }),
  downloadCeilingStatement: async (month) => {
    const r = await fetch(`${API}/rar/stats/ceiling-statement-pdf?month=${month}`, { credentials: 'include', headers: getAuthHeaders() });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Relevé indisponible');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url; a.download = `releve-plafond-${month}.pdf`; a.click();
    URL.revokeObjectURL(url);
  },
  downloadAnnualStatement: async (year) => {
    const r = await fetch(`${API}/rar/stats/ceiling-statement-annual-pdf?year=${year}`, { credentials: 'include', headers: getAuthHeaders() });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Relevé annuel indisponible');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url; a.download = `releve-plafond-annuel-${year}.pdf`; a.click();
    URL.revokeObjectURL(url);
  },
  downloadLitigationZip: async (all = false) => {
    const r = await fetch(`${API}/rar/delivery/admin/litigation-export${all ? '?all=true' : ''}`, { credentials: 'include', headers: getAuthHeaders() });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Aucun litige à exporter');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url; a.download = all ? 'livraisons-rar.zip' : 'litiges-rar.zip'; a.click();
    URL.revokeObjectURL(url);
  },
  downloadProofPdf: async (orderId, orderNumber) => {
    const r = await fetch(`${API}/rar/delivery/${orderId}/proof-pdf`, { credentials: 'include', headers: getAuthHeaders() });
    if (!r.ok) throw new Error('Bon de livraison indisponible');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url; a.download = `bon-livraison-${orderNumber}.pdf`; a.click();
    URL.revokeObjectURL(url);
  },
};
