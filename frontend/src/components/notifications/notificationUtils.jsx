import i18n from '@/i18n';
import React from 'react';
import {
  Bell, FileText, User, Building2, Wallet, AlertTriangle, ShoppingCart,
  Truck, Package, CreditCard, ClipboardCheck, CheckCircle, XCircle,
} from 'lucide-react';

export const getNotificationIcon = (type) => {
  const icons = {
    new_quote: FileText,
    new_user: User,
    org_submitted: Building2,
    org_approved: CheckCircle,
    org_rejected: XCircle,
    subscription_activated: CreditCard,
    subscription_past_due: AlertTriangle,
    order_created: ShoppingCart,
    order_shipped: Truck,
    order_delivered: Package,
    wallet_credit: Plus,
    wallet_debit: Minus,
    system_alert: Bell,
    document_ready: FileText,
    pod_available: ClipboardCheck,
  };
  return icons[type] || Bell;
};

export const getNotificationColor = (type) => {
  const colors = {
    new_quote: '#D9B35A',
    new_user: '#D4AF37',
    org_submitted: '#3B82F6',
    org_approved: '#10B981',
    org_rejected: '#EF4444',
    subscription_activated: '#8B5CF6',
    subscription_past_due: '#F59E0B',
    order_created: '#06B6D4',
    order_shipped: '#14B8A6',
    order_delivered: '#22C55E',
    wallet_credit: '#10B981',
    wallet_debit: '#EF4444',
    system_alert: '#6B7280',
    document_ready: '#8B5CF6',
    pod_available: '#0EA5E9',
  };
  return colors[type] || '#6B7280';
};

export const dateFilterOptions = [
  { value: 'all', label: 'Toutes les dates' },
  { value: 'today', label: "Aujourd'hui" },
  { value: 'yesterday', label: 'Hier' },
  { value: 'last_7_days', label: '7 derniers jours' },
  { value: 'last_30_days', label: '30 derniers jours' },
];

export const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  
  if (diff < 60000) return 'À l\'instant';
  if (diff < 3600000) return `Il y a ${Math.floor(diff / 60000)} min`;
  if (diff < 86400000) return `Il y a ${Math.floor(diff / 3600000)}h`;
  
  return date.toLocaleDateString(i18n.language, {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit'
  });
};

