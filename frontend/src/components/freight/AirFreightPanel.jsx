import { useEffect, useState } from 'react';
import { Plane, Anchor } from 'lucide-react';
import { toast } from 'sonner';
import { API } from '../../services/http';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { FreightToOrder } from './FreightToOrder';
import { FreightToOperation } from './FreightToOperation';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

export const AirFreightPanel = () => {
  const [data, setData] = useState(null);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState({ route_id: '', weight_kg: '100', volume_m3: '' });
  const [quote, setQuote] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API}/public/freight/air/routes`).then((r) => r.json()).then((d) => {
      setData(d);
      if (d.routes?.length) setForm((f) => ({ ...f, route_id: d.routes[0].id }));
    }).catch(() => {});
  }, []);

  const filtered = (data?.routes || []).filter((r) =>
    `${r.origin} ${r.destination}`.toLowerCase().includes(search.toLowerCase()));

  const compute = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/public/freight/air/quote`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          route_id: form.route_id,
          weight_kg: parseFloat(String(form.weight_kg).replace(',', '.')) || 0,
          volume_m3: parseFloat(String(form.volume_m3).replace(',', '.')) || 0,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Erreur');
      setQuote(json);
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  if (!data) return null;
  return (
    <div className="grid md:grid-cols-2 gap-5" data-testid="air-freight-panel">
      <div className="glass-panel-soft rounded-[20px] p-5 space-y-3">
        <div>
          <label className="text-xs text-white/60">Rechercher un aéroport</label>
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="ex: Miami, Réunion…"
            data-testid="air-route-search" className="bg-white/5 border-white/15 text-white" />
        </div>
        <div>
          <label className="text-xs text-white/60">Route aérienne ({filtered.length})</label>
          <select value={form.route_id} onChange={(e) => setForm({ ...form, route_id: e.target.value })}
            data-testid="air-route-select"
            className="w-full bg-white/5 border border-white/15 rounded-md px-3 py-2 text-sm text-white">
            {filtered.map((r) => (
              <option key={r.id} value={r.id} className="bg-[#2A1045]">
                {r.origin} ✈ {r.destination} (~{r.transit_days} j)
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-white/60">Poids réel (kg)</label>
          <Input value={form.weight_kg} onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
            data-testid="air-weight" className="bg-white/5 border-white/15 text-white" />
        </div>
        <div>
          <label className="text-xs text-white/60">Volume (m³, optionnel — poids taxable 167 kg/m³)</label>
          <Input value={form.volume_m3} onChange={(e) => setForm({ ...form, volume_m3: e.target.value })}
            data-testid="air-volume" className="bg-white/5 border-white/15 text-white" />
        </div>
        <Button onClick={compute} disabled={busy} data-testid="air-quote-btn"
          className="on-gold w-full bg-[#D9B35A] hover:bg-[#F2D07A] font-semibold">
          <Plane className="w-4 h-4 mr-1" /> Calculer le tarif aérien
        </Button>
      </div>

      <div className="glass-panel-soft rounded-[20px] p-5">
        <h3 className="text-sm tracking-wider uppercase text-white/70 font-semibold mb-3 flex items-center gap-2">
          <Anchor className="w-4 h-4 text-[#D9B35A]" /> Estimation aérienne
        </h3>
        {!quote ? <p className="text-white/40 text-sm">Renseignez le poids puis calculez.</p> : (
          <div className="space-y-1.5 text-sm" data-testid="air-quote-result">
            <p className="text-white/85 font-semibold">{quote.route}</p>
            <p className="text-white/55 text-xs">Poids taxable : {quote.taxable_weight_kg} kg × {eur(quote.rate_per_kg)}/kg · transit ≈ {quote.transit_days_estimate} j</p>
            <div className="pt-2 space-y-1">
              <div className="flex justify-between text-white/70"><span>Fret aérien de base</span><span>{eur(quote.breakdown.base_freight)}</span></div>
              <div className="flex justify-between text-white/70"><span>Surcharge carburant</span><span>{eur(quote.breakdown.fuel_surcharge)}</span></div>
              <div className="flex justify-between text-white/70"><span>Frais de sûreté</span><span>{eur(quote.breakdown.security_fee)}</span></div>
              <div className="flex justify-between font-bold text-[#E9CF8E] border-t border-white/10 pt-1.5">
                <span>Total HT</span><span>{eur(quote.total_ex_vat)}</span>
              </div>
            </div>
            <p className="text-[11px] text-white/50">{data.note}</p>
            <FreightToOperation quote={{ ...quote, container: 'Fret aérien', quantity: quote.taxable_weight_kg }} />
            <FreightToOrder quote={{ ...quote, container: `Fret aérien (${quote.taxable_weight_kg} kg)`, quantity: 1 }} />
          </div>
        )}
      </div>
    </div>
  );
};
