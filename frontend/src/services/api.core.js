// Core (V1) APIs: auth, quotes, subscriptions, credits, stats, admin, notifications,
// zones, organizations, documents, exports, payments, admin plans.
import { API, apiCall } from './http';

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
        account_type: userData.accountType || 'buyer',
      }),
    });
  },

  login: async (email, password) => {
    const data = await apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    // JWT is stored in an httpOnly cookie by the backend (not accessible to JS)
    localStorage.setItem('user', JSON.stringify(data.user));

    return data;
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' }).catch(() => {});
  },

  getMe: async () => {
    return apiCall('/auth/me');
  },

  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  isAuthenticated: () => {
    return !!localStorage.getItem('user');
  },

  // Emergent-managed Google OAuth
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  startEmergentLogin: () => {
    const redirectUrl = window.location.origin + '/auth/callback';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  },
  exchangeEmergentSession: async (sessionId) => {
    const res = await fetch(`${API}/auth/emergent/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ session_id: sessionId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erreur authentification');
    if (data.user) localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  },
};

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

export const statsAPI = {
  getUserStats: async () => {
    return apiCall('/users/stats');
  },

  getOrders: async (skip = 0, limit = 20) => {
    return apiCall(`/users/orders?skip=${skip}&limit=${limit}`);
  },
};

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

export const downloadOffer = () => {
  window.open(`${API}/download-offer`, '_blank');
};

export const documentsAPI = {
  list: async () => {
    return apiCall('/documents');
  },

  get: async (docId) => {
    return apiCall(`/documents/${docId}`);
  },
};

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

    const url = `${API}/admin/export/${type}?${searchParams}`;

    return fetch(url, {
      credentials: 'include'
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

// ============== ADMIN PLANS & CREDITS API ==============
export const adminPlansAPI = {
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

  listUsersWithCredits: (search = '', page = 1, pageSize = 20) => {
    const q = new URLSearchParams({ page, page_size: pageSize });
    if (search) q.append('search', search);
    return apiCall(`/admin/plans/credits/users?${q.toString()}`);
  },
  getUserCredits: (userId) => apiCall(`/admin/plans/credits/users/${userId}`),
  grantByProfile: (data) =>
    apiCall('/admin/plans/credits/grant-by-profile', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  adjustUserCredits: (userId, data) =>
    apiCall(`/admin/plans/credits/users/${userId}/adjust`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getStats: () => apiCall('/admin/plans/stats'),

  listWalletPacks: () => apiCall('/admin/wallet-packs'),
  createWalletPack: (data) =>
    apiCall('/admin/wallet-packs', { method: 'POST', body: JSON.stringify(data) }),
  updateWalletPack: (packId, data) =>
    apiCall(`/admin/wallet-packs/${packId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteWalletPack: (packId) =>
    apiCall(`/admin/wallet-packs/${packId}`, { method: 'DELETE' }),
};
