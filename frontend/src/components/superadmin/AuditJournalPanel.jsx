import { useCallback, useEffect, useState } from 'react';
import { ScrollText, ShieldCheck, Search, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-9 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';

const TYPE_COLOR = (t) => {
  if (t.startsWith('TERRITORY')) return 'bg-[#60A5FA]/15 text-[#60A5FA]';
  if (t.startsWith('CAMPAIGN')) return 'bg-[#D9B35A]/20 text-[#E9CF8E]';
  return 'bg-[#C9A8F0]/15 text-[#C9A8F0]';
};

export const AuditJournalPanel = () => {
  const [items, setItems] = useState([]);
  const [types, setTypes] = useState([]);
  const [filter, setFilter] = useState('');
  const [q, setQ] = useState('');
  const [chain, setChain] = useState(null);

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (filter) params.set('event_type', filter);
    if (q) params.set('q', q);
    fetch(`${API}/admin/audit?${params}`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => { setItems(d.items || []); setTypes(d.event_types || []); })
      .catch(() => {});
  }, [filter, q]);
  useEffect(() => { load(); }, [load]);

  const verify = async () => {
    const r = await fetch(`${API}/admin/audit/verify`, { credentials: 'include' });
    const d = await r.json();
    setChain(d);
    d.valid ? toast.success(`Chaîne d'audit intègre (${d.entries_verified} entrées vérifiées)`) : toast.error(`Chaîne corrompue au seq ${d.broken_at_seq}`);
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="audit-journal-panel">
      <div className="flex flex-wrap items-center gap-2 mb-1">
        <h3 className="font-display text-lg text-white flex items-center gap-2 flex-1">
          <ScrollText size={16} style={{ color: '#D9B35A' }} /> Journal d'audit
          <span className="text-sm font-normal text-white/50">({items.length})</span>
        </h3>
        <button type="button" onClick={verify} data-testid="audit-verify-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/[0.06] border border-white/15 text-white/70 hover:text-white transition-colors">
          <ShieldCheck size={13} /> Vérifier l'intégrité
        </button>
      </div>
      <p className="text-xs text-white/45 mb-3">Traçabilité inviolable (chaînage SHA-256) : territoires, campagnes, consultations, attributions.</p>
      {chain && (
        <p className={`text-xs font-bold mb-2 ${chain.valid ? 'text-emerald-400' : 'text-red-400'}`} data-testid="audit-chain-status">
          {chain.valid ? '✓ Chaîne intègre' : `✗ Chaîne corrompue (seq ${chain.broken_at_seq})`}
        </p>
      )}
      <div className="flex flex-wrap gap-2 mb-3">
        <select className={inp} style={{ colorScheme: 'dark' }} value={filter} onChange={(e) => setFilter(e.target.value)} data-testid="audit-type-filter">
          <option value="" style={{ background: '#2A1045' }}>Tous les événements</option>
          {types.map((t) => <option key={t} value={t} style={{ background: '#2A1045' }}>{t}</option>)}
        </select>
        <div className="relative flex-1 min-w-[180px]">
          <Search size={13} className="absolute left-3 top-3 text-white/40" />
          <input className={`${inp} pl-8 w-full`} placeholder="Acteur, référence…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="audit-search-input" />
        </div>
        <button type="button" onClick={load} data-testid="audit-refresh-btn"
          className="p-2 rounded-lg bg-white/[0.06] border border-white/15 text-white/70 hover:text-white transition-colors"><RefreshCw size={14} /></button>
      </div>
      <div className="space-y-1 max-h-[420px] overflow-y-auto pr-1">
        {items.map((e) => (
          <div key={e.seq} className="flex flex-wrap items-start gap-2 p-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-[11px]" data-testid={`audit-entry-${e.seq}`}>
            <span className="text-white/35 font-mono w-10">#{e.seq}</span>
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${TYPE_COLOR(e.event_type)}`}>{e.event_type}</span>
            <span className="text-white/70">{String(e.ts).slice(0, 16).replace('T', ' ')}</span>
            <span className="text-white/50">{e.actor || '—'}</span>
            <span className="flex-1 min-w-[160px] text-white/45 break-all">
              {e.consultation_id ? `cons:${e.consultation_id.slice(0, 8)} ` : ''}
              {e.payload && Object.keys(e.payload).length > 0 && JSON.stringify(e.payload).slice(0, 140)}
            </span>
          </div>
        ))}
        {!items.length && <p className="text-sm text-white/45 py-3">Aucune entrée pour ces filtres.</p>}
      </div>
    </div>
  );
};
