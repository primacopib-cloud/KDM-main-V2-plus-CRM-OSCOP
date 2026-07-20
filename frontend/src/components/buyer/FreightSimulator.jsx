import { useEffect, useState } from 'react';
import { Ship } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;
const panel = 'bg-white/[0.04] border border-white/[0.08] rounded-2xl';
const inp = 'h-9 rounded-lg px-2 text-xs text-white bg-white/[0.05] border border-white/15';
const LABELS = { GUADELOUPE: 'Guadeloupe', MARTINIQUE: 'Martinique', GUYANE: 'Guyane', REUNION: 'Réunion', HEXAGONE: 'Hexagone' };

export const FreightSimulator = () => {
  const [territories, setTerritories] = useState([]);
  const [f, setF] = useState({ origin: 'GUADELOUPE', destinations: ['MARTINIQUE'], weight_kg: '', volume_m3: '', express: false });
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/buyer-tools/freight/rates`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setTerritories(d.territories || [])).catch(() => {});
  }, []);

  const toggleDest = (t) => setF((p) => ({
    ...p, destinations: p.destinations.includes(t) ? p.destinations.filter((x) => x !== t) : [...p.destinations, t],
  }));

  const simulate = async () => {
    if (!f.destinations.length) return toast.error('Sélectionnez au moins une destination');
    const r = await fetch(`${API}/api/buyer-tools/freight/simulate-multi`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ origin: f.origin, destinations: f.destinations, express: f.express, weight_kg: Number(f.weight_kg) || 0, volume_m3: Number(f.volume_m3) || 0 }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setResult(d);
  };

  return (
    <div className={`${panel} p-5`} data-testid="freight-simulator">
      <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
        <Ship className="w-4 h-4 text-[#D9B35A]" /> Simulation de fret inter-îles
      </h3>
      <p className="text-[11px] text-white/40 mb-3">Estimez le coût logistique vers une ou plusieurs destinations (règle du payant : poids ou volume).</p>
      <div className="flex flex-wrap items-end gap-2 mb-2">
        <div><p className="text-[10px] text-white/50 mb-1">Origine</p>
          <select className={inp} style={{ colorScheme: 'dark' }} value={f.origin} onChange={(e) => setF({ ...f, origin: e.target.value, destinations: f.destinations.filter((d) => d !== e.target.value) })} data-testid="freight-origin">
            {territories.map((t) => <option key={t} value={t} style={{ background: '#2A1045' }}>{LABELS[t] || t}</option>)}
          </select></div>
        <div><p className="text-[10px] text-white/50 mb-1">Poids (kg)</p>
          <input className={`${inp} w-24`} type="number" min="0" value={f.weight_kg} onChange={(e) => setF({ ...f, weight_kg: e.target.value })} data-testid="freight-weight" /></div>
        <div><p className="text-[10px] text-white/50 mb-1">Volume (m³)</p>
          <input className={`${inp} w-24`} type="number" min="0" step="0.1" value={f.volume_m3} onChange={(e) => setF({ ...f, volume_m3: e.target.value })} data-testid="freight-volume" /></div>
        <label className="inline-flex items-center gap-1.5 h-9 text-xs text-white/60 cursor-pointer">
          <input type="checkbox" checked={f.express} onChange={(e) => setF({ ...f, express: e.target.checked })} className="w-4 h-4 accent-[#D9B35A]" data-testid="freight-express" />
          Express (×1,6)
        </label>
        <button type="button" onClick={simulate} data-testid="freight-simulate-btn"
          className="h-9 px-4 rounded-xl text-xs font-bold hover:brightness-110 transition-all"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>Simuler</button>
      </div>
      <div className="mb-3">
        <p className="text-[10px] text-white/50 mb-1">Destinations (multi-sélection)</p>
        <div className="flex flex-wrap gap-1.5">
          {territories.filter((t) => t !== f.origin).map((t) => {
            const on = f.destinations.includes(t);
            return (
              <button key={t} type="button" onClick={() => toggleDest(t)} data-testid={`freight-dest-${t}`}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-colors ${on ? 'bg-[#D9B35A]/25 text-[#E9CF8E] border-[#D9B35A]/50' : 'bg-white/[0.04] text-white/40 border-white/10 hover:text-white/70'}`}>
                {LABELS[t] || t}
              </button>
            );
          })}
        </div>
      </div>
      {result && (
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid="freight-result">
          <div className="space-y-1.5 mb-2">
            {result.items.map((it) => (
              <div key={it.destination} className="flex flex-wrap items-center gap-2 text-[11px]" data-testid={`freight-result-${it.destination}`}>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/70">{LABELS[it.destination] || it.destination}</span>
                <span className="font-bold text-[#E9CF8E]">{eur(it.total_ht_cents)} HT</span>
                <span className="text-white/45">facturé au {it.billed_on} · BAF {it.fuel_surcharge_pct} % · {it.delay_days} j{it.express ? ' · express' : ''}</span>
              </div>
            ))}
          </div>
          {result.items.length > 1 && (
            <div className="pt-2 border-t border-white/[0.08] flex items-center gap-2">
              <p className="text-[10px] text-white/50 uppercase font-semibold">Total {result.items.length} destinations</p>
              <p className="text-xl font-bold text-[#E9CF8E]" data-testid="freight-grand-total">{eur(result.grand_total_ht_cents)} <span className="text-xs text-white/40">HT</span></p>
            </div>
          )}
          {result.items.length === 1 && (
            <p className="text-2xl font-bold text-[#E9CF8E]" data-testid="freight-total">{eur(result.items[0].total_ht_cents)} <span className="text-xs text-white/40">HT</span></p>
          )}
          <p className="text-[10px] text-white/35 mt-2">{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
};
