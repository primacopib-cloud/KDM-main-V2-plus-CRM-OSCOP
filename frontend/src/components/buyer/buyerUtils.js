import {
  Package, Clock, CheckCircle2, XCircle, Truck,
  ArrowUpRight, ArrowDownRight, RefreshCw,
} from 'lucide-react';

// Format currency
export const formatCurrency = (cents) => {
  if (!cents && cents !== 0) return '---';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
};

// Format date
export const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Format short date
export const formatShortDate = (dateStr) => {
  if (!dateStr) return '---';
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short'
  });
};

// Order status config
export const ORDER_STATUS = {
  PENDING: { label: 'En attente', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: Clock },
  CONFIRMED: { label: 'Confirmée', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: CheckCircle2 },
  PROCESSING: { label: 'En préparation', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30', icon: Package },
  READY_FOR_PICKUP: { label: 'Prête', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: Truck },
  COMPLETED: { label: 'Terminée', color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: CheckCircle2 },
  CANCELED: { label: 'Annulée', color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: XCircle },
};

// Transaction type config
export const TRANSACTION_TYPE = {
  CREDIT_PURCHASE: { label: 'Achat crédits', icon: ArrowUpRight, color: 'text-emerald-400' },
  CREDIT_USED: { label: 'Utilisation', icon: ArrowDownRight, color: 'text-orange-400' },
  REFUND: { label: 'Remboursement', icon: ArrowUpRight, color: 'text-blue-400' },
  ADMIN_ADJUSTMENT: { label: 'Ajustement', icon: RefreshCw, color: 'text-purple-400' },
};
