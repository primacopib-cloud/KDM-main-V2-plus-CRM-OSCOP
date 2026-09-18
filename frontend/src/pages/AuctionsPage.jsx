import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Gavel, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import i18n from '@/i18n';
import { API, getAuthHeaders, getSessionToken, apiCall } from '../services/http';
import LolodriveLayout from '../components/LolodriveLayout';
import { AuctionCard } from '../components/auctions/AuctionCard';
import { AuctionFilters } from '../components/auctions/AuctionFilters';
import { AuctionPlanGate } from '../components/auctions/AuctionPlanGate';
import { WinnerDialog } from '../components/auctions/WinnerDialog';
import { AuctionHistoryPanel } from '../components/auctions/AuctionHistoryPanel';
import { AuctionAlertPrefs } from '../components/auctions/AuctionAlertPrefs';
import { MyPriceAlerts } from '../components/auctions/MyPriceAlerts';
import { HeaderBackButton } from '../components/HeaderBackButton';
import { PriceDropTicker } from '../components/auctions/PriceDropTicker';

const FILTERS_KEY = 'coopact_filters_v1';
const SAVED_FILTERS_KEY = 'coopact_saved_filters_v1';
const DEFAULT_FILTERS = { status: '', category: '', type_id: '', source: '', q: '', shop: '', country: '', brand: '', product: '', date: '' };
const loadFilters = () => {
  try { return { ...DEFAULT_FILTERS, ...JSON.parse(localStorage.getItem(FILTERS_KEY) || '{}') }; }
  catch { return DEFAULT_FILTERS; }
};
const loadSavedFilters = () => {
  try { return JSON.parse(localStorage.getItem(SAVED_FILTERS_KEY) || '[]'); }
  catch { return []; }
};

