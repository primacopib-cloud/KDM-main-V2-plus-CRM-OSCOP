// Format price in cents to euros (locale-aware)
import { fmtMoney } from '../../i18n/fmt';

export const MIN_INSTALLMENT_CENTS = 550000;

export const formatPrice = (cents) => {
  if (!cents) return '---';
  return fmtMoney(cents / 100);
};

// Taux de référence Pack Starter : 1 crédit = 0,50 €
export const CREDIT_RATE_EUR = 0.5;
export const centsToCredits = (cents) => Math.round((cents || 0) / (CREDIT_RATE_EUR * 100));
