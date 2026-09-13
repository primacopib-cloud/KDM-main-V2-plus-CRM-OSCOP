import { useEffect, useState } from 'react';
import { Coins, Lock } from 'lucide-react';
import { toast } from 'sonner';
import i18n from '@/i18n';
import { API, getAuthHeaders } from '../../services/http';

// Plan CREDI'SCOP-Enchères obligatoire pour enchérir : solde + achat Stripe
export const AuctionPlanGate = ({ me, onRefresh, isLogged }) => {
  const [plans, setPlans] = useState([]);

  useEffect(() => {
    fetch(`${API}/auctions/plans`).then((r) => r.json()).then((d) => setPlans(d.items || [])).catch(() => {});
  }, []);

  const buy = async (planId) => {
    if (!isLogged) {
      window.location.href = '/connexion?next=/encheres';
      return;
    }
    try {
      const res = await fetch(`${API}/auctions/plans/checkout`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        credentials: 'include',
        body: JSON.stringify({ plan_id: planId, origin_url: window.location.origin }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erreur');
      window.location.href = data.checkout_url;
    } catch (e) {
      toast.error(String(e.message || e));
    }
  };

  if (me?.active) {
    const acc = me.account || {};
    return (
      <div className="mb-5 rounded-2xl border border-[#D9B35A]/35 bg-[#D9B35A]/[0.07] p-3 flex flex-wrap items-center gap-4"
        data-testid="auction-account-bar">
        <span className="inline-flex items-center gap-1.5 text-sm font-bold text-[#E9CF8E]">
          <Coins className="w-4 h-4" /> {i18n.t('auction.my_credits')} : {acc.credits ?? 0}
        </span>
        <span className="text-[11px] text-white/55">
          {acc.plan_label} · {i18n.t('auction.valid_until')} {acc.valid_until ? new Date(acc.valid_until).toLocaleDateString(i18n.language) : '—'}
        </span>
        <div className="ml-auto flex gap-2">
          {plans.map((p) => (
            <button key={p.id} type="button" onClick={() => buy(p.id)}
              data-testid={`auction-recharge-${p.id}`}
              className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-white/10 text-white/70 hover:bg-white/20 transition-colors">
              +{p.credits} cr. — {(p.price_ht_cents / 100).toFixed(2)} € HT
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-5 rounded-2xl border border-[#D9B35A]/35 bg-[#D9B35A]/[0.07] p-4" data-testid="auction-plan-gate">
      <p className="text-sm font-semibold text-[#E9CF8E] flex items-center gap-2 mb-3">
        <Lock className="w-4 h-4" /> {i18n.t('auction.plan_required')}
      </p>
      <div className="grid gap-2 sm:grid-cols-3">
        {plans.map((p) => (
          <div key={p.id} className="rounded-xl bg-white/[0.04] border border-white/10 p-3 flex flex-col gap-1"
            data-testid={`auction-plan-${p.id}`}>
            <span className="text-xs font-bold text-white">{p.label}</span>
            <span className="text-lg font-bold text-[#E9CF8E]">{(p.price_ht_cents / 100).toFixed(2)} € <span className="text-[10px] text-white/40">HT</span></span>
            <span className="text-[11px] text-white/55">{p.credits} {i18n.t('auction.credits')} · {p.validity_days} j</span>
            <button type="button" onClick={() => buy(p.id)} data-testid={`auction-buy-plan-${p.id}`}
              className="mt-1 h-8 rounded-lg text-[11px] font-bold text-[#2A1045] transition-transform hover:scale-[1.02]"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
              {i18n.t('auction.buy_plan')}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
