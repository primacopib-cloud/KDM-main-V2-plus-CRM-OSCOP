import i18n from '@/i18n';
import {
  Plus, CreditCard, TrendingUp, TrendingDown, RefreshCw,
} from 'lucide-react';

export const formatCredits = (amount) => {
  if (amount === null || amount === undefined) return '---';
  return amount.toLocaleString(i18n.language);
};

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

export const TX_TYPES = {
  CREDIT: { label: 'Crédit', icon: TrendingUp, color: 'text-green-400' },
  DEBIT: { label: 'Débit', icon: TrendingDown, color: 'text-red-400' },
  TOPUP: { label: 'Recharge', icon: Plus, color: 'text-blue-400' },
  SUBSCRIPTION: { label: 'Abonnement', icon: CreditCard, color: 'text-purple-400' },
  REFUND: { label: 'Remboursement', icon: RefreshCw, color: 'text-orange-400' },
};

export const ZONE_TYPES = {
  OM: { label: 'Outre-Mer', color: 'bg-blue-500/20 text-blue-400' },
  EU: { label: 'Europe', color: 'bg-green-500/20 text-green-400' },
  CARIB: { label: 'Caraïbes', color: 'bg-purple-500/20 text-purple-400' },
  AFRICA: { label: 'Afrique', color: 'bg-orange-500/20 text-orange-400' },
};
