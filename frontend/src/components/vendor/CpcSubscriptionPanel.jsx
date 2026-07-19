import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Repeat, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';

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
          toast.success(`Abonnement ${d.subscription.plan_label} activé — ${d.subscription.monthly_cpc} CPC/mois`);
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
    if (!window.confirm('Résilier votre abonnement CPC à la fin de la période en cours ? Les CPC déjà crédités restent utilisables jusqu\'à leur expiration.')) return;
    const r = await fetch(`${API}/api/cpc/subscription/cancel`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(d.message);
    load();
  };

  const active = sub && ['ACTIVE', 'CANCELLING', 'PAST_DUE'].includes(sub.status);
  return (
    <Card data-testid="cpc-subscription-panel">
      <CardContent className="p-5 space-y-3">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <Repeat className="w-4 h-4 text-purple-600" /> Abonnement mensuel avec CPC inclus
        </h3>
        {active ? (
          <div className="flex flex-wrap items-center gap-3 p-3 rounded-lg bg-purple-50 border border-purple-100" data-testid="cpc-sub-active">
            <div className="flex-1 min-w-[200px]">
              <p className="text-sm font-bold text-purple-700">Formule {sub.plan_label} — {sub.monthly_cpc} CPC/mois</p>
              <p className="text-xs text-gray-500">{eur(sub.ttc_cents)} TTC/mois · statut : {S_LABEL[sub.status] || sub.status}</p>
            </div>
            {sub.status !== 'CANCELLING' && (
              <Button variant="outline" size="sm" onClick={cancel} data-testid="cpc-sub-cancel-btn">
                <XCircle className="w-3.5 h-3.5 mr-1" /> Résilier
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {plans.map((p) => (
              <div key={p.id} className="border border-gray-200 rounded-xl p-4 text-center space-y-1.5 hover:border-purple-300 transition-colors" data-testid={`cpc-sub-plan-${p.id}`}>
                <p className="text-sm font-bold text-gray-700">{p.label}</p>
                <p className="text-2xl font-bold text-purple-600">{p.monthly_cpc} <span className="text-xs text-gray-400">CPC/mois</span></p>
                <p className="text-sm font-bold text-gray-900">{eur(p.price_ht_cents)} <span className="text-[10px] text-gray-400">HT/mois</span></p>
                <Button size="sm" onClick={() => subscribe(p)} className="w-full bg-purple-600 hover:bg-purple-700" data-testid={`cpc-sub-btn-${p.id}`}>
                  S'abonner
                </Button>
              </div>
            ))}
          </div>
        )}
        <p className="text-[11px] text-gray-400">
          CPC inclus crédités chaque mois à réception du paiement (validité 3 mois). Résiliable à tout moment,
          effective en fin de période. Sans effet sur le classement des offres.
        </p>
      </CardContent>
    </Card>
  );
};
