// API Service for B2B ESS Platform

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Helper function to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Helper function for API calls
const apiCall = async (endpoint, options = {}) => {
  const response = await fetch(`${API}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Une erreur est survenue');
  }

  return data;
};

// Auth APIs
export const authAPI = {
  register: async (userData) => {
    return apiCall('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email: userData.email,
        password: userData.password,
        company_name: userData.companyName,
        siret: userData.siret,
        contact_name: userData.contactName,
        phone: userData.phone,
        plan: userData.plan || 'ess-acces-pro',
      }),
    });
  },

  login: async (email, password) => {
    const data = await apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    
    // Store token and user
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    
    return data;
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },

  getMe: async () => {
    return apiCall('/auth/me');
  },

  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  isAuthenticated: () => {
    return !!localStorage.getItem('token');
  },
};

// Quote Request APIs
export const quoteAPI = {
  create: async (quoteData) => {
    return apiCall('/quotes', {
      method: 'POST',
      body: JSON.stringify({
        company: quoteData.company,
        contact_name: quoteData.contactName,
        email: quoteData.email,
        phone: quoteData.phone,
        plan: quoteData.plan,
        message: quoteData.message,
      }),
    });
  },

  getAll: async () => {
    return apiCall('/quotes');
  },
};

// Subscription APIs
export const subscriptionAPI = {
  getPlans: async () => {
    return apiCall('/subscriptions');
  },

  updatePlan: async (plan) => {
    return apiCall('/users/subscription', {
      method: 'PUT',
      body: JSON.stringify({ plan }),
    });
  },
};

// Credits APIs
export const creditsAPI = {
  get: async () => {
    return apiCall('/credits');
  },

  add: async (amount) => {
    return apiCall('/credits/add', {
      method: 'POST',
      body: JSON.stringify({ amount }),
    });
  },
};

// Password Reset APIs
export const passwordAPI = {
  forgotPassword: async (email) => {
    return apiCall('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  resetPassword: async (token, newPassword) => {
    return apiCall('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  },
};

// User Statistics APIs
export const statsAPI = {
  getUserStats: async () => {
    return apiCall('/users/stats');
  },

  getOrders: async (skip = 0, limit = 20) => {
    return apiCall(`/users/orders?skip=${skip}&limit=${limit}`);
  },
};

// Admin APIs
export const adminAPI = {
  getStats: async () => {
    return apiCall('/admin/stats');
  },

  getUsers: async (page = 1, perPage = 20, search = '') => {
    const params = new URLSearchParams({ page, per_page: perPage });
    if (search) params.append('search', search);
    return apiCall(`/admin/users?${params}`);
  },

  getQuotes: async (statusFilter = null, skip = 0, limit = 50) => {
    const params = new URLSearchParams({ skip, limit });
    if (statusFilter) params.append('status_filter', statusFilter);
    return apiCall(`/admin/quotes?${params}`);
  },

  updateQuoteStatus: async (quoteId, newStatus) => {
    return apiCall(`/admin/quotes/${quoteId}/status?new_status=${newStatus}`, {
      method: 'PUT',
    });
  },

  updateUserCredits: async (userId, amount) => {
    return apiCall(`/admin/users/${userId}/credits?amount=${amount}`, {
      method: 'PUT',
    });
  },

  getOrganizations: async (statusFilter = null, skip = 0, limit = 50) => {
    const params = new URLSearchParams({ skip, limit });
    if (statusFilter) params.append('status_filter', statusFilter);
    return apiCall(`/admin/organizations?${params}`);
  },
};

// Notifications APIs (Phase 1)
export const notificationsAPI = {
  getAll: async (limit = 20, unreadOnly = false) => {
    const params = new URLSearchParams({ limit });
    if (unreadOnly) params.append('unread_only', 'true');
    return apiCall(`/notifications?${params}`);
  },

  poll: async (since = null) => {
    const params = new URLSearchParams();
    if (since) params.append('since', since);
    return apiCall(`/notifications/poll?${params}`);
  },

  markAsRead: async (notificationId) => {
    return apiCall(`/notifications/${notificationId}/read`, { method: 'POST' });
  },

  markAllAsRead: async () => {
    return apiCall('/notifications/read-all', { method: 'POST' });
  },
};

// Zones APIs (Phase 2)
export const zonesAPI = {
  getAll: async () => {
    return apiCall('/zones');
  },

  create: async (zone) => {
    return apiCall('/zones', {
      method: 'POST',
      body: JSON.stringify(zone),
    });
  },
};

// Organizations APIs (Phase 2)
export const organizationsAPI = {
  create: async (orgData) => {
    return apiCall('/organizations', {
      method: 'POST',
      body: JSON.stringify(orgData),
    });
  },

  get: async (orgId) => {
    return apiCall(`/organizations/${orgId}`);
  },

  submit: async (orgId) => {
    return apiCall(`/organizations/${orgId}/submit`, { method: 'POST' });
  },

  decide: async (orgId, decision, reasonCode = null, comment = null) => {
    return apiCall(`/organizations/${orgId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, reason_code: reasonCode, comment }),
    });
  },

  suspend: async (orgId, reason) => {
    return apiCall(`/organizations/${orgId}/suspend?reason=${reason}`, { method: 'POST' });
  },

  getZones: async (orgId) => {
    return apiCall(`/organizations/${orgId}/zones`);
  },

  addZone: async (orgId, zoneId) => {
    return apiCall(`/organizations/${orgId}/zones?zone_id=${zoneId}`, { method: 'POST' });
  },

  selectZone: async (orgId, zoneCode) => {
    return apiCall(`/organizations/${orgId}/select-zone?zone_code=${zoneCode}`, { method: 'POST' });
  },
};

