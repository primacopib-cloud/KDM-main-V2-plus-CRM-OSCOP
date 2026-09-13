export const NOTIF_CATEGORIES = [
  { key: 'stock', label: 'Stock' },
  { key: 'promo', label: 'Promotions' },
  { key: 'auction', label: "COOP'ACT" },
  { key: 'other', label: 'Autres' },
];

export const classifyNotif = (type) => {
  const t = (type || '').toLowerCase();
  if (t.includes('stock') || t.includes('restock')) return 'stock';
  if (t.includes('promo')) return 'promo';
  if (t.includes('bid') || t.includes('enchere') || t.includes('auction')) return 'auction';
  return 'other';
};

const DEFAULT_PREFS = { stock: true, promo: true, auction: true, other: true };
export const getSoundPrefs = () => {
  try { return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem('notif_sound_cats') || '{}') }; }
  catch { return { ...DEFAULT_PREFS }; }
};
export const saveSoundPrefs = (prefs) => localStorage.setItem('notif_sound_cats', JSON.stringify(prefs));
