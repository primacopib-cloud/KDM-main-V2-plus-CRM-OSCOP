import i18n from '@/i18n';
import { Search } from 'lucide-react';

const flag = (cc) => (cc && cc.length === 2
  ? String.fromCodePoint(...[...cc.toUpperCase()].map((c) => 127397 + c.charCodeAt(0)))
  : '');

const Pill = ({ active, onClick, children, testId }) => (
  <button type="button" onClick={onClick} data-testid={testId}
    className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
      active ? 'bg-[#D9B35A] text-[#2A1045] on-gold border-[#D9B35A]' : 'bg-white/[0.06] text-white/80 border-white/20 hover:bg-white/15'}`}>
    {children}
  </button>
);

// Filtre enrichi : statut, catégorie, type, provenance, boutique/pays, recherche
export const AuctionFilters = ({ filters, setFilters, categories, types, sources, shops = [], countries = [] }) => {
  const set = (k, v) => setFilters((f) => ({ ...f, [k]: f[k] === v ? '' : v }));
  return (
    <div className="space-y-2 mb-5" data-testid="auction-filters">
      <div className="relative max-w-sm">
        <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-white/35" />
        <input value={filters.q} onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
          placeholder={i18n.t('auction.search')} data-testid="auction-search-input"
          className="w-full h-8 pl-8 pr-3 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white placeholder-white/30 outline-none focus:border-[#D9B35A]/60" />
      </div>
      <div className="flex flex-wrap gap-1.5 items-center" data-testid="auction-status-filter-row">
        {[['', 'filter_all'], ['LIVE', 'filter_live'], ['SCHEDULED', 'filter_scheduled'], ['FINISHED', 'filter_finished']].map(([v, k]) => (
          <Pill key={k} active={filters.status === v} onClick={() => setFilters((f) => ({ ...f, status: v }))}
            testId={`auction-status-filter-${v || 'all'}`}>{i18n.t(`auction.${k}`)}</Pill>
        ))}
      </div>
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-1.5 items-center" data-testid="auction-category-filter-row">
          <span className="text-[11px] font-bold text-white/60 uppercase tracking-wide">{i18n.t('auction.filter_category')}</span>
          {categories.map((c) => (
            <Pill key={c.id} active={filters.category === c.id} onClick={() => set('category', c.id)}
              testId={`auction-cat-filter-${c.id}`}>{c.label}</Pill>
          ))}
        </div>
      )}
      {types.length > 0 && (
        <div className="flex flex-wrap gap-1.5 items-center" data-testid="auction-type-filter-row">
          <span className="text-[11px] font-bold text-white/60 uppercase tracking-wide">{i18n.t('auction.filter_type')}</span>
          {types.map((t) => (
            <Pill key={t.id} active={filters.type_id === t.id} onClick={() => set('type_id', t.id)}
              testId={`auction-type-filter-${t.id}`}>{t.label}</Pill>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-1.5 items-center" data-testid="auction-source-filter-row">
        <span className="text-[11px] font-bold text-white/60 uppercase tracking-wide">{i18n.t('auction.filter_source')}</span>
        {sources.map((s) => (
          <Pill key={s.code} active={filters.source === s.code} onClick={() => set('source', s.code)}
            testId={`auction-source-filter-${s.code}`}>{s.label}</Pill>
        ))}
      </div>
      {shops.length > 0 && (
        <div className="flex flex-wrap gap-1.5 items-center" data-testid="auction-shop-filter-row">
          <span className="text-[11px] font-bold text-white/60 uppercase tracking-wide">Boutiques</span>
          {shops.map(([name, cc]) => (
            <Pill key={name} active={filters.shop === name} onClick={() => set('shop', name)}
              testId={`auction-shop-filter-${name}`}>{flag(cc)} {name}</Pill>
          ))}
          {countries.length > 1 && countries.map((cc) => (
            <Pill key={cc} active={filters.country === cc} onClick={() => set('country', cc)}
              testId={`auction-country-filter-${cc}`}>{flag(cc)} {cc}</Pill>
          ))}
        </div>
      )}
    </div>
  );
};
