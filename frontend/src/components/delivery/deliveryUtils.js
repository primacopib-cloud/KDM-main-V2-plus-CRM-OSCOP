import i18n from '@/i18n';

export const formatCurrency = (cents) => {
  return new Intl.NumberFormat(i18n.language, {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
};
