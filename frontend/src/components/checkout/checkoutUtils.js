export const MIN_INSTALLMENT_CENTS = 550000;

import { Package, Truck, FileSignature, CreditCard } from 'lucide-react';

export const formatCurrency = (cents) => {
  if (!cents && cents !== 0) return '---';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
};

// Steps configuration
export const STEPS = [
  { id: 'review', label: 'Récapitulatif', icon: Package },
  { id: 'delivery', label: 'Livraison', icon: Truck },
  { id: 'preparation', label: 'Préparation', icon: Package },
  { id: 'signature', label: 'Signature', icon: FileSignature },
  { id: 'payment', label: 'Paiement', icon: CreditCard },
];

