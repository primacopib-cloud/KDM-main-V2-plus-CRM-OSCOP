import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Store, Coins, Package, BadgeCheck } from 'lucide-react';
import { toast } from 'sonner';
import { detaillantAPI } from '../services/api.detaillant';
import { authAPI } from '../services/api';
import { DetaillantProfileCard } from '../components/detaillant/DetaillantProfileCard';
import { DetaillantOfferForm } from '../components/detaillant/DetaillantOfferForm';
import { DetaillantSalesTable } from '../components/detaillant/DetaillantSalesTable';
import { DT } from '../components/detaillant/detaillantI18n';

const STATUS_COLOR = { PENDING: '#f59e0b', APPROVED: '#10b981', REJECTED: '#ef4444' };

export default function DetaillantSpacePage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [lang, setLang] = useState('fr');
  const t = DT[lang];
  const [info, setInfo] = useState(null);
  const [offers, setOffers] = useState([]);
  const [reg, setReg] = useState({ email: '', password: '', company_name: '' });
  const [guest, setGuest] = useState(false);

  const load = useCallback(async () => {
    try {
      const [i, o] = await Promise.all([detaillantAPI.profile(), detaillantAPI.myOffers()]);
      setInfo(i); setOffers(o.offers || []); setGuest(false);
    } catch {
      setGuest(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const sid = params.get('sub_session');
    if (sid) {
      detaillantAPI.activate(sid)
        .then(() => { toast.success('Abonnement Détaillant activé ✓'); load(); })
        .catch((e) => toast.error(e.message));
    }
    const cid = params.get('credits_session');
    if (cid) {
      detaillantAPI.creditsActivate(cid)
        .then((r) => { toast.success(`+${r.credits} crédits COOP'ACT crédités ✓`); load(); })
        .catch((e) => toast.error(e.message));
    }
  }, [params, load]);

  const buyCredits = async (pack) => {
    try {
      const r = await detaillantAPI.creditsCheckout(pack, window.location.origin);
      window.location.href = r.checkout_url;
    } catch (e) { toast.error(e.message); }
  };

  const register = async () => {
    try {
      await detaillantAPI.register(reg);
      await authAPI.login(reg.email, reg.password);
      toast.success('Compte Détaillant créé ✓');
      await load();
    } catch (e) { toast.error(e.message); }
  };

  const subscribe = async () => {
    try {
      const r = await detaillantAPI.checkout(window.location.origin);
      window.location.href = r.checkout_url;
    } catch (e) { toast.error(e.message); }
  };

  const langBtns = (
    <div className="flex gap-1" data-testid="dt-lang-switch">
      {['fr', 'en', 'es', 'gcf'].map((l) => (
        <button key={l} onClick={() => setLang(l)} data-testid={`dt-lang-${l}`}
          className={`px-2 h-7 rounded-full text-[10px] font-bold border ${lang === l ? 'bg-[#D9B35A] text-black border-[#D9B35A]' : 'text-white/60 border-white/15 hover:border-[#D9B35A]/50'}`}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );

  if (guest) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] text-white px-4 py-10">
        <div className="max-w-md mx-auto space-y-4" data-testid="detaillant-register">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-[#E9CF8E]">{t.space}</h1>
            {langBtns}
          </div>
          <p className="text-sm text-white/60">{t.tagline} — 390 €/mois, 3 offres de lots incluses.</p>
          <input placeholder={t.company} value={reg.company_name}
            onChange={(e) => setReg((p) => ({ ...p, company_name: e.target.value }))}
            className="w-full h-10 px-3 rounded-lg bg-white/[0.05] border border-white/15 text-sm" data-testid="reg-company" />
          <input placeholder={t.email} type="email" value={reg.email}
            onChange={(e) => setReg((p) => ({ ...p, email: e.target.value }))}
            className="w-full h-10 px-3 rounded-lg bg-white/[0.05] border border-white/15 text-sm" data-testid="reg-email" />
          <input placeholder={t.password} type="password" value={reg.password}
            onChange={(e) => setReg((p) => ({ ...p, password: e.target.value }))}
            className="w-full h-10 px-3 rounded-lg bg-white/[0.05] border border-white/15 text-sm" data-testid="reg-password" />
          <button onClick={register} data-testid="reg-submit"
            className="w-full h-10 rounded-full bg-[#D9B35A] text-black text-sm font-bold hover:bg-[#E9CF8E]">
            {t.register}
          </button>
          <button onClick={() => navigate('/connexion')} className="w-full text-xs text-white/50 hover:text-white underline">
            {t.login}
          </button>
        </div>
      </div>
    );
  }

  if (!info) return <div className="min-h-screen bg-[#0a0a0f]" />;

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-5" data-testid="detaillant-space">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h1 className="text-2xl font-bold text-[#E9CF8E] flex items-center gap-2">
              <Store className="w-6 h-6" /> {t.space}
            </h1>
            <p className="text-xs text-white/50 mt-1">{t.tagline}</p>
          </div>
          {langBtns}
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3" data-testid="dt-kpi-credits">
            <Coins className="w-4 h-4 text-[#D9B35A]" />
            <p className="text-lg font-bold mt-1">{info.credits}</p>
            <p className="text-[10px] text-white/50">{t.credits}</p>
            <div className="flex gap-1 mt-1.5 flex-wrap">
              {[['P100', '100'], ['P300', '300'], ['P500', '500']].map(([pack, n]) => (
                <button key={pack} onClick={() => buyCredits(pack)} data-testid={`dt-buy-${pack}`}
                  className="px-1.5 h-5 rounded-full text-[9px] font-bold text-[#E9CF8E] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/15">
                  +{n} ({n / 10} €)
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3" data-testid="dt-kpi-offers">
            <Package className="w-4 h-4 text-[#D9B35A]" />
            <p className="text-lg font-bold mt-1">{info.offers_used_this_month}/{info.included_offers}</p>
            <p className="text-[10px] text-white/50">{t.offersUsed}</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3" data-testid="dt-kpi-sub">
            <BadgeCheck className={`w-4 h-4 ${info.subscription_active ? 'text-emerald-400' : 'text-white/30'}`} />
            <p className="text-xs font-bold mt-1">{info.subscription_active ? t.subActive : '—'}</p>
            <p className="text-[10px] text-white/50">390 €/mois</p>
          </div>
        </div>

        {!info.subscription_active && (
          <div className="rounded-2xl border border-amber-400/30 bg-amber-500/[0.06] p-4" data-testid="dt-subscribe-card">
            <p className="text-sm text-amber-200 mb-3">{t.subNeeded}</p>
            <button onClick={subscribe} data-testid="dt-subscribe-btn"
              className="h-10 px-6 rounded-full bg-[#D9B35A] text-black text-sm font-bold hover:bg-[#E9CF8E]">
              {t.subscribe}
            </button>
          </div>
        )}

        <DetaillantProfileCard t={t} profile={info.profile} onSaved={load} />

        {info.subscription_active && <DetaillantOfferForm t={t} info={info} onCreated={load} />}

        {info.subscription_active && <DetaillantSalesTable />}

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="dt-offers-list">
          <h3 className="text-sm font-bold text-[#E9CF8E] mb-3">{t.myOffers} ({offers.length})</h3>
          {offers.length === 0 && <p className="text-xs text-white/40">—</p>}
          <div className="space-y-2">
            {offers.map((o) => (
              <div key={o.id} className="flex items-center justify-between gap-3 p-2.5 rounded-xl bg-white/[0.03] border border-white/10"
                data-testid={`dt-offer-${o.id}`}>
                <div className="min-w-0">
                  <p className="text-xs font-bold truncate">{o.product_name} · {o.qty_lots} lot(s) ×3 {o.lot_type === 'COMPOSED' ? '(composé)' : ''}</p>
                  <p className="text-[10px] text-white/50 truncate">{o.description}</p>
                  {o.final_price != null && (
                    <p className="text-[10px] text-[#E9CF8E]" data-testid={`dt-offer-price-${o.id}`}>
                      {Number(o.lot_price).toFixed(2)} {o.currency} → <strong>{Number(o.final_price).toFixed(2)} {o.currency}</strong> (−{Number(o.discount_pct).toFixed(0)} %)
                    </p>
                  )}
                  {o.scheduled_start && new Date(o.scheduled_start) > new Date() && (
                    <p className="text-[10px] text-amber-300" data-testid={`dt-offer-countdown-${o.id}`}>
                      ⏳ Programmée — démarre dans {Math.max(0, Math.floor((new Date(o.scheduled_start) - Date.now()) / 3600000))} h ({new Date(o.scheduled_start).toLocaleString('fr-FR')})
                    </p>
                  )}
                  {o.review_note && <p className="text-[10px] text-red-300">Motif : {o.review_note}</p>}
                </div>
                <div className="text-right shrink-0">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
                    style={{ color: STATUS_COLOR[o.status], borderColor: `${STATUS_COLOR[o.status]}66` }}>
                    {t[o.status.toLowerCase()] || o.status}
                  </span>
                  <p className="text-[10px] text-white/40 mt-1">{o.cost_credits} cr.</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
