import { Badge } from '../ui/badge';
import { Clock, CheckCircle2, XCircle, Edit } from 'lucide-react';

// Product categories
export const CATEGORIES = [
  { value: 'alimentaire', label: 'Alimentaire' },
  { value: 'boissons', label: 'Boissons' },
  { value: 'hygiene', label: 'Hygiène & Beauté' },
  { value: 'entretien', label: 'Entretien' },
  { value: 'fournitures', label: 'Fournitures' },
  { value: 'textile', label: 'Textile' },
  { value: 'equipement', label: 'Équipement' },
  { value: 'autre', label: 'Autre' },
];

// Unit types
export const UNIT_TYPES = [
  { value: 'unit', label: 'Unité' },
  { value: 'kg', label: 'Kilogramme' },
  { value: 'liter', label: 'Litre' },
  { value: 'box', label: 'Carton' },
  { value: 'pallet', label: 'Palette' },
];

// Format types
export const FORMAT_TYPES = [
  { value: 'standard', label: 'Standard (unité)' },
  { value: 'lot', label: 'Lot / Pack' },
  { value: 'palette', label: 'Palette complète' },
  { value: 'container', label: 'Container' },
];

// TVA rates
export const TVA_RATES = [
  { value: 0, label: '0% (Exonéré)' },
  { value: 2.1, label: '2.1% (Super-réduit)' },
  { value: 5.5, label: '5.5% (Réduit)' },
  { value: 8.5, label: '8.5% (DOM)' },
  { value: 10, label: '10% (Intermédiaire)' },
  { value: 20, label: '20% (Normal)' },
];

// Zones
export const ZONES = ['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'MAYOTTE'];

// Status badge helper
export const getStatusBadge = (status) => {
  switch (status) {
    case 'pending_approval':
      return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200"><Clock className="w-3 h-3 mr-1" /> En attente</Badge>;
    case 'approved':
      return <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200"><CheckCircle2 className="w-3 h-3 mr-1" /> Approuvé</Badge>;
    case 'rejected':
      return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" /> Rejeté</Badge>;
    case 'draft':
      return <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200"><Edit className="w-3 h-3 mr-1" /> Brouillon</Badge>;
    case 'inactive':
      return <Badge variant="secondary"><XCircle className="w-3 h-3 mr-1" /> Inactif</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
};

