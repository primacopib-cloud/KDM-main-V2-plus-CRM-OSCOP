// CRM O'SCOP Bridge — couche relationnelle / impact
import { apiCall } from './http';

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
  updateOppStage: (oppId, stage) =>
    apiCall(`/crm/opportunities/${oppId}/stage`, {
      method: 'PATCH',
      body: JSON.stringify({ stage }),
    }),

  // Dossiers
  createDossier: (payload) =>
    apiCall('/crm/dossiers', { method: 'POST', body: JSON.stringify(payload) }),
  listDossiers: (typeDossier, statut, limit = 100) => {
    const p = new URLSearchParams({ limit });
    if (typeDossier) p.append('type_dossier', typeDossier);
    if (statut) p.append('statut', statut);
    return apiCall(`/crm/dossiers?${p.toString()}`);
  },
  updateDossierStatus: (dossierId, statut, etape) =>
    apiCall(`/crm/dossiers/${dossierId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ statut, etape_actuelle: etape }),
    }),

  // Tasks
  createTask: (payload) =>
    apiCall('/crm/tasks', { method: 'POST', body: JSON.stringify(payload) }),
  listTasks: (status, dueOnly = false) => {
    const p = new URLSearchParams();
    if (status) p.append('status', status);
    if (dueOnly) p.append('due_only', 'true');
    return apiCall(`/crm/tasks${p.toString() ? `?${p.toString()}` : ''}`);
  },
  updateTaskStatus: (taskId, status) =>
    apiCall(`/crm/tasks/${taskId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  // Impact / sync
  impactSummary: () => apiCall('/crm/impact/summary'),
  rebuildFromLolodrive: () =>
    apiCall('/crm/sync/rebuild-from-lolodrive', { method: 'POST' }),
};
