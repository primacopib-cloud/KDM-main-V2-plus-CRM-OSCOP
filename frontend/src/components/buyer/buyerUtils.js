import i18n from '@/i18n';
import {
  Package, Clock, CheckCircle2, XCircle, Truck,
  ArrowUpRight, ArrowDownRight, RefreshCw,
} from 'lucide-react';

// Format currency
export const formatCurrency = (cents) => {
  if (!cents && cents !== 0) return '---';
  return new Intl.NumberFormat(i18n.language, {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
};

// Format date
export const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  return new Date(dateStr).toLocaleDateString(i18n.language, {
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
  return new Date(dateStr).toLocaleDateString(i18n.language, {
    day: '2-digit',
    month: 'short'
  });
};

// Order status config
export const ORDER_STATUS = {
  PENDING: { get label() { return i18n.t('orders.en_attente'); }, color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: Clock },
  CONFIRMED: { get label() { return i18n.t('orders.confirmee'); }, color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: CheckCircle2 },
  PROCESSING: { get label() { return i18n.t('orders.en_preparation'); }, color: 'bg-purple-500/20 text-purple-400 border-purple-500/30', icon: Package },
  READY_FOR_PICKUP: { get label() { return i18n.t('orders.prete_a_enlever'); }, color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: Truck },
  COMPLETED: { get label() { return i18n.t('orders.terminee'); }, color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: CheckCircle2 },
  CANCELED: { get label() { return i18n.t('orders.annulee'); }, color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: XCircle },
};

// Transaction type config
export const TRANSACTION_TYPE = {
  CREDIT_PURCHASE: { get label() { return i18n.t('wallet.achat_credits'); }, icon: ArrowUpRight, color: 'text-emerald-400' },
  CREDIT_USED: { get label() { return i18n.t('wallet.utilisation'); }, icon: ArrowDownRight, color: 'text-orange-400' },
  REFUND: { get label() { return i18n.t('wallet.remboursement'); }, icon: ArrowUpRight, color: 'text-blue-400' },
  ADMIN_ADJUSTMENT: { get label() { return i18n.t('wallet.ajustement'); }, icon: RefreshCw, color: 'text-purple-400' },
};
