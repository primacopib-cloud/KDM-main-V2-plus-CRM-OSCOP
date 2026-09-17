import i18n from '@/i18n';
import { BellRing, RotateCcw, Search } from 'lucide-react';
import { Flag } from '../Flag';
import { API } from '../../services/http';

const Pill = ({ active, onClick, children, testId }) => (
  <button type="button" onClick={onClick} data-testid={testId}
    className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
      active ? 'bg-[#D9B35A] text-[#2A1045] on-gold border-[#D9B35A]' : 'bg-white/[0.06] text-white/80 border-white/20 hover:bg-white/15'}`}>
    {children}
  </button>
);

// Filtre enrichi : statut, catégorie, type, provenance, boutique/pays, marque, produit, date, recherche
export const AuctionFilters = ({ filters, setFilters, onReset, categories, types, sources, shops = [], countries = [], brands = [], products = [], brandFollows = null, onToggleBrandFollow = () => {} }) => {
  const set = (k, v) => setFilters((f) => ({ ...f, [k]: f[k] === v ? '' : v }));
  const hasActive = Object.values(filters).some((v) => v);
  return (
    <div className="space-y-2 mb-5" data-testid="auction-filters">
      <div className="flex items-center gap-2 max-w-sm">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-white/35" />
          <input value={filters.q} onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
            placeholder={i18n.t('auction.search')} data-testid="auction-search-input"
            className="w-full h-8 pl-8 pr-3 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white placeholder-white/30 outline-none focus:border-[#D9B35A]/60" />
        </div>
        {hasActive && onReset && (
          <button type="button" onClick={onReset} data-testid="auction-filters-reset-button"
            className="inline-flex items-center gap-1 h-8 px-3 rounded-lg border border-white/20 bg-white/[0.06] text-[11px] font-semibold text-white/75 hover:bg-white/15 hover:text-white transition-colors whitespace-nowrap">
            <RotateCcw className="w-3 h-3" /> Réinitialiser les filtres
          </button>
        )}
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
              testId={`auction-shop-filter-${name}`}><Flag code={cc} /> {name}</Pill>
          ))}
          {countries.length > 1 && countries.map((cc) => (
            <Pill key={cc} active={filters.country === cc} onClick={() => set('country', cc)}
              testId={`auction-country-filter-${cc}`}><Flag code={cc} /> {cc}</Pill>
          ))}
        </div>
      )}
      {brands.length > 0 && (
        <div className="flex flex-wrap gap-1.5 items-center" data-testid="auction-brand-filter-row">
          <span className="text-[11px] font-bold text-white/60 uppercase tracking-wide">Marques</span>
          {brands.map(([b, logo]) => (
            <span key={b} className="inline-flex items-center gap-1">
              <Pill active={filters.brand === b} onClick={() => set('brand', b)}
                testId={`auction-brand-filter-${b}`}>
                {logo && <img src={logo.startsWith('/api/') ? `${API}${logo.slice(4)}` : logo} alt="" className="inline h-3.5 w-auto max-w-[36px] object-contain rounded-[2px] bg-white/90 px-0.5 mr-1 align-[-2px]" />}
                {b}
              </Pill>
              {brandFollows && (
                <button type="button" onClick={() => onToggleBrandFollow(b)}
                  data-testid={`auction-brand-follow-${b}`}
                  title={brandFollows.includes(b) ? 'Ne plus suivre cette marque' : 'Suivre cette marque — alerte à chaque nouveau lot'}
                  className={`w-6 h-6 rounded-full border flex items-center justify-center transition-colors ${
                    brandFollows.includes(b)
                      ? 'text-emerald-300 border-emerald-400/50 bg-emerald-500/15'
                      : 'text-white/45 border-white/20 hover:border-emerald-400/50 hover:text-emerald-300'}`}>
                  <BellRing className="w-3 h-3" />
                </button>
              )}
            </span>
          ))}
        </div>
      )}
      {products.length > 1 && (
        <div className="flex flex-wrap gap-1.5 items-center" data-testid="auction-product-filter-row">
          <span className="text-[11px] font-bold text-white/60 uppercase tracking-wide">Produits</span>
          {products.map((p) => (
            <Pill key={p} active={filters.product === p} onClick={() => set('product', p)}
              testId={`auction-product-filter-${p}`}>{p}</Pill>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-1.5 items-center" data-testid="auction-date-filter-row">
        <span className="text-[11px] font-bold text-white/60 uppercase tracking-wide">Date</span>
        <input type="date" value={filters.date} data-testid="auction-date-filter"
          onChange={(e) => setFilters((f) => ({ ...f, date: e.target.value }))}
          className="h-7 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-[11px] text-white outline-none focus:border-[#D9B35A]/60" />
        {filters.date && (
          <button onClick={() => setFilters((f) => ({ ...f, date: '' }))} data-testid="auction-date-clear"
            className="text-[10px] text-white/45 hover:text-white underline">effacer</button>
        )}
      </div>
    </div>
  );
};
