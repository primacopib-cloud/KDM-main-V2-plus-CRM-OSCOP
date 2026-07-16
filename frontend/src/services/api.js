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

import {
  authAPI, quoteAPI, subscriptionAPI, creditsAPI, passwordAPI, statsAPI,
  adminAPI, notificationsAPI, zonesAPI, organizationsAPI, downloadOffer,
  documentsAPI, exportAPI, paymentAPI,
} from './api.core';
import {
  orgsAPIV2, applicationsAPIV2, plansAPIV2, subscriptionsAPIV2, walletAPIV2,
  zonesAPIV2, catalogAPI, ordersAPIV2, installmentAPI, adminAPIV2,
} from './api.v2';

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
