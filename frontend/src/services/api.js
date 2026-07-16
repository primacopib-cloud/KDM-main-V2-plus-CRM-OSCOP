// API Service — barrel file. Implementations live in domain modules:
//   http.js · api.core.js · api.v2.js · api.lolodrive.js · api.crm.js
// All existing imports (`from '../services/api'`) keep working unchanged.

export {
  authAPI,
  quoteAPI,
  subscriptionAPI,
  creditsAPI,
  passwordAPI,
  statsAPI,
  adminAPI,
  notificationsAPI,
  zonesAPI,
  organizationsAPI,
  downloadOffer,
  documentsAPI,
  exportAPI,
  paymentAPI,
  adminPlansAPI,
} from './api.core';

export {
  orgsAPIV2,
  applicationsAPIV2,
  plansAPIV2,
  subscriptionsAPIV2,
  walletAPIV2,
  zonesAPIV2,
  catalogAPI,
  ordersAPIV2,
  installmentAPI,
  invoicesAPI,
  adminAPIV2,
} from './api.v2';

export { lolodriveAPI } from './api.lolodrive';
export { crmAPI } from './api.crm';
