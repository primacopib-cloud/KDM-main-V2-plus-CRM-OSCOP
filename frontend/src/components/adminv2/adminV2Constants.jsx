import { FileText, Clock, Eye, CheckCircle2, XCircle, AlertCircle, Shield } from 'lucide-react';

export const APP_STATUSES = {
  DRAFT: { label: 'Brouillon', color: 'bg-gray-500/20 text-gray-400', icon: FileText },
  SUBMITTED: { label: 'Soumis', color: 'bg-yellow-500/20 text-yellow-400', icon: Clock },
  PENDING_REVIEW: { label: 'En révision', color: 'bg-blue-500/20 text-blue-400', icon: Eye },
  APPROVED: { label: 'Approuvé', color: 'bg-green-500/20 text-green-400', icon: CheckCircle2 },
  REJECTED: { label: 'Rejeté', color: 'bg-red-500/20 text-red-400', icon: XCircle },
};

// Org status configuration
export const ORG_STATUSES = {
  DRAFT: { label: 'Brouillon', color: 'bg-gray-500/20 text-gray-400' },
  SUBMITTED: { label: 'Soumis', color: 'bg-yellow-500/20 text-yellow-400' },
  PENDING_REVIEW: { label: 'En révision', color: 'bg-blue-500/20 text-blue-400' },
  APPROVED: { label: 'Approuvé', color: 'bg-green-500/20 text-green-400' },
  REJECTED: { label: 'Rejeté', color: 'bg-red-500/20 text-red-400' },
  SUSPENDED: { label: 'Suspendu', color: 'bg-orange-500/20 text-orange-400' },
  CLOSED: { label: 'Fermé', color: 'bg-gray-500/20 text-gray-400' },
};

// Rejection reasons
export const REJECTION_REASONS = [
  { code: 'INCOMPLETE_DOCS', label: 'Documents incomplets ou illisibles' },
  { code: 'INVALID_REGISTRATION', label: 'Numéro d\'immatriculation invalide' },
  { code: 'INELIGIBLE_ACTIVITY', label: 'Activité non éligible' },
  { code: 'DUPLICATE', label: 'Demande en doublon' },
  { code: 'FRAUD_SUSPICION', label: 'Suspicion de fraude' },
  { code: 'OTHER', label: 'Autre raison' },
];

// Format date
export const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  const date = new Date(dateStr);
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

