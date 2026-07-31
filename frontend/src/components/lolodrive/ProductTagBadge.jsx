// Étiquettes commerciales produits + badge LOT — partagés catalogue client, POS et admin
export const PRODUCT_TAGS = [
  { value: 'PROMO', label: 'Promo', cls: 'text-red-300 border-red-400/50' },
  { value: 'SOLDE', label: 'Solde', cls: 'text-orange-300 border-orange-400/50' },
  { value: 'NOUVEAU', label: 'Nouveau', cls: 'text-emerald-300 border-emerald-400/50' },
  { value: 'DESTOCKAGE', label: 'Déstockage', cls: 'text-sky-300 border-sky-400/50' },
  { value: 'EXCLUSIVITE', label: 'Exclusivité', cls: 'text-[#E9CF8E] border-[#D9B35A]/60' },
];

export const TagBadge = ({ tag, sku }) => {
  const t = PRODUCT_TAGS.find((x) => x.value === tag);
  if (!t) return null;
  return (
    <span data-testid={`tag-badge-${sku}`}
      className={`px-1 py-0.5 rounded bg-black/60 border backdrop-blur-sm uppercase ${t.cls}`}>
      {t.label}
    </span>
  );
};

export const LotBadge = ({ p }) =>
  p.is_lot ? (
    <span data-testid={`lot-badge-${p.sku}`}
      className="px-1 py-0.5 rounded text-fuchsia-300 bg-black/60 border border-fuchsia-400/50 backdrop-blur-sm">
      LOT ×{p.lot_total_qty}{p.lot_free_qty ? ` (+${p.lot_free_qty} OFFERT${p.lot_free_qty > 1 ? 'S' : ''})` : ''}
    </span>
  ) : null;

// Compte à rebours d'étiquette : « fin dans X j » / « dernier jour ! » — urgence d'achat
export const TagCountdown = ({ p }) => {
  if (!p.tag || !p.tag_until) return null;
  const ms = new Date(p.tag_until).getTime() - Date.now();
  if (ms <= 0) return null;
  const days = Math.ceil(ms / 86400000);
  const label = days <= 1 ? '⏳ dernier jour !' : days <= 3 ? `⏳ fin dans ${days} j !` : `fin dans ${days} j`;
  return (
    <span data-testid={`tag-countdown-${p.sku}`}
      className={`px-1 py-0.5 rounded bg-black/60 border backdrop-blur-sm ${days <= 3 ? 'text-red-300 border-red-400/50 animate-pulse' : 'text-amber-300 border-amber-400/40'}`}>
      {label}
    </span>
  );
};
