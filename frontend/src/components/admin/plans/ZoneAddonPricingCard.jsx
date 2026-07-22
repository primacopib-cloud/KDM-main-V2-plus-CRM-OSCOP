import { useEffect, useState } from 'react';
import { MapPin, Save, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';

export const ZoneAddonPricingCard = () => {
  const [credits, setCredits] = useState('');
  const [priceEur, setPriceEur] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch(`${API}/zone-addon/pricing`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setCredits(String(d.credits));
        setPriceEur(String(d.price_eur_cents / 100));
      }).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/zone-addon/admin/pricing`, {
        method: 'PUT', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          credits: Number(credits) || 0,
          price_eur_cents: Math.round((Number(priceEur) || 0) * 100),
        }),
      });
      if (!r.ok) throw new Error();
      toast.success('Tarif zone additionnelle enregistré');
    } catch { toast.error('Enregistrement impossible'); }
    setSaving(false);
  };

  return (
    <div className="mb-4 rounded-xl p-4 flex flex-wrap items-end gap-4"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(217,179,90,0.25)' }}
      data-testid="zone-addon-pricing-card">
      <div className="flex items-center gap-2 text-white/80 text-sm font-semibold min-w-[220px]">
        <MapPin className="w-4 h-4 text-[#D9B35A]" />
        Zone additionnelle (add-on)
        <span className="block text-[10px] font-normal text-white/40">Prix d'ajout d'une zone à un abonnement</span>
      </div>
      <label className="text-xs text-white/50">
        Prix en crédits
        <input type="number" min="0" value={credits} onChange={(e) => setCredits(e.target.value)}
          data-testid="zone-addon-credits-input"
          className="block mt-1 w-28 h-9 px-2 rounded-lg text-sm text-white bg-white/[0.06] border border-white/15 focus:outline-none" />
      </label>
      <label className="text-xs text-white/50">
        Prix carte (€ HT)
        <input type="number" min="0" step="0.01" value={priceEur} onChange={(e) => setPriceEur(e.target.value)}
          data-testid="zone-addon-eur-input"
          className="block mt-1 w-28 h-9 px-2 rounded-lg text-sm text-white bg-white/[0.06] border border-white/15 focus:outline-none" />
      </label>
      <button type="button" onClick={save} disabled={saving} data-testid="zone-addon-pricing-save"
        className="inline-flex items-center gap-1.5 h-9 px-4 rounded-lg text-xs font-bold disabled:opacity-50"
        style={{ background: '#D9B35A', color: '#070A10' }}>
        {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} Enregistrer
      </button>
    </div>
  );
};