export default function AuctionsPage() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ items: [], categories: [], types: [], sources: [] });
  const [me, setMe] = useState(null);
  const [follows, setFollows] = useState(null);
  const [filters, setFilters] = useState(loadFilters);
  useEffect(() => {
    try { localStorage.setItem(FILTERS_KEY, JSON.stringify(filters)); } catch {}
  }, [filters]);
  const resetFilters = useCallback(() => {
    try { localStorage.removeItem(FILTERS_KEY); } catch {}
    setFilters(DEFAULT_FILTERS);
  }, []);
  const [savedFilters, setSavedFilters] = useState(loadSavedFilters);
  const persistSaved = (next) => {
    setSavedFilters(next);
    try { localStorage.setItem(SAVED_FILTERS_KEY, JSON.stringify(next)); } catch {}
  };
  const saveFilterSet = (name, current) => {
    persistSaved([...savedFilters.filter((s) => s.name !== name), { name, filters: current }]);
    toast.success(`★ Filtres « ${name} » sauvegardés`);
  };
  const applyFilterSet = (s) => setFilters({ ...DEFAULT_FILTERS, ...s.filters });
  const deleteFilterSet = (name) => persistSaved(savedFilters.filter((s) => s.name !== name));
  const [priceAlerts, setPriceAlerts] = useState(null);
  const [brandFollows, setBrandFollows] = useState(null);
  const [winnerAuction, setWinnerAuction] = useState(null);
  const isLogged = Boolean(getSessionToken());

  const load = useCallback(async () => {
    const qs = new URLSearchParams();
    if (filters.category) qs.set('category', filters.category);
    if (filters.type_id) qs.set('type_id', filters.type_id);
    if (filters.source) qs.set('source', filters.source);
    if (filters.q) qs.set('q', filters.q);
    const res = await fetch(`${API}/auctions/public?${qs}`);
    if (res.ok) setData(await res.json());
  }, [filters.category, filters.type_id, filters.source, filters.q]);

  const loadMe = useCallback(async () => {
    if (!isLogged) return;
    const res = await fetch(`${API}/auctions/me`, { headers: getAuthHeaders(), credentials: 'include' });
    if (res.ok) setMe(await res.json());
  }, [isLogged]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadMe(); }, [loadMe]);

  // Marque les suggestions « Pour vous » comme vues (compteur cloche)
  useEffect(() => {
    try { localStorage.setItem('coopact_suggestions_seen_v1', new Date().toISOString()); } catch {}
  }, []);

  // Rafraîchissement léger des enchères en cours (prix + statuts)
  useEffect(() => {
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  // Retour Stripe : activation du plan par polling
  useEffect(() => {
    const sid = params.get('auction_session_id');
    if (!sid) return;
    let tries = 0;
    const poll = async () => {
      tries += 1;
      try {
        const res = await fetch(`${API}/auctions/plans/status?session_id=${sid}`,
          { headers: getAuthHeaders(), credentials: 'include' });
        const d = await res.json();
        if (d.status === 'ACTIVE') {
          toast.success(`✓ ${d.plan_label}`);
          params.delete('auction_session_id');
          setParams(params, { replace: true });
          loadMe();
          return;
        }
      } catch { /* retry */ }
      if (tries < 6) setTimeout(poll, 2500);
    };
    poll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Lien email gagnant : ?win={auction_id}
  useEffect(() => {
    const winId = params.get('win');
    if (!winId || !me) return;
    const win = (me.wins || []).find((w) => w.id === winId && !w.fulfillment);
    if (win) setWinnerAuction(win);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me]);

  const visible = useMemo(() => {
    let items = data.items;
    if (filters.status === 'FINISHED') items = items.filter((a) => a.status === 'WON' || a.status === 'EXPIRED');
    else if (filters.status) items = items.filter((a) => a.status === filters.status);
    if (filters.shop) items = items.filter((a) => a.retailer?.company_name === filters.shop);
    if (filters.country) items = items.filter((a) => a.retailer?.country_code === filters.country);
    if (filters.brand) items = items.filter((a) => a.brand === filters.brand);
    if (filters.product) items = items.filter((a) => (a.title || '').includes(filters.product));
    if (filters.date) {
      items = items.filter((a) => {
        const d = filters.date;
        const s = (a.starts_at || '').slice(0, 10);
        const e = (a.ends_at || '').slice(0, 10);
        return (!s || s <= d) && (!e || e >= d);
      });
    }
    return items;
  }, [data.items, filters.status, filters.shop, filters.country, filters.brand, filters.product, filters.date]);

  const shopFacets = useMemo(() => {
    const shops = new Map();
    const countries = new Map();
    const brands = new Map();
    const productCount = new Map();
    data.items.forEach((a) => {
      if (a.retailer?.company_name) shops.set(a.retailer.company_name, a.retailer.country_code);
      if (a.retailer?.country_code) countries.set(a.retailer.country_code, true);
      if (a.brand) brands.set(a.brand, a.brand_logo || null);
      const prod = (a.title || '').replace(/^Lot ×\d+ — /, '').replace(/ — lot COOP.*$/i, '').trim();
      if (prod) productCount.set(prod, (productCount.get(prod) || 0) + 1);
    });
    const products = [...productCount.entries()].sort((x, y) => y[1] - x[1]).slice(0, 12).map(([p]) => p);
    return { shops: [...shops.entries()], countries: [...countries.keys()], brands: [...brands.entries()], products };
  }, [data.items]);

  const pendingWin = (me?.wins || []).find((w) => !w.fulfillment);

  const [priceAlertList, setPriceAlertList] = useState([]);
  const loadAlerts = useCallback(async () => {
    if (!isLogged) return;
    try {
      const d = await apiCall('/auctions/price-alerts');
      const m = {};
      (d.alerts || []).forEach((x) => { m[x.auction_id] = x.target_eur; });
      setPriceAlerts(m);
      setPriceAlertList(d.alerts || []);
    } catch { /* liste non critique */ }
  }, [isLogged]);

  useEffect(() => {
    if (!isLogged) return;
    apiCall('/auctions/shops/follows').then((d) => setFollows(d.follows || [])).catch(() => {});
    apiCall('/auctions/brands/follows').then((d) => setBrandFollows(d.follows || [])).catch(() => {});
    loadAlerts();
  }, [isLogged, loadAlerts]);

  const setPriceAlert = async (auctionId, target) => {
    try {
      const r = await apiCall(`/auctions/${auctionId}/price-alert`, {
        method: 'POST', body: JSON.stringify({ target_eur: target }) });
      setPriceAlerts((m) => {
        const n = { ...m };
        if (r.active) n[auctionId] = r.target_eur; else delete n[auctionId];
        return n;
      });
      loadAlerts();
      toast.success(r.active
        ? `🎯 Alerte activée — cloche + email dès que le prix atteint ${r.target_eur.toFixed(2)} €`
        : 'Alerte prix retirée');
    } catch (e) { toast.error(e.message); }
  };

  // Suggestions : lots en salle / à venir correspondant aux marques et boutiques suivies
  const suggestions = useMemo(() => {
    if (!isLogged) return [];
    const f = follows || [];
    const b = brandFollows || [];
    if (!f.length && !b.length) return [];
    return data.items.filter((a) =>
      (a.status === 'LIVE' || a.status === 'SCHEDULED') &&
      ((a.brand && b.includes(a.brand)) ||
       (a.retailer?.detaillant_user_id && f.includes(a.retailer.detaillant_user_id)))
    ).slice(0, 6);
  }, [data.items, follows, brandFollows, isLogged]);
  const suggestedIds = useMemo(() => new Set(suggestions.map((a) => a.id)), [suggestions]);

  const toggleBrandFollow = async (brand) => {
    try {
      const r = await apiCall('/auctions/brands/follow', { method: 'POST', body: JSON.stringify({ brand }) });
      setBrandFollows((f) => (r.following ? [...(f || []), brand] : (f || []).filter((b) => b !== brand)));
      toast.success(r.following ? `✓ Marque ${brand} suivie — alerte à chaque nouveau lot` : 'Suivi retiré');
    } catch (e) { toast.error(e.message); }
  };

  const toggleFollow = async (detaillantId) => {
    try {
      const r = await apiCall(`/auctions/shops/${detaillantId}/follow`, { method: 'POST' });
      setFollows((f) => (r.following ? [...(f || []), detaillantId] : (f || []).filter((x) => x !== detaillantId)));
      toast.success(r.following ? '✓ POP\'S suivi — vous serez alerté de ses nouveaux lots' : 'Suivi retiré');
    } catch (e) { toast.error(e.message); }
  };

  return (
    <LolodriveLayout title={i18n.t('auction.title')} subtitle={i18n.t('auction.subtitle')}>
      <div data-testid="auctions-page">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <HeaderBackButton fallback="/"
            className="!px-3 !rounded-full border border-white/20 hover:border-white/40" />
          <Link to="/coopact" data-testid="coopact-brand-link"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border border-[#D9B35A]/50 text-[#F2D07A] hover:bg-[#D9B35A]/15 transition-colors">
            <Sparkles className="w-3.5 h-3.5" /> {i18n.t('auction.brand_link')}
          </Link>
          <p className="text-[11px] text-amber-200/90 font-semibold" data-testid="auction-rule-note">
            ⚠️ {i18n.t('auction.rule_note')}
          </p>
        </div>

        <PriceDropTicker />

        <AuctionPlanGate me={me} onRefresh={loadMe} isLogged={isLogged} />

        {pendingWin && (
          <button type="button" onClick={() => setWinnerAuction(pendingWin)} data-testid="pending-win-banner"
            className="w-full mb-5 rounded-2xl border border-emerald-400/40 bg-emerald-500/10 p-3 text-left text-sm font-semibold text-emerald-200 hover:bg-emerald-500/20 transition-colors">
            {i18n.t('auction.you_won')} — {pendingWin.title} · {i18n.t('auction.choose_fulfillment')}
          </button>
        )}

        <AuctionFilters filters={filters} setFilters={setFilters} onReset={resetFilters}
          savedFilters={savedFilters} onSaveFilters={saveFilterSet}
          onApplySaved={applyFilterSet} onDeleteSaved={deleteFilterSet}
          categories={data.categories} types={data.types} sources={data.sources}
          shops={shopFacets.shops} countries={shopFacets.countries}
          brands={shopFacets.brands} products={shopFacets.products}
          brandFollows={brandFollows} onToggleBrandFollow={toggleBrandFollow} />

        <MyPriceAlerts alerts={priceAlertList} onRemove={(id) => setPriceAlert(id, 0)} />

        {data.weekly_top && (
          <Link to={`/encheres/lot/${data.weekly_top.reference}`} data-testid="weekly-top-banner"
            className="block mb-5 rounded-2xl border border-[#D9B35A]/50 p-3.5 hover:border-[#D9B35A] transition-colors"
            style={{ background: 'linear-gradient(90deg, rgba(217,179,90,0.16), rgba(217,179,90,0.04))' }}>
            <span className="text-[10px] font-black uppercase tracking-[0.18em] text-[#F2D07A]">
              🏆 Lot vedette de la semaine — le plus coop'acté
            </span>
            <div className="flex flex-wrap items-baseline gap-2 mt-1">
              <span className="text-sm font-bold text-white" data-testid="weekly-top-title">{data.weekly_top.title}</span>
              <span className="text-sm font-bold text-[#E9CF8E]">{Number(data.weekly_top.price_eur).toFixed(2)} €</span>
              <span className="text-[11px] text-white/55">· {data.weekly_top.week_bids} Coop'Act cette semaine</span>
            </div>
          </Link>
        )}

        {suggestions.length > 0 && (
          <div className="mb-5" data-testid="auction-suggestions">
            <div className="text-[11px] font-bold uppercase tracking-wide text-[#F2D07A] mb-2 inline-flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Pour vous — vos marques et boutiques suivies ({suggestions.length})
            </div>
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}>
              {suggestions.map((a) => (
                <AuctionCard key={`sg-${a.id}`} auction={a} canBid={Boolean(me?.active)} suggested
                  weeklyTop={a.id === data.weekly_top?.id}
                  follows={follows} onToggleFollow={toggleFollow}
                  priceAlerts={priceAlerts} onSetPriceAlert={setPriceAlert}
                  onChanged={() => { load(); loadMe(); }} />
              ))}
            </div>
          </div>
        )}

        {visible.length === 0 ? (
          <div className="text-center text-white/40 py-14" data-testid="auctions-empty">
            <Gavel className="w-8 h-8 mx-auto mb-2 opacity-40" />
            {i18n.t('auction.no_auctions')}
          </div>
        ) : (
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}
            data-testid="auctions-grid">
            {visible.map((a, i) => (
              <div key={a.id} className="card-in" style={{ animationDelay: `${Math.min(i * 60, 480)}ms` }}>
                <AuctionCard auction={a} canBid={Boolean(me?.active)}
                  follows={follows} onToggleFollow={toggleFollow}
                  priceAlerts={priceAlerts} onSetPriceAlert={setPriceAlert}
                  suggested={suggestedIds.has(a.id)}
                  weeklyTop={a.id === data.weekly_top?.id}
                  onChanged={() => { load(); loadMe(); }} />
              </div>
            ))}
          </div>
        )}

        <AuctionHistoryPanel me={me} />
        {me?.active && <AuctionAlertPrefs />}

        {winnerAuction && (
          <WinnerDialog auction={winnerAuction} onClose={() => setWinnerAuction(null)}
            onDone={() => { loadMe(); }} />
        )}
      </div>
    </LolodriveLayout>
  );
}
