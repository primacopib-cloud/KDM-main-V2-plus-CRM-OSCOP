import { useEffect, useState } from 'react';
import { BookOpenCheck, RefreshCw, Search } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const VeilleArchiveCard = () => {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState(null);

  const load = (query = q) => {
    setBusy(true);
    fetch(`${API}/oracle-admin/veille-digests${query ? `?q=${encodeURIComponent(query)}` : ''}`,
      { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setItems(d?.digests || []))
      .catch(() => {})
      .finally(() => setBusy(false));
  };
  useEffect(() => load(''), []);

  return (
    <div className="rounded-2xl border border-[#D9B35A]/25 bg-white/[0.02] p-4 mt-4" data-testid="veille-archive-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-[#E9CF8E] flex items-center gap-2">
          <BookOpenCheck size={15} /> Veilles réglementaires archivées
        </h3>
        <button type="button" onClick={() => load()} data-testid="veille-archive-refresh"
          className="p-1.5 rounded-lg text-white/40 hover:text-[#E9CF8E] transition-colors">
          <RefreshCw size={13} className={busy ? 'animate-spin' : ''} />
        </button>
      </div>
      <div className="flex items-center gap-2 mb-3">
        <div className="relative flex-1">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/35" />
          <input value={q} onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && load()}
            placeholder="Rechercher par thème (octroi de mer, bouclier qualité-prix…)"
            data-testid="veille-archive-search"
            className="w-full h-8 pl-7 pr-2 rounded-lg bg-white/[0.05] border border-white/15 text-[11px] text-white/85 placeholder:text-white/30 outline-none focus:border-[#D9B35A]/50" />
        </div>
        <button type="button" onClick={() => load()} data-testid="veille-archive-search-btn"
          className="h-8 px-3 rounded-lg text-[10.5px] font-bold text-[#2A1045] gold-chip"
          style={{ background: 'linear-gradient(90deg, #E9CF8E, #D9B35A)' }}>
          Rechercher
        </button>
      </div>
      {items.length === 0 ? (
        <p className="text-[11px] text-white/40" data-testid="veille-archive-empty">
          {q ? 'Aucune note ne mentionne ce thème.' : 'Aucune note de veille archivée pour le moment — la première partira lundi 7h (ou demandez une veille à Oracle).'}
        </p>
      ) : (
        <div className="space-y-1.5 max-h-80 overflow-y-auto">
          {items.map((d) => (
            <div key={d.id} className="rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2"
              data-testid={`veille-digest-row-${d.id}`}>
              <button type="button" onClick={() => setOpenId(openId === d.id ? null : d.id)}
                data-testid={`veille-digest-toggle-${d.id}`}
                className="w-full flex items-center gap-2 text-left">
                <span className="text-[11px] font-semibold text-white/80">{d.week}</span>
                <span className="px-2 py-0.5 rounded-full text-[9px] font-bold text-emerald-300 bg-emerald-500/15 border border-emerald-400/40">
                  {d.sent} email(s)
                </span>
                <span className="ml-auto text-[9.5px] text-white/35">
                  {new Date(d.created_at).toLocaleString('fr-FR')} · {openId === d.id ? 'Replier ▲' : 'Lire ▼'}
                </span>
              </button>
              {openId === d.id ? (
                <p className="text-[10.5px] text-white/65 mt-2 whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                  {d.note}
                </p>
              ) : (
                <p className="text-[10px] text-white/40 mt-0.5 line-clamp-2">{(d.note || '').slice(0, 180)}…</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
