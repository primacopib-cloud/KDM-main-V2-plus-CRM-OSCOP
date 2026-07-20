import { useEffect, useState } from 'react';
import { Ship } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const inp = 'h-8 rounded-lg px-2 text-[11px] text-white bg-white/[0.05] border border-white/15';
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;

export const FreightEstimateInline = ({ territories }) => {
  const [codes, setCodes] = useState(['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'MAYOTTE']);
  const parsed = (territories || '').split(',').map((t) => t.trim().toUpperCase()).filter((t) => codes.includes(t));
  const [f, setF] = useState({ origin: '', destinations: [], weight_kg: '' });
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch(`${API}/buyer-tools/freight/rates`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => d.territories?.length && setCodes(d.territories)).catch(() => {});
  }, []);

  const origin = f.origin || parsed[0] || codes[0];
  const destinations = f.destinations.length ? f.destinations : (parsed.length > 1 ? parsed.slice(1) : [codes.find((c) => c !== origin)]);

  const toggleDest = (c) => setF((p) => {
    const cur = p.destinations.length ? p.destinations : destinations;
    return { ...p, destinations: cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c] };
  });

  const simulate = async () => {
    const r = await fetch(`${API}/buyer-tools/freight/simulate-multi`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ origin, destinations, weight_kg: Number(f.weight_kg) || 0, volume_m3: 0 }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setResult(d);
  };

  return (
    <div className="p-2.5 rounded-xl bg-white/[0.04] border border-[#D9B35A]/20 space-y-2" data-testid="freight-inline">
      <p className="text-[10px] font-bold text-[#E9CF8E] flex items-center gap-1.5">
        <Ship className="w-3 h-3" /> Estimation de fret inter-îles (lot interterritorial{destinations.length > 1 ? ` — ${destinations.length} destinations` : ''})
      </p>
      <div className="flex flex-wrap items-center gap-1.5">
        <select className={inp} style={{ colorScheme: 'dark' }} value={origin}
          onChange={(e) => setF({ ...f, origin: e.target.value, destinations: destinations.filter((d) => d !== e.target.value) })} data-testid="freight-inline-origin">
          {codes.map((t) => <option key={t} value={t} style={{ background: '#2A1045' }}>{t}</option>)}
        </select>
        <span className="text-white/40 text-xs">→</span>
        {codes.filter((c) => c !== origin).map((c) => {
          const on = destinations.includes(c);
          return (
            <button key={c} type="button" onClick={() => toggleDest(c)} data-testid={`freight-inline-dest-${c}`}
              className={`px-1.5 py-1 rounded-lg text-[9px] font-bold border transition-colors ${on ? 'bg-[#D9B35A]/25 text-[#E9CF8E] border-[#D9B35A]/50' : 'bg-white/[0.04] text-white/40 border-white/10'}`}>
              {c}
            </button>
          );
        })}
        <input className={`${inp} w-20`} type="number" min="0" placeholder="kg" value={f.weight_kg}
          onChange={(e) => setF({ ...f, weight_kg: e.target.value })} data-testid="freight-inline-weight" />
        <button type="button" onClick={simulate} data-testid="freight-inline-btn"
          className="px-2.5 py-1.5 rounded-lg text-[10px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
          Estimer
        </button>
        {result && (
          <span className="text-[11px] text-white/75" data-testid="freight-inline-result">
            ≈ <b className="text-[#E9CF8E]">{eur(result.grand_total_ht_cents)} HT</b>
            {result.items.length > 1 && <span className="text-white/45"> ({result.items.map((i) => `${i.destination} ${eur(i.total_ht_cents)}`).join(' · ')})</span>}
          </span>
        )}
      </div>
      {result && <p className="text-[9.5px] text-white/35">{result.disclaimer}</p>}
    </div>
  );
};
