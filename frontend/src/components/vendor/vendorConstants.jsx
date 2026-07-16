import i18n from '@/i18n';
import { Badge } from '../ui/badge';
import { Clock, CheckCircle2, XCircle, Edit } from 'lucide-react';

// Product categories
export const CATEGORIES = [
  { value: 'alimentaire', label: i18n.t('adm.alimentaire') },
  { value: 'boissons', label: i18n.t('adm.boissons') },
  { value: 'hygiene', label: i18n.t('adm.hygiene_beaute') },
  { value: 'entretien', label: i18n.t('adm.entretien') },
  { value: 'fournitures', label: i18n.t('adm.fournitures') },
  { value: 'textile', label: i18n.t('adm.textile') },
  { value: 'equipement', label: i18n.t('adm.equipement') },
  { value: 'autre', label: i18n.t('adm.autre') },
];

// Unit types
export const UNIT_TYPES = [
  { value: 'unit', label: i18n.t('adm.unite') },
  { value: 'kg', label: i18n.t('adm.kilogramme') },
  { value: 'liter', label: i18n.t('adm.litre') },
  { value: 'box', label: i18n.t('adm.carton') },
  { value: 'pallet', label: i18n.t('adm.palette') },
];

// Format types
export const FORMAT_TYPES = [
  { value: 'standard', label: i18n.t('adm.standard_unite') },
  { value: 'lot', label: i18n.t('adm.lot_pack') },
  { value: 'palette', label: i18n.t('adm.palette_complete') },
  { value: 'container', label: i18n.t('adm.container') },
];

// TVA rates
export const TVA_RATES = [
  { value: 0, label: i18n.t('adm.0_exonere') },
  { value: 2.1, label: i18n.t('adm.2_1_super_reduit') },
  { value: 5.5, label: i18n.t('adm.5_5_reduit') },
  { value: 8.5, label: i18n.t('adm.8_5_dom') },
  { value: 10, label: i18n.t('adm.10_intermediaire') },
  { value: 20, label: i18n.t('adm.20_normal') },
];

// Zones
export const ZONES = ['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'MAYOTTE'];

// Status badge helper
export const getStatusBadge = (status) => {
  switch (status) {
    case 'pending_approval':
      return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200"><Clock className="w-3 h-3 mr-1" /> {i18n.t('adm.en_attente')}</Badge>;
    case 'approved':
      return <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200"><CheckCircle2 className="w-3 h-3 mr-1" /> {i18n.t('adm.approuve')}</Badge>;
    case 'rejected':
      return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" /> {i18n.t('adm.rejete')}</Badge>;
    case 'draft':
      return <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200"><Edit className="w-3 h-3 mr-1" /> {i18n.t('adm.brouillon')}</Badge>;
    case 'inactive':
      return <Badge variant="secondary"><XCircle className="w-3 h-3 mr-1" /> {i18n.t('adm.inactif')}</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
};

