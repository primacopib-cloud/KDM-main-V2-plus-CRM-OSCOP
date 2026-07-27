// LOLODRIVE by O'SCOP — moteur transactionnel V2
import { apiCall } from './http';

export const lolodriveAPI = {
  // PASS & wallet
  myPass: () => apiCall('/lolodrive/pass/me'),
  myWallet: () => apiCall('/lolodrive/wallet/me'),

  // Catalogue
  catalogTeaser: () => apiCall('/lolodrive/catalog/teaser'),
  catalogProducts: (catalogType, territory, pointCode) => {
    const q = new URLSearchParams();
    if (catalogType) q.append('catalog_type', catalogType);
    if (territory) q.append('territory', territory);
    if (pointCode) q.append('point_code', pointCode);
    return apiCall(`/lolodrive/catalog/products${q.toString() ? `?${q.toString()}` : ''}`);
  },
  quote: (items) =>
    apiCall('/lolodrive/catalog/quote', { method: 'POST', body: JSON.stringify({ items }) }),

  // Orders
  createOrder: (payload) =>
    apiCall('/lolodrive/orders', { method: 'POST', body: JSON.stringify(payload) }),
  myOrders: () => apiCall('/lolodrive/orders/me'),
  payOrderUC: (orderId) =>
    apiCall(`/lolodrive/orders/${orderId}/pay-uc`, { method: 'POST' }),

  // Stripe payments
  passIntent: () =>
    apiCall('/lolodrive/payments/pass-intent', { method: 'POST' }),
  rechargeIntent: (pack) =>
    apiCall('/lolodrive/payments/recharge-intent', {
      method: 'POST',
      body: JSON.stringify({ pack }),
    }),
  orderIntent: (orderId) =>
    apiCall('/lolodrive/payments/order-intent', {
      method: 'POST',
      body: JSON.stringify({ order_id: orderId }),
    }),

  // Logistics
  logisticsConfig: () => apiCall('/lolodrive/logistics/config'),
  zones: () => apiCall('/lolodrive/logistics/zones'),

  // POS
  posOrders: (status, loloPointCode) => {
    const q = new URLSearchParams();
    if (status) q.append('status', status);
    if (loloPointCode) q.append('lolo_point_code', loloPointCode);
    return apiCall(`/lolodrive/pos/orders${q.toString() ? `?${q.toString()}` : ''}`);
  },
  posUpdateStatus: (orderId, status) =>
    apiCall(`/lolodrive/pos/orders/${orderId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),
  posScan: (orderId) =>
    apiCall(`/lolodrive/pos/orders/${orderId}/scan`, { method: 'POST' }),
  posRemindPickup: (orderId) =>
    apiCall(`/lolodrive/pos/orders/${orderId}/remind`, { method: 'POST' }),
  favoritesGet: () => apiCall('/lolodrive/favorites'),
  favoritesSave: (skus) =>
    apiCall('/lolodrive/favorites', { method: 'POST', body: JSON.stringify({ skus }) }),
  managerProStatus: () => apiCall('/lolodrive/manager/pro-status'),
  posCatalog: (pointCode) =>
    apiCall(`/lolodrive/pos/catalog${pointCode ? `?point_code=${pointCode}` : ''}`),
  managerProducts: () => apiCall('/lolodrive/manager/products'),
  managerSubmitProduct: (payload) =>
    apiCall('/lolodrive/manager/products', { method: 'POST', body: JSON.stringify(payload) }),
  managerUpdateProduct: (sku, payload) =>
    apiCall(`/lolodrive/manager/products/${sku}`, { method: 'PUT', body: JSON.stringify(payload) }),
  posCounterSale: (items, paymentMethod) =>
    apiCall('/lolodrive/pos/counter-sale', { method: 'POST', body: JSON.stringify({ items, payment_method: paymentMethod }) }),
  posCounterJournal: () => apiCall('/lolodrive/pos/counter-journal'),
  posTopProducts: (days = 30) => apiCall(`/lolodrive/pos/top-products?days=${days}`),
  posMonthlyCompare: () => apiCall('/lolodrive/pos/monthly-compare'),
  posStockAlerts: (days = 30) => apiCall(`/lolodrive/pos/stock-alerts?days=${days}`),
  posSetStock: (sku, stockQty) =>
    apiCall(`/lolodrive/pos/products/${sku}/stock`, { method: 'PATCH', body: JSON.stringify({ stock_qty: stockQty }) }),
  posStockHistory: (sku, limit = 50) =>
    apiCall(`/lolodrive/pos/stock-history?sku=${encodeURIComponent(sku)}&limit=${limit}`),
  adminCounterRanking: (month) =>
    apiCall(`/lolodrive/admin/counter-ranking${month ? `?month=${month}` : ''}`),
  posEmailTicket: (orderId, email) =>
    apiCall(`/lolodrive/pos/counter-sale/${orderId}/email-ticket`, { method: 'POST', body: JSON.stringify({ email }) }),
  adminRelayProducts: (status = 'PENDING') =>
    apiCall(`/lolodrive/admin/relay-products?status=${status}`),
  adminReviewRelayProduct: (sku, action, reason) =>
    apiCall(`/lolodrive/admin/relay-products/${sku}/review`, { method: 'POST', body: JSON.stringify({ action, reason }) }),
  adminPointsProStatus: () => apiCall('/lolodrive/admin/lolo-points/pro-status'),

  // LOLO POINTS
  listLoloPoints: (cityOrOpts, territory) => {
    // Backward compatible: support listLoloPoints(city) AND listLoloPoints({city, territory})
    let city = cityOrOpts;
    let terr = territory;
    if (cityOrOpts && typeof cityOrOpts === 'object') {
      city = cityOrOpts.city;
      terr = cityOrOpts.territory;
    }
    const q = new URLSearchParams();
    if (city) q.append('city', city);
    if (terr) q.append('territory', terr);
    return apiCall(`/lolodrive/lolo-points${q.toString() ? `?${q.toString()}` : ''}`);
  },
  listTerritories: () => apiCall('/lolodrive/territories'),
  createLoloPoint: (payload) =>
    apiCall('/lolodrive/admin/lolo-points', { method: 'POST', body: JSON.stringify(payload) }),
  addContribution: (pointId, payload) =>
    apiCall(`/lolodrive/admin/lolo-points/${pointId}/contributions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  payoutPreview: (pointId, fromDate, toDate) =>
    apiCall(`/lolodrive/admin/lolo-points/${pointId}/payout-preview`, {
      method: 'POST',
      body: JSON.stringify({ from_date: fromDate, to_date: toDate }),
    }),

  // Events / partners
  activeEvents: () => apiCall('/lolodrive/events/active'),
  listEvents: (scope = 'all') => apiCall(`/lolodrive/events?scope=${scope}`),
  eventDetail: (eventId) => apiCall(`/lolodrive/events/${eventId}`),
  reserveEvent: (eventId) =>
    apiCall(`/lolodrive/events/${eventId}/reserve`, { method: 'POST' }),
  cancelReservation: (eventId) =>
    apiCall(`/lolodrive/events/${eventId}/reserve`, { method: 'DELETE' }),
  listEventReservations: (eventId) =>
    apiCall(`/lolodrive/admin/events/${eventId}/reservations`),
  linkProductsToEvent: (eventId, linkedProducts) =>
    apiCall(`/lolodrive/admin/events/${eventId}/products`, {
      method: 'POST',
      body: JSON.stringify({ linked_products: linkedProducts }),
    }),
  createEvent: (payload) =>
    apiCall('/lolodrive/admin/events', { method: 'POST', body: JSON.stringify(payload) }),
  createPartner: (payload) =>
    apiCall('/lolodrive/admin/partners', { method: 'POST', body: JSON.stringify(payload) }),

  // Manager LOLO POINT (gérant connecté)
  managerMyPoint: () => apiCall('/lolodrive/manager/my-point'),
  managerMyOrders: (orderStatus) => apiCall(`/lolodrive/manager/my-orders${orderStatus ? `?order_status=${orderStatus}` : ''}`),
  managerPayoutPreview: () => apiCall('/lolodrive/manager/my-payout-preview'),
  managerTimeseries: (days = 30) => apiCall(`/lolodrive/manager/my-timeseries?days=${days}`),
  managerNetworkRanking: (days = 30) => apiCall(`/lolodrive/manager/network-ranking?days=${days}`),

  // Brevo metrics (délivrabilité)
  brevoMetricsSummary: (days = 30) => apiCall(`/brevo/metrics/summary?days=${days}`),

  // PASS lifecycle (auto-renew + parrainage)
  setPassAutoRenew: (enabled) =>
    apiCall('/lolodrive/pass/auto-renew', { method: 'POST', body: JSON.stringify({ enabled }) }),
  getMyReferralCode: () => apiCall('/lolodrive/pass/referral/me'),
  claimReferralCode: (code) =>
    apiCall('/lolodrive/pass/referral/claim', { method: 'POST', body: JSON.stringify({ code }) }),
  getReferralStats: () => apiCall('/lolodrive/pass/referral/stats'),

  // Reporting timeseries
  kpiTimeseries: (metric = 'revenue', days = 30) =>
    apiCall(`/lolodrive/admin/kpi/timeseries?metric=${metric}&days=${days}`),

  // Admin
  initDefaults: () => apiCall('/lolodrive/admin/init-defaults', { method: 'POST' }),
  createProduct: (payload) =>
    apiCall('/lolodrive/admin/products', { method: 'POST', body: JSON.stringify(payload) }),
  kpiOverview: (fromDate, toDate) => {
    const q = new URLSearchParams();
    if (fromDate) q.append('from_date', fromDate);
    if (toDate) q.append('to_date', toDate);
    return apiCall(`/lolodrive/admin/kpi/overview${q.toString() ? `?${q.toString()}` : ''}`);
  },

  // Relay reviews (avis relais)
  relayReviewsPending: () => apiCall('/lolodrive/relay-reviews/pending'),
  submitRelayReview: (payload) =>
    apiCall('/lolodrive/relay-reviews', { method: 'POST', body: JSON.stringify(payload) }),
  relayReviewStats: () => apiCall('/lolodrive/relay-reviews/stats'),
  relayReviewsList: (pointCode) => apiCall(`/lolodrive/relay-reviews/list/${pointCode}`),
  relayReviewsLatest: (limit = 6) => apiCall(`/lolodrive/relay-reviews/latest?limit=${limit}`),
  relayPodium: () => apiCall('/lolodrive/relay-reviews/podium'),
  managerMyReviews: () => apiCall('/lolodrive/manager/my-reviews'),
  replyRelayReview: (reviewId, reply) =>
    apiCall(`/lolodrive/manager/my-reviews/${reviewId}/reply`, { method: 'POST', body: JSON.stringify({ reply }) }),

  // Demo simulators (no Stripe webhook required)
  simulateOrderPayment: (orderId) =>
    apiCall(`/lolodrive/demo/simulate-order-payment/${orderId}`, { method: 'POST' }),
  mySavings: () => apiCall('/lolodrive/me/savings'),

  // POS extras
  posCancelOrder: (orderId, reason, refundUc = false) =>
    apiCall(`/lolodrive/pos/orders/${orderId}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason, refund_uc: refundUc }),
    }),

  // Extended dashboard KPI (UC en circulation, top produits, alertes, CA jour/mois)
  kpiDashboard: () => apiCall('/lolodrive/admin/kpi/dashboard'),

  // Stripe Checkout (hosted)
  checkoutPass: (originUrl) =>
    apiCall('/lolodrive/checkout/pass-session', {
      method: 'POST',
      body: JSON.stringify({ origin_url: originUrl }),
    }),
  checkoutRecharge: (originUrl, pack) =>
    apiCall('/lolodrive/checkout/recharge-session', {
      method: 'POST',
      body: JSON.stringify({ origin_url: originUrl, pack }),
    }),
  checkoutOrder: (originUrl, orderId) =>
    apiCall('/lolodrive/checkout/order-session', {
      method: 'POST',
      body: JSON.stringify({ origin_url: originUrl, order_id: orderId }),
    }),
  checkoutStatus: (sessionId) =>
    apiCall(`/lolodrive/checkout/status/${sessionId}`),
};
