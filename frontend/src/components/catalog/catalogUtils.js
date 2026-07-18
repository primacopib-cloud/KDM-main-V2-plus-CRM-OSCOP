// Format price in cents to euros
export const MIN_INSTALLMENT_CENTS = 550000;

export const formatPrice = (cents) => {
  if (!cents) return '---';
  return (cents / 100).toFixed(2).replace('.', ',') + ' €';
};

// Taux de référence Pack Starter : 1 crédit = 0,50 €
export const CREDIT_RATE_EUR = 0.5;
export const centsToCredits = (cents) => Math.round((cents || 0) / (CREDIT_RATE_EUR * 100));
