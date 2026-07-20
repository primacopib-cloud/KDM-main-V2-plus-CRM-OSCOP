import { useState } from 'react';
import { Ship } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const TERRITORIES = ['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'HEXAGONE'];
const inp = 'h-8 rounded-lg px-2 text-[11px] text-white bg-white/[0.05] border border-white/15';
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;

export const FreightEstimateInline = ({ territories }) => {
  const parsed = (territories || '').split(',').map((t) => t.trim().toUpperCase()).filter((t) => TERRITORIES.includes(t));
  const [f, setF] = useState({ origin: parsed[0] || 'GUADELOUPE', destination: parsed[1] || 'MARTINIQUE', weight_kg: '' });
  const [result, setResult] = useState(null);

  const simulate = async () => {
    const r = await fetch(`${API}/buyer-tools/freight/simulate`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ ...f, weight_kg: Number(f.weight_kg) || 0, volume_m3: 0 }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setResult(d);
  };

  return (
    <div className="p-2.5 rounded-xl bg-white/[0.04] border border-[#D9B35A]/20 space-y-2" data-testid="freight-inline">
      <p className="text-[10px] font-bold text-[#E9CF8E] flex items-center gap-1.5">
        <Ship className="w-3 h-3" /> Estimation de fret inter-îles (lot interterritorial)
      </p>
      <div className="flex flex-wrap items-center gap-1.5">
        <select className={inp} style={{ colorScheme: 'dark' }} value={f.origin}
          onChange={(e) => setF({ ...f, origin: e.target.value })} data-testid="freight-inline-origin">
          {TERRITORIES.map((t) => <option key={t} value={t} style={{ background: '#2A1045' }}>{t}</option>)}
        </select>
        <span className="text-white/40 text-xs">→</span>
        <select className={inp} style={{ colorScheme: 'dark' }} value={f.destination}
          onChange={(e) => setF({ ...f, destination: e.target.value })} data-testid="freight-inline-destination">
          {TERRITORIES.map((t) => <option key={t} value={t} style={{ background: '#2A1045' }}>{t}</option>)}
        </select>
        <input className={`${inp} w-20`} type="number" min="0" placeholder="kg" value={f.weight_kg}
          onChange={(e) => setF({ ...f, weight_kg: e.target.value })} data-testid="freight-inline-weight" />
        <button type="button" onClick={simulate} data-testid="freight-inline-btn"
          className="px-2.5 py-1.5 rounded-lg text-[10px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
          Estimer
        </button>
        {result && (
          <span className="text-[11px] text-white/75" data-testid="freight-inline-result">
            ≈ <b className="text-[#E9CF8E]">{eur(result.total_ht_cents)} HT</b> · {result.delay_days} j
          </span>
        )}
      </div>
      {result && <p className="text-[9.5px] text-white/35">{result.disclaimer}</p>}
    </div>
  );
};
