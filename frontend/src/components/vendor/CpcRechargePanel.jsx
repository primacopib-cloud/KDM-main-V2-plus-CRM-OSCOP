import { useEffect, useState } from 'react';
import { BellRing } from 'lucide-react';
import { toast } from 'sonner';
import { Switch } from '../ui/switch';

const API = process.env.REACT_APP_BACKEND_URL;
const inp = 'h-9 rounded-lg px-2.5 text-sm text-white bg-white/[0.05] border border-white/15 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';

export const CpcRechargePanel = ({ packs }) => {
  const [s, setS] = useState({ enabled: false, threshold: 20, pack_id: 'cpc-pack-150' });

  useEffect(() => {
    fetch(`${API}/api/cpc/recharge/settings`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setS({ enabled: !!d.enabled, threshold: d.threshold ?? 20, pack_id: d.pack_id || 'cpc-pack-150' }))
      .catch(() => {});
  }, []);

  const save = async () => {
    const r = await fetch(`${API}/api/cpc/recharge/settings`, {
      method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...s, threshold: parseInt(s.threshold, 10) || 20 }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(s.enabled
      ? `Recharge activée : email avec lien de paiement 1 clic sous ${s.threshold} CREDI'SCOP`
      : 'Recharge automatique désactivée');
  };

  return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 space-y-3" data-testid="cpc-recharge-panel">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <BellRing className="w-4 h-4 text-[#D9B35A]" /> Recharge semi-automatique
        </h3>
        <Switch checked={s.enabled} onCheckedChange={(v) => setS({ ...s, enabled: v })} data-testid="cpc-recharge-switch" />
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-white/60">Si mon solde passe sous</span>
        <input className={`${inp} w-20`} type="number" min="1"
          value={s.threshold} onChange={(e) => setS({ ...s, threshold: e.target.value })} data-testid="cpc-recharge-threshold" />
        <span className="text-white/60">CREDI'SCOP, m'envoyer un lien de paiement 1 clic pour le</span>
        <select className={inp} style={{ colorScheme: 'dark' }} value={s.pack_id}
          onChange={(e) => setS({ ...s, pack_id: e.target.value })} data-testid="cpc-recharge-pack">
          {(packs || []).map((p) => <option key={p.id} value={p.id} style={{ background: '#2A1045' }}>{p.label} ({p.credits} CREDI'SCOP — {(p.price_ht_cents / 100).toFixed(2)} € HT)</option>)}
        </select>
        <button type="button" onClick={save} data-testid="cpc-recharge-save"
          className="px-3.5 py-2 rounded-xl text-xs font-bold hover:brightness-110 transition-all"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>
          Enregistrer
        </button>
      </div>
      <p className="text-[11px] text-white/40">
        Aucune carte enregistrée, aucun débit automatique : vous validez chaque paiement sur la page sécurisée Stripe.
        Un seul email par franchissement de seuil.
      </p>
    </div>
  );
};
