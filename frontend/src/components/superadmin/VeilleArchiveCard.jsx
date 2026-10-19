import { useEffect, useState } from 'react';
import { BookOpenCheck, RefreshCw, Search } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const VeilleArchiveCard = () => {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState(null);
  const [themes, setThemes] = useState([]);
  const [newTheme, setNewTheme] = useState('');
  const [savingThemes, setSavingThemes] = useState(false);

  const loadThemes = () => {
    fetch(`${API}/oracle-admin/veille-themes`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setThemes(d?.themes || []))
      .catch(() => {});
  };
  const saveThemes = (next) => {
    setSavingThemes(true);
    fetch(`${API}/oracle-admin/veille-themes`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ themes: next }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d?.themes) setThemes(d.themes); })
      .catch(() => {})
      .finally(() => setSavingThemes(false));
  };
  const addTheme = () => {
    const t = newTheme.trim();
    if (!t || themes.includes(t) || themes.length >= 10) return;
    setNewTheme('');
    saveThemes([...themes, t]);
  };
  const removeTheme = (t) => {
    if (themes.length <= 1) return;
    saveThemes(themes.filter((x) => x !== t));
  };
  useEffect(loadThemes, []);

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
      <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-2.5 mb-3" data-testid="veille-themes-editor">
        <p className="text-[10px] font-bold uppercase tracking-wider text-[#E9CF8E]/70 mb-1.5">
          Thèmes suivis par la veille hebdo (lundi 7h) {savingThemes && '· enregistrement…'}
        </p>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {themes.map((t) => (
            <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold text-white/80 bg-[#D9B35A]/15 border border-[#D9B35A]/35"
              data-testid={`veille-theme-chip-${t.replace(/\s+/g, '-')}`}>
              {t}
              <button type="button" onClick={() => removeTheme(t)} disabled={themes.length <= 1 || savingThemes}
                data-testid={`veille-theme-remove-${t.replace(/\s+/g, '-')}`}
                className="text-white/40 hover:text-red-300 disabled:opacity-30 transition-colors">×</button>
            </span>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <input value={newTheme} onChange={(e) => setNewTheme(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTheme()}
            placeholder="Ajouter un thème (transport, prix carburant, Egalim…)"
            data-testid="veille-theme-input"
            className="flex-1 h-7 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-[10.5px] text-white/85 placeholder:text-white/30 outline-none focus:border-[#D9B35A]/50" />
          <button type="button" onClick={addTheme} disabled={!newTheme.trim() || savingThemes}
            data-testid="veille-theme-add"
            className="h-7 px-2.5 rounded-lg text-[10px] font-bold text-[#E9CF8E] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/15 disabled:opacity-40 transition-colors">
            Ajouter
          </button>
        </div>
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
