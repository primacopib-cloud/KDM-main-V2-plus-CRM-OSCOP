import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Repeat, XCircle } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;
const S_LABEL = { ACTIVE: 'Actif', PENDING: 'En attente de paiement', CANCELLING: 'Résiliation programmée', PAST_DUE: 'Paiement en échec' };

export const CpcSubscriptionPanel = ({ onChanged }) => {
  const [plans, setPlans] = useState([]);
  const [sub, setSub] = useState(null);
  const [params, setParams] = useSearchParams();

  const load = useCallback(() => {
    fetch(`${API}/api/cpc/subscription/plans`, { credentials: 'include' }).then((r) => r.json()).then((d) => setPlans(d.items || [])).catch(() => {});
    fetch(`${API}/api/cpc/subscription/me`, { credentials: 'include' }).then((r) => r.json()).then((d) => setSub(d.subscription)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!params.get('sub_session')) return;
    let tries = 0;
    const poll = setInterval(async () => {
      tries += 1;
      try {
        const r = await fetch(`${API}/api/cpc/subscription/me`, { credentials: 'include' });
        const d = await r.json();
        if (d.subscription?.status === 'ACTIVE') {
          clearInterval(poll);
          toast.success(`Abonnement ${d.subscription.plan_label} activé — ${d.subscription.monthly_cpc} CREDI'SCOP/mois`);
          params.delete('sub_session'); setParams(params, { replace: true });
          setSub(d.subscription);
          onChanged?.();
        } else if (tries > 30) clearInterval(poll);
      } catch { /* retry */ }
    }, 2000);
    return () => clearInterval(poll);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const subscribe = async (plan) => {
    const r = await fetch(`${API}/api/cpc/subscription/checkout`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan_id: plan.id, origin_url: window.location.origin }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    window.location.href = d.checkout_url;
  };

  const cancel = async () => {
    if (!window.confirm('Résilier votre abonnement à la fin de la période en cours ? Les crédits déjà reçus restent utilisables jusqu\'à leur expiration.')) return;
    const r = await fetch(`${API}/api/cpc/subscription/cancel`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(d.message);
    load();
  };

  const active = sub && ['ACTIVE', 'CANCELLING', 'PAST_DUE'].includes(sub.status);
  return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 space-y-3" data-testid="cpc-subscription-panel">
      <h3 className="font-semibold text-white flex items-center gap-2">
        <Repeat className="w-4 h-4 text-[#D9B35A]" /> Abonnement mensuel avec CREDI'SCOP inclus
      </h3>
      {active ? (
        <div className="flex flex-wrap items-center gap-3 p-3 rounded-xl bg-[#D9B35A]/10 border border-[#D9B35A]/25" data-testid="cpc-sub-active">
          <div className="flex-1 min-w-[200px]">
            <p className="text-sm font-bold text-[#E9CF8E]">Formule {sub.plan_label} — {sub.monthly_cpc} CREDI'SCOP/mois</p>
            <p className="text-xs text-white/55">{eur(sub.ttc_cents)} TTC/mois · statut : {S_LABEL[sub.status] || sub.status}</p>
          </div>
          {sub.status !== 'CANCELLING' && (
            <button type="button" onClick={cancel} data-testid="cpc-sub-cancel-btn"
              className="px-3 py-1.5 rounded-lg text-xs font-bold bg-white/10 text-white/70 hover:text-white inline-flex items-center gap-1 transition-colors">
              <XCircle className="w-3.5 h-3.5" /> Résilier
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {plans.map((p) => (
            <div key={p.id} className="border border-white/10 rounded-xl p-4 text-center space-y-1.5 hover:border-[#D9B35A]/40 transition-colors" data-testid={`cpc-sub-plan-${p.id}`}>
              <p className="text-sm font-bold text-white/75">{p.label}</p>
              <p className="text-2xl font-bold text-[#E9CF8E]">{p.monthly_cpc} <span className="text-[10px] text-white/40">CREDI'SCOP/mois</span></p>
              <p className="text-sm font-bold text-white">{eur(p.price_ht_cents)} <span className="text-[10px] text-white/40">HT/mois</span></p>
              <button type="button" onClick={() => subscribe(p)} data-testid={`cpc-sub-btn-${p.id}`}
                className="w-full py-2 rounded-xl text-xs font-bold hover:brightness-110 transition-all"
                style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>
                S'abonner
              </button>
            </div>
          ))}
        </div>
      )}
      <p className="text-[11px] text-white/40">
        Crédits inclus ajoutés chaque mois à réception du paiement (validité 3 mois). Résiliable à tout moment,
        effective en fin de période. Sans effet sur le classement des offres.
      </p>
    </div>
  );
};
