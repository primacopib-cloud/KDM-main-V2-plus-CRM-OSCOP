import i18n from '@/i18n';
import { FileText, Clock, Eye, CheckCircle2, XCircle, AlertCircle, Shield } from 'lucide-react';

export const APP_STATUSES = {
  DRAFT: { label: i18n.t('adm.brouillon'), color: 'bg-gray-500/20 text-gray-400', icon: FileText },
  SUBMITTED: { label: i18n.t('adm.soumis'), color: 'bg-yellow-500/20 text-yellow-400', icon: Clock },
  PENDING_REVIEW: { label: i18n.t('adm.en_revision'), color: 'bg-blue-500/20 text-blue-400', icon: Eye },
  APPROVED: { label: i18n.t('adm.approuve'), color: 'bg-green-500/20 text-green-400', icon: CheckCircle2 },
  REJECTED: { label: i18n.t('adm.rejete'), color: 'bg-red-500/20 text-red-400', icon: XCircle },
};

// Org status configuration
export const ORG_STATUSES = {
  DRAFT: { label: i18n.t('adm.brouillon'), color: 'bg-gray-500/20 text-gray-400' },
  SUBMITTED: { label: i18n.t('adm.soumis'), color: 'bg-yellow-500/20 text-yellow-400' },
  PENDING_REVIEW: { label: i18n.t('adm.en_revision'), color: 'bg-blue-500/20 text-blue-400' },
  APPROVED: { label: i18n.t('adm.approuve'), color: 'bg-green-500/20 text-green-400' },
  REJECTED: { label: i18n.t('adm.rejete'), color: 'bg-red-500/20 text-red-400' },
  SUSPENDED: { label: i18n.t('adm.suspendu'), color: 'bg-orange-500/20 text-orange-400' },
  CLOSED: { label: i18n.t('adm.ferme'), color: 'bg-gray-500/20 text-gray-400' },
};

// Rejection reasons
export const REJECTION_REASONS = [
  { code: 'INCOMPLETE_DOCS', label: i18n.t('adm.documents_incomplets_ou_illisibles') },
  { code: 'INVALID_REGISTRATION', label: i18n.t('adm.numero_d_immatriculation_invalide') },
  { code: 'INELIGIBLE_ACTIVITY', label: i18n.t('adm.activite_non_eligible') },
  { code: 'DUPLICATE', label: i18n.t('adm.demande_en_doublon') },
  { code: 'FRAUD_SUSPICION', label: i18n.t('adm.suspicion_de_fraude') },
  { code: 'OTHER', label: i18n.t('adm.autre_raison') },
];

// Format date
export const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  const date = new Date(dateStr);
  return date.toLocaleDateString(i18n.language, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

