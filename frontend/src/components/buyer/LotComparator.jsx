import { useEffect, useState } from 'react';
import { GitCompareArrows } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => (c == null ? '—' : `${(c / 100).toFixed(2).replace('.', ',')} € HT`);
const panel = 'bg-white/[0.04] border border-white/[0.08] rounded-2xl';
const sel = 'h-9 rounded-lg px-2 text-xs text-white bg-white/[0.05] border border-white/15 flex-1 min-w-[200px]';

const Side = ({ lot, testid }) => (
  <div className="flex-1 min-w-[240px] p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-1.5" data-testid={testid}>
    <p className="text-xs font-bold text-[#E9CF8E]">{lot.ref}</p>
    <p className="text-sm font-bold text-white">{lot.title}</p>
    <p className="text-[10px] text-white/45">{lot.status.replace(/_/g, ' ')} · {lot.category} · clôture {String(lot.closes_at || '').slice(0, 10)}</p>
    <div className="grid grid-cols-2 gap-x-3 gap-y-1 pt-2 text-[11px]">
      <span className="text-white/50">Inscrits</span><b className="text-white/85 text-right">{lot.participants}</b>
      <span className="text-white/50">Offres valides</span><b className="text-white/85 text-right">{lot.valid_bids}</b>
      <span className="text-white/50">Meilleure offre</span><b className="text-[#E9CF8E] text-right">{eur(lot.best_offer_ht_cents)}</b>
      <span className="text-white/50">Offre médiane</span><b className="text-white/85 text-right">{eur(lot.median_offer_ht_cents)}</b>
      {lot.winner && (<><span className="text-white/50">Attributaire</span><b className="text-emerald-400 text-right">{lot.winner}</b></>)}
    </div>
  </div>
);

export const LotComparator = () => {
  const [cands, setCands] = useState([]);
  const [pairs, setPairs] = useState([]);
  const [a, setA] = useState('');
  const [b, setB] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/buyer-tools/compare/candidates`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => { setCands(d.items || []); setPairs(d.linked_pairs || []); })
      .catch(() => {});
  }, []);

  const compare = async (ca = a, cb = b) => {
    if (!ca || !cb) return toast.error('Sélectionnez deux consultations');
    const r = await fetch(`${API}/api/buyer-tools/compare?a=${ca}&b=${cb}`, { credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setResult(d);
  };

  const applyPair = (p) => { setA(p.a); setB(p.b); compare(p.a, p.b); };
  const dl = result?.deltas || {};

  return (
    <div className={`${panel} p-5`} data-testid="lot-comparator">
      <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
        <GitCompareArrows className="w-4 h-4 text-[#D9B35A]" /> Comparateur de lots
      </h3>
      <p className="text-[11px] text-white/40 mb-3">Comparez les résultats de deux consultations clôturées — idéal pour un lot relancé par duplication.</p>
      {pairs.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {pairs.map((p) => {
            const la = cands.find((c) => c.id === p.a); const lb = cands.find((c) => c.id === p.b);
            return (
              <button key={`${p.a}-${p.b}`} type="button" onClick={() => applyPair(p)} data-testid={`compare-pair-${p.b}`}
                className="px-2 py-1 rounded-lg text-[10px] font-bold bg-[#D9B35A]/15 text-[#E9CF8E] hover:bg-[#D9B35A]/25">
                {la?.ref} ↔ {lb?.ref} (dupliqué)
              </button>
            );
          })}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <select className={sel} style={{ colorScheme: 'dark' }} value={a} onChange={(e) => setA(e.target.value)} data-testid="compare-select-a">
          <option value="" style={{ background: '#2A1045' }}>Consultation A…</option>
          {cands.map((c) => <option key={c.id} value={c.id} style={{ background: '#2A1045' }}>{c.ref} — {c.title}</option>)}
        </select>
        <select className={sel} style={{ colorScheme: 'dark' }} value={b} onChange={(e) => setB(e.target.value)} data-testid="compare-select-b">
          <option value="" style={{ background: '#2A1045' }}>Consultation B…</option>
          {cands.map((c) => <option key={c.id} value={c.id} style={{ background: '#2A1045' }}>{c.ref} — {c.title}</option>)}
        </select>
        <button type="button" onClick={() => compare()} data-testid="compare-run-btn"
          className="px-4 py-2 rounded-xl text-xs font-bold hover:brightness-110 transition-all"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>Comparer</button>
      </div>
      {!cands.length && <p className="text-xs text-white/40">Aucune consultation clôturée à comparer pour l'instant.</p>}
      {result && (
        <div data-testid="compare-result">
          <div className="flex flex-wrap gap-3">
            <Side lot={result.a} testid="compare-side-a" />
            <Side lot={result.b} testid="compare-side-b" />
          </div>
          <div className="flex flex-wrap gap-2 mt-3 text-[11px]" data-testid="compare-deltas">
            {dl.best_offer_diff_cents != null && (
              <span className={`px-2 py-1 rounded-lg font-bold ${dl.best_offer_diff_cents <= 0 ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                Meilleure offre B vs A : {dl.best_offer_diff_cents > 0 ? '+' : ''}{(dl.best_offer_diff_cents / 100).toFixed(2).replace('.', ',')} € ({dl.best_offer_diff_pct > 0 ? '+' : ''}{dl.best_offer_diff_pct} %)
              </span>
            )}
            <span className="px-2 py-1 rounded-lg font-bold bg-white/10 text-white/70">Participation : {dl.participants_diff > 0 ? '+' : ''}{dl.participants_diff}</span>
            <span className="px-2 py-1 rounded-lg font-bold bg-white/10 text-white/70">Offres valides : {dl.valid_bids_diff > 0 ? '+' : ''}{dl.valid_bids_diff}</span>
            {result.linked_by_duplication && <span className="px-2 py-1 rounded-lg font-bold bg-[#D9B35A]/15 text-[#E9CF8E]">Liées par duplication</span>}
          </div>
        </div>
      )}
    </div>
  );
};
