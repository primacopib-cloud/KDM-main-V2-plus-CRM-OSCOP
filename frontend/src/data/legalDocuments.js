// Legal Documents Data - CGV KDMARCHE B2B, CG O'SCOP & Convention de partenariat
// Contenus découpés dans ./legal/* (règle < 500 lignes)
// Template variables are replaced at runtime with actual values

import { legalVariables } from './legal/variables';
import { cgvKdmarcheContent, cgOscopContent } from './legal/cgv';
import { conventionContent, auditComplianceTable, invoiceTemplate } from './legal/convention';
import { charteESSContent, annexeLogiscopContent } from './legal/ess';
import { contratTransportLogiscopContent, annexeTourneesESSContent } from './legal/logiscop';

export {
  legalVariables,
  cgvKdmarcheContent,
  cgOscopContent,
  conventionContent,
  auditComplianceTable,
  invoiceTemplate,
  charteESSContent,
  annexeLogiscopContent,
  contratTransportLogiscopContent,
  annexeTourneesESSContent,
};

export const allLegalDocuments = [
  cgvKdmarcheContent,
  cgOscopContent,
  conventionContent,
  charteESSContent,
  annexeLogiscopContent,
  contratTransportLogiscopContent,
  annexeTourneesESSContent
];

// Helper function to replace template variables
export const replaceVariables = (text, variables = legalVariables) => {
  if (!text) return '';
  let result = text;
  Object.entries(variables).forEach(([key, value]) => {
    result = result.replace(new RegExp(`{{${key}}}`, 'g'), value);
  });
  return result;
};

// Get document by ID
export const getDocumentById = (id) => {
  return allLegalDocuments.find(doc => doc.id === id) || null;
};
