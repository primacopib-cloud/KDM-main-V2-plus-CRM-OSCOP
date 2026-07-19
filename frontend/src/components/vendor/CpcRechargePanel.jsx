import { useEffect, useState } from 'react';
import { BellRing } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';

const API = process.env.REACT_APP_BACKEND_URL;

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
      ? `Recharge activée : email avec lien de paiement 1 clic sous ${s.threshold} CPC`
      : 'Recharge automatique désactivée');
  };

  return (
    <Card data-testid="cpc-recharge-panel">
      <CardContent className="p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <BellRing className="w-4 h-4 text-purple-600" /> Recharge semi-automatique
          </h3>
          <Switch checked={s.enabled} onCheckedChange={(v) => setS({ ...s, enabled: v })} data-testid="cpc-recharge-switch" />
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-gray-600">Si mon solde passe sous</span>
          <input className="h-9 w-20 rounded-lg border border-gray-200 px-2.5 text-sm" type="number" min="1"
            value={s.threshold} onChange={(e) => setS({ ...s, threshold: e.target.value })} data-testid="cpc-recharge-threshold" />
          <span className="text-gray-600">CPC, m'envoyer un lien de paiement 1 clic pour le</span>
          <select className="h-9 rounded-lg border border-gray-200 px-2.5 text-sm" value={s.pack_id}
            onChange={(e) => setS({ ...s, pack_id: e.target.value })} data-testid="cpc-recharge-pack">
            {(packs || []).map((p) => <option key={p.id} value={p.id}>{p.label} ({p.credits} CPC — {(p.price_ht_cents / 100).toFixed(2)} € HT)</option>)}
          </select>
          <Button size="sm" onClick={save} className="bg-purple-600 hover:bg-purple-700" data-testid="cpc-recharge-save">Enregistrer</Button>
        </div>
        <p className="text-[11px] text-gray-400">
          Aucune carte enregistrée, aucun débit automatique : vous validez chaque paiement sur la page sécurisée Stripe.
          Un seul email par franchissement de seuil.
        </p>
      </CardContent>
    </Card>
  );
};
