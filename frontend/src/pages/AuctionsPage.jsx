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

export default function AuctionsPage() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ items: [], categories: [], types: [], sources: [] });
  const [me, setMe] = useState(null);
  const [follows, setFollows] = useState(null);
  const [filters, setFilters] = useState({ status: '', category: '', type_id: '', source: '', q: '', shop: '', country: '', brand: '', product: '', date: '' });
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

  useEffect(() => {
    if (!isLogged) return;
    apiCall('/auctions/shops/follows').then((d) => setFollows(d.follows || [])).catch(() => {});
  }, [isLogged]);

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
          <Link to="/coopact" data-testid="coopact-brand-link"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border border-[#D9B35A]/50 text-[#F2D07A] hover:bg-[#D9B35A]/15 transition-colors">
            <Sparkles className="w-3.5 h-3.5" /> {i18n.t('auction.brand_link')}
          </Link>
          <p className="text-[11px] text-amber-200/90 font-semibold" data-testid="auction-rule-note">
            ⚠️ {i18n.t('auction.rule_note')}
          </p>
        </div>

        <AuctionPlanGate me={me} onRefresh={loadMe} isLogged={isLogged} />

        {pendingWin && (
          <button type="button" onClick={() => setWinnerAuction(pendingWin)} data-testid="pending-win-banner"
            className="w-full mb-5 rounded-2xl border border-emerald-400/40 bg-emerald-500/10 p-3 text-left text-sm font-semibold text-emerald-200 hover:bg-emerald-500/20 transition-colors">
            {i18n.t('auction.you_won')} — {pendingWin.title} · {i18n.t('auction.choose_fulfillment')}
          </button>
        )}

        <AuctionFilters filters={filters} setFilters={setFilters}
          categories={data.categories} types={data.types} sources={data.sources}
          shops={shopFacets.shops} countries={shopFacets.countries}
          brands={shopFacets.brands} products={shopFacets.products} />

        {visible.length === 0 ? (
          <div className="text-center text-white/40 py-14" data-testid="auctions-empty">
            <Gavel className="w-8 h-8 mx-auto mb-2 opacity-40" />
            {i18n.t('auction.no_auctions')}
          </div>
        ) : (
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}
            data-testid="auctions-grid">
            {visible.map((a) => (
              <AuctionCard key={a.id} auction={a} canBid={Boolean(me?.active)}
                follows={follows} onToggleFollow={toggleFollow}
                onChanged={() => { load(); loadMe(); }} />
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