// PDF Download
export const downloadOffer = () => {
  window.open(`${API}/download-offer`, '_blank');
};

// ============== V2 APIs (B2B Workflow) ==============

const API_V2 = `${BACKEND_URL}/api/v2`;

// Helper function for V2 API calls
const apiCallV2 = async (endpoint, options = {}) => {
  const response = await fetch(`${API_V2}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Une erreur est survenue');
  }

  return data;
};

// V2 Organizations APIs
export const orgsAPIV2 = {
  create: async (orgData) => {
    return apiCallV2('/orgs', {
      method: 'POST',
      body: JSON.stringify({
        legal_name: orgData.legalName,
        registration_country: orgData.registrationCountry || 'FR',
        registration_id: orgData.registrationId,
        territory: orgData.territory,
        contact_email: orgData.contactEmail,
        contact_name: orgData.contactName,
        contact_phone: orgData.contactPhone,
        address: orgData.address || null,
      }),
    });
  },

  get: async (orgId) => {
    return apiCallV2(`/orgs/${orgId}`);
  },

  list: async () => {
    return apiCallV2('/orgs');
  },
};

// V2 Applications APIs
export const applicationsAPIV2 = {
  create: async (orgId) => {
    return apiCallV2(`/orgs/${orgId}/applications`, {
      method: 'POST',
    });
  },

  uploadDocument: async (appId, docType, fileUrl, checksum = null) => {
    return apiCallV2(`/applications/${appId}/documents`, {
      method: 'POST',
      body: JSON.stringify({
        doc_type: docType,
        file_url: fileUrl,
        checksum_sha256: checksum,
      }),
    });
  },

  submit: async (appId) => {
    return apiCallV2(`/applications/${appId}/submit`, {
      method: 'POST',
    });
  },

  decide: async (appId, decision, reasonCode = null, comment = null) => {
    return apiCallV2(`/applications/${appId}/decision`, {
      method: 'POST',
      body: JSON.stringify({
        decision,
        reason_code: reasonCode,
        comment,
      }),
    });
  },

  listAdmin: async (statusFilter = null, limit = 50) => {
    const params = new URLSearchParams({ limit });
    if (statusFilter) params.append('status_filter', statusFilter);
    return apiCallV2(`/admin/applications?${params}`);
  },
};

// V2 Plans & Subscriptions APIs
export const plansAPIV2 = {
  list: async () => {
    return apiCallV2('/plans');
  },
};

export const subscriptionsAPIV2 = {
  create: async (orgId, planId) => {
    return apiCallV2(`/orgs/${orgId}/subscriptions`, {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId }),
    });
  },

  list: async (orgId) => {
    return apiCallV2(`/orgs/${orgId}/subscriptions`);
  },
};

// V2 Wallet APIs
export const walletAPIV2 = {
  get: async (orgId) => {
    return apiCallV2(`/orgs/${orgId}/wallet`);
  },

  topup: async (orgId, amount) => {
    return apiCallV2(`/orgs/${orgId}/wallet/topup?amount=${amount}`, {
      method: 'POST',
    });
  },

  getLedger: async (orgId, limit = 50) => {
    return apiCallV2(`/orgs/${orgId}/wallet/ledger?limit=${limit}`);
  },
};

// V2 Zones APIs
export const zonesAPIV2 = {
  list: async () => {
    return apiCallV2('/zones');
  },

  getOrgEntitlements: async (orgId) => {
    return apiCallV2(`/orgs/${orgId}/zones`);
  },

  addEntitlement: async (orgId, zoneId) => {
    return apiCallV2(`/orgs/${orgId}/zones/${zoneId}`, {
      method: 'POST',
    });
  },

  selectZone: async (orgId, zoneId) => {
    return apiCallV2(`/orgs/${orgId}/select-zone?zone_id=${zoneId}`, {
      method: 'POST',
    });
  },
};

// V2 Catalog APIs
export const catalogAPI = {
  getCategories: async () => {
    return apiCallV2('/catalog/categories');
  },

  getProducts: async (params = {}) => {
    const searchParams = new URLSearchParams();
    if (params.categoryId) searchParams.append('category_id', params.categoryId);
    if (params.zoneCode) searchParams.append('zone_code', params.zoneCode);
    if (params.search) searchParams.append('search', params.search);
    if (params.tags) searchParams.append('tags', params.tags);
    if (params.skip) searchParams.append('skip', params.skip);
    if (params.limit) searchParams.append('limit', params.limit);
    return apiCallV2(`/catalog/products?${searchParams}`);
  },

  getProduct: async (productId, zoneCode = null) => {
    const params = zoneCode ? `?zone_code=${zoneCode}` : '';
    return apiCallV2(`/catalog/products/${productId}${params}`);
  },

  getPickupLocations: async (zoneCode = null) => {
    const params = zoneCode ? `?zone_code=${zoneCode}` : '';
    return apiCallV2(`/catalog/pickup-locations${params}`);
  },

  getCart: async () => {
    return apiCallV2('/catalog/cart');
  },

  addToCart: async (productId, quantity) => {
    return apiCallV2('/catalog/cart/items', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId, quantity }),
    });
  },

  removeFromCart: async (itemId) => {
    return apiCallV2(`/catalog/cart/items/${itemId}`, {
      method: 'DELETE',
    });
  },

  clearCart: async () => {
    return apiCallV2('/catalog/cart', {
      method: 'DELETE',
    });
  },
};

// V2 Orders APIs
export const ordersAPIV2 = {
  create: async (cartId, pickupLocationId, notes = null, useInstallment = false) => {
    return apiCallV2('/orders', {
      method: 'POST',
      body: JSON.stringify({
        cart_id: cartId,
        pickup_location_id: pickupLocationId,
        notes,
        use_installment: useInstallment,
      }),
    });
  },

  list: async (statusFilter = null, skip = 0, limit = 20) => {
    const params = new URLSearchParams({ skip, limit });
    if (statusFilter) params.append('status_filter', statusFilter);
    return apiCallV2(`/orders?${params}`);
  },

  get: async (orderId) => {
    return apiCallV2(`/orders/${orderId}`);
  },

  cancel: async (orderId, reason = 'Client request') => {
    return apiCallV2(`/orders/${orderId}/cancel?reason=${encodeURIComponent(reason)}`, {
      method: 'POST',
    });
  },
};

// Installment calculation API
export const installmentAPI = {
  calculate: async (amountHtCents) => {
    return apiCallV2(`/catalog/installment/calculate?amount_ht_cents=${amountHtCents}`);
  },
};

// Invoices API
export const invoicesAPI = {
  list: async (status = null, paymentStatus = null, skip = 0, limit = 20) => {
    const params = new URLSearchParams({ skip, limit });
    if (status) params.append('status', status);
    if (paymentStatus) params.append('payment_status', paymentStatus);
    return apiCallV2(`/invoices?${params}`);
  },

  get: async (invoiceId) => {
    return apiCallV2(`/invoices/${invoiceId}`);
  },

  getByOrder: async (orderId) => {
    return apiCallV2(`/invoices/by-order/${orderId}`);
  },

  getStats: async () => {
    return apiCallV2('/invoices/stats');
  },

  generate: async (orderId) => {
    return apiCallV2(`/invoices/generate/${orderId}`, { method: 'POST' });
  },

  markPaid: async (invoiceId, paymentMethod = 'CARD') => {
    return apiCallV2(`/invoices/${invoiceId}/mark-paid?payment_method=${paymentMethod}`, { method: 'POST' });
  },
};

// V2 Admin APIs
export const adminAPIV2 = {
  listOrgs: async (statusFilter = null, limit = 100) => {
    const params = new URLSearchParams({ limit });
    if (statusFilter) params.append('status_filter', statusFilter);
    return apiCallV2(`/admin/orgs?${params}`);
  },

  suspendOrg: async (orgId, reason = 'compliance') => {
    return apiCallV2(`/admin/orgs/${orgId}/suspend?reason=${encodeURIComponent(reason)}`, {
      method: 'POST',
    });
  },

  getAuditLog: async (orgId = null, action = null, limit = 100) => {
    const params = new URLSearchParams({ limit });
    if (orgId) params.append('org_id', orgId);
    if (action) params.append('action', action);
    return apiCallV2(`/admin/audit-log?${params}`);
  },
};

// Legal Documents APIs
export const documentsAPI = {
  list: async () => {
    return apiCall('/documents');
  },

  get: async (docId) => {
    return apiCall(`/documents/${docId}`);
  },
};

// Export APIs (Admin only)
export const exportAPI = {
  getSummary: async () => {
    return apiCall('/admin/export/summary');
  },

  download: (type, params = {}) => {
    const searchParams = new URLSearchParams();
    if (params.statusFilter) searchParams.append('status_filter', params.statusFilter);
    if (params.dateFrom) searchParams.append('date_from', params.dateFrom);
    if (params.dateTo) searchParams.append('date_to', params.dateTo);
    if (params.orgId) searchParams.append('org_id', params.orgId);
    
    const token = localStorage.getItem('token');
    const url = `${API}/admin/export/${type}?${searchParams}`;
    
    // Create a temporary link to download with auth
    return fetch(url, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(res => {
      if (!res.ok) throw new Error('Export failed');
      return res.blob();
    }).then(blob => {
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${type}_export.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    });
  },
};

// Payment APIs (Stripe + Bank Transfer + SEPA)
export const paymentAPI = {
  getPackages: async () => {
    return apiCall('/payments/packages');
  },

  // Card payment via Stripe Checkout
  createCheckout: async (packageId) => {
    const originUrl = window.location.origin;
    return apiCall('/payments/checkout', {
      method: 'POST',
      body: JSON.stringify({
        package_id: packageId,
        origin_url: originUrl,
      }),
    });
  },

  getStatus: async (sessionId) => {
    return apiCall(`/payments/status/${sessionId}`);
  },

  getHistory: async (limit = 20) => {
    return apiCall(`/payments/history?limit=${limit}`);
  },

  // Bank Transfer
  getBankDetails: async () => {
    return apiCall('/payments/bank-details');
  },

  createBankTransfer: async (packageId, companyName) => {
    return apiCall('/payments/bank-transfer', {
      method: 'POST',
      body: JSON.stringify({
        package_id: packageId,
        company_name: companyName,
      }),
    });
  },

  getBankTransferStatus: async (transferId) => {
    return apiCall(`/payments/bank-transfer/${transferId}/status`);
  },

  // SEPA Direct Debit
  createSepaSetup: async (packageId, iban, accountHolderName, email) => {
    return apiCall('/payments/sepa/setup', {
      method: 'POST',
      body: JSON.stringify({
        package_id: packageId,
        iban: iban,
        account_holder_name: accountHolderName,
        email: email,
      }),
    });
  },

  confirmSepaPayment: async (setupId) => {
    return apiCall(`/payments/sepa/confirm/${setupId}`, {
      method: 'POST',
    });
  },
};

export default {
  auth: authAPI,
  quote: quoteAPI,
  subscription: subscriptionAPI,
  credits: creditsAPI,
  password: passwordAPI,
  stats: statsAPI,
  admin: adminAPI,
  notifications: notificationsAPI,
  zones: zonesAPI,
  organizations: organizationsAPI,
  downloadOffer,
  // V2 APIs
  orgsV2: orgsAPIV2,
  applicationsV2: applicationsAPIV2,
  plansV2: plansAPIV2,
  subscriptionsV2: subscriptionsAPIV2,
  walletV2: walletAPIV2,
  zonesV2: zonesAPIV2,
  catalog: catalogAPI,
  ordersV2: ordersAPIV2,
  installment: installmentAPI,
  adminV2: adminAPIV2,
  documents: documentsAPI,
  export: exportAPI,
  payment: paymentAPI,
};


// ============== ADMIN PLANS & CREDITS API ==============
export const adminPlansAPI = {
  // Subscription Plans
  listPlans: (includeInactive = true) =>
    apiCall(`/admin/plans/subscriptions?include_inactive=${includeInactive}`),
  getPlan: (planId) => apiCall(`/admin/plans/subscriptions/${planId}`),
  createPlan: (data) =>
    apiCall('/admin/plans/subscriptions', { method: 'POST', body: JSON.stringify(data) }),
  updatePlan: (planId, data) =>
    apiCall(`/admin/plans/subscriptions/${planId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deletePlan: (planId, force = false) =>
    apiCall(`/admin/plans/subscriptions/${planId}?force=${force}`, { method: 'DELETE' }),

  // Plan Options
  listOptions: (includeInactive = true) =>
    apiCall(`/admin/plans/options?include_inactive=${includeInactive}`),
  createOption: (data) =>
    apiCall('/admin/plans/options', { method: 'POST', body: JSON.stringify(data) }),
  updateOption: (optionId, data) =>
    apiCall(`/admin/plans/options/${optionId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteOption: (optionId) =>
    apiCall(`/admin/plans/options/${optionId}`, { method: 'DELETE' }),

  // Credits
  listUsersWithCredits: (search = '', page = 1, pageSize = 20) => {
    const q = new URLSearchParams({ page, page_size: pageSize });
    if (search) q.append('search', search);
    return apiCall(`/admin/plans/credits/users?${q.toString()}`);
  },
  getUserCredits: (userId) => apiCall(`/admin/plans/credits/users/${userId}`),
  adjustUserCredits: (userId, data) =>
    apiCall(`/admin/plans/credits/users/${userId}/adjust`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Stats
  getStats: () => apiCall('/admin/plans/stats'),
};


// ============================================================
// LOLODRIVE by O'SCOP — moteur transactionnel V2
// ============================================================
export const lolodriveAPI = {
  // PASS & wallet
  myPass: () => apiCall('/lolodrive/pass/me'),
  myWallet: () => apiCall('/lolodrive/wallet/me'),

  // Catalogue
  catalogTeaser: () => apiCall('/lolodrive/catalog/teaser'),
  catalogProducts: (catalogType) =>
    apiCall(`/lolodrive/catalog/products${catalogType ? `?catalog_type=${catalogType}` : ''}`),
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

  // LOLO POINTS
  listLoloPoints: (city) =>
    apiCall(`/lolodrive/lolo-points${city ? `?city=${encodeURIComponent(city)}` : ''}`),
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
  createEvent: (payload) =>
    apiCall('/lolodrive/admin/events', { method: 'POST', body: JSON.stringify(payload) }),
  createPartner: (payload) =>
    apiCall('/lolodrive/admin/partners', { method: 'POST', body: JSON.stringify(payload) }),

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
};

// ============================================================
// CRM O'SCOP Bridge — couche relationnelle / impact
// ============================================================
export const crmAPI = {
  // Contacts
  createContact: (payload) =>
    apiCall('/crm/contacts', { method: 'POST', body: JSON.stringify(payload) }),
  listContacts: (q, typeActeur, limit = 100) => {
    const p = new URLSearchParams({ limit });
    if (q) p.append('q', q);
    if (typeActeur) p.append('type_acteur', typeActeur);
    return apiCall(`/crm/contacts?${p.toString()}`);
  },
  getContact: (id) => apiCall(`/crm/contacts/${id}`),

  // Organizations
  createOrg: (payload) =>
    apiCall('/crm/organizations', { method: 'POST', body: JSON.stringify(payload) }),
  listOrgs: (q, typeStructure, limit = 100) => {
    const p = new URLSearchParams({ limit });
    if (q) p.append('q', q);
    if (typeStructure) p.append('type_structure', typeStructure);
    return apiCall(`/crm/organizations?${p.toString()}`);
  },

  // Opportunities
  createOpp: (payload) =>
    apiCall('/crm/opportunities', { method: 'POST', body: JSON.stringify(payload) }),
  listOpps: (stage, typeBesoin, limit = 100) => {
    const p = new URLSearchParams({ limit });
    if (stage) p.append('stage', stage);
    if (typeBesoin) p.append('type_besoin', typeBesoin);
    return apiCall(`/crm/opportunities?${p.toString()}`);
  },

  // Dossiers
  createDossier: (payload) =>
    apiCall('/crm/dossiers', { method: 'POST', body: JSON.stringify(payload) }),
  listDossiers: (typeDossier, statut, limit = 100) => {
    const p = new URLSearchParams({ limit });
    if (typeDossier) p.append('type_dossier', typeDossier);
    if (statut) p.append('statut', statut);
    return apiCall(`/crm/dossiers?${p.toString()}`);
  },

  // Tasks
  createTask: (payload) =>
    apiCall('/crm/tasks', { method: 'POST', body: JSON.stringify(payload) }),
  listTasks: (status, dueOnly = false) => {
    const p = new URLSearchParams();
    if (status) p.append('status', status);
    if (dueOnly) p.append('due_only', 'true');
    return apiCall(`/crm/tasks${p.toString() ? `?${p.toString()}` : ''}`);
  },

  // Impact / sync
  impactSummary: () => apiCall('/crm/impact/summary'),
  rebuildFromLolodrive: () =>
    apiCall('/crm/sync/rebuild-from-lolodrive', { method: 'POST' }),
};
