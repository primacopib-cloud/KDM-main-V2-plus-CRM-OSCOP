import i18n from '@/i18n';

const LOCALE_MAP = { fr: 'fr-FR', en: 'en-GB', es: 'es-ES', gcf: 'fr-FR', ar: 'ar' };

export const uiLocale = () => {
  const l = i18n.language || 'fr';
  const key = l.startsWith('gcf') ? 'gcf' : l.slice(0, 2);
  return LOCALE_MAP[key] || 'fr-FR';
};

// Montants : chiffres occidentaux (latn) conservés en arabe
export const fmtMoney = (eur, opts = {}) =>
  new Intl.NumberFormat(uiLocale() === 'ar' ? 'ar-u-nu-latn' : uiLocale(), {
    style: 'currency', currency: 'EUR', ...opts,
  }).format(eur);

export const fmtNumber = (n) =>
  new Intl.NumberFormat(uiLocale() === 'ar' ? 'ar-u-nu-latn' : uiLocale()).format(n);

export const fmtDate = (d, opts = { day: 'numeric', month: 'short', year: 'numeric' }) => {
  const date = typeof d === 'string' ? new Date(d) : d;
  if (!date || Number.isNaN(date.getTime())) return '';
  const loc = uiLocale() === 'ar' ? 'ar-u-nu-latn' : uiLocale();
  return new Intl.DateTimeFormat(loc, opts).format(date);
};
