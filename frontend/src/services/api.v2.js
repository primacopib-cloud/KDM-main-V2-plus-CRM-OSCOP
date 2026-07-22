// V2 APIs (B2B Workflow): orgs, applications, plans, subscriptions, wallet,
// zones, catalog, orders, installments, invoices, admin.
import { apiCallV2 } from './http';

export const orgsAPIV2 = {
  create: async (orgData) => {
    return apiCallV2('/orgs', {
      method: 'POST',
      body: JSON.stringify({
        legal_name: orgData.legalName,
        registration_country: orgData.registrationCountry || 'FR',
        registration_id: orgData.registrationId,
        territory: orgData.territory,
        member_type: orgData.memberType || 'BUYER_PRO',
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

export const catalogAPI = {
  getCategories: async () => {
    return apiCallV2('/catalog/categories');
  },

  suggest: async (q, lang = 'fr') => {
    return apiCallV2(`/catalog/suggest?q=${encodeURIComponent(q)}&lang=${lang}`);
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

  getCartSuggestions: async (limit = 4) => {
    return apiCallV2(`/catalog/cart/suggestions?limit=${limit}`);
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

export const installmentAPI = {
  calculate: async (amountHtCents) => {
    return apiCallV2(`/catalog/installment/calculate?amount_ht_cents=${amountHtCents}`);
  },
};

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
