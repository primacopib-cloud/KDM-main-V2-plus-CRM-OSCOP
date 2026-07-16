import {
  Star, Plus, ShoppingCart, Package, Wallet, FileText, LayoutDashboard,
  Scale, Home, CreditCard, Building2, Store, Users,
} from 'lucide-react';

export const iconMap = {
  Star,
  ShoppingCart,
  Package,
  Wallet,
  FileText,
  LayoutDashboard,
  Scale,
  Home,
  CreditCard,
  Building2,
  Store,
  Users,
  Plus,
};

export const getIcon = (iconName) => {
  return iconMap[iconName] || Star;
};

// Color options
export const colorOptions = [
  { value: '#D9B35A', label: 'Or' },
  { value: '#D4AF37', label: 'Vert' },
  { value: '#3B82F6', label: 'Bleu' },
  { value: '#8B5CF6', label: 'Violet' },
  { value: '#EC4899', label: 'Rose' },
  { value: '#F59E0B', label: 'Orange' },
  { value: '#EF4444', label: 'Rouge' },
  { value: '#06B6D4', label: 'Cyan' },
];

