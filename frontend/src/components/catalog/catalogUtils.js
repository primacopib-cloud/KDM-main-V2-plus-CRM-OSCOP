// Format price in cents to euros
export const MIN_INSTALLMENT_CENTS = 550000;

export const formatPrice = (cents) => {
  if (!cents) return '---';
  return (cents / 100).toFixed(2).replace('.', ',') + ' €';
};
