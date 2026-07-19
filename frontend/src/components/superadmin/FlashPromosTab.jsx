import { useCallback, useEffect, useState } from 'react';
import { Zap, Plus, Trash2, Pencil, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });

const PLACES = [
  { k: 'landing', label: "Page d'accueil" },
  { k: 'kdmarche', label: 'Page KDMARCHÉ' },
  { k: 'member_spaces', label: 'Espaces membres' },
];

const toLocal = (iso) => (iso ? new Date(iso).toISOString().slice(0, 16) : '');

const Modal = ({ initial, onClose, onSaved }) => {
  const [f, setF] = useState(initial
    ? { ...initial, starts_at: toLocal(initial.starts_at), ends_at: toLocal(initial.ends_at) }
    : { title: '', description: '', discount_pct: 10, starts_at: toLocal(new Date().toISOString()), ends_at: '', placements: ['landing', 'kdmarche', 'member_spaces'], cta_url: '', active: true });
  const save = async () => {
    if (!f.title || !f.ends_at) return toast.error('Titre et date de fin requis');
    const body = { ...f, discount_pct: parseInt(f.discount_pct || 0, 10),
      starts_at: new Date(f.starts_at).toISOString(), ends_at: new Date(f.ends_at).toISOString() };
    const r = initial
      ? await fetch(`${API}/admin/flash-promos/${initial.id}`, jsonOpts('PUT', body))
      : await fetch(`${API}/admin/flash-promos`, jsonOpts('POST', body));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(initial ? 'Promo mise à jour' : 'Promo flash créée');
    onSaved();
  };
  const togglePlace = (k) => {
    const cur = f.placements || [];
    setF({ ...f, placements: cur.includes(k) ? cur.filter((p) => p !== k) : [...cur, k] });
  };
  const inp = 'w-full h-10 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15';
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.75)' }} data-testid="flash-promo-modal">
      <div className="w-full max-w-lg rounded-[18px] p-5 max-h-[90vh] overflow-y-auto" style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white">{initial ? 'Modifier la promo' : 'Nouvelle promo flash'}</h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-3">
          <input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Titre de la promo" data-testid="promo-title-input" className={inp} />
          <input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="Description courte (optionnel)" className={inp} />
          <div className="grid grid-cols-3 gap-2">
            <div><p className="text-[10px] text-white/50 mb-1">Remise %</p>
              <input type="number" value={f.discount_pct} onChange={(e) => setF({ ...f, discount_pct: e.target.value })} className={inp} data-testid="promo-discount-input" /></div>
            <div><p className="text-[10px] text-white/50 mb-1">Début</p>
              <input type="datetime-local" value={f.starts_at} onChange={(e) => setF({ ...f, starts_at: e.target.value })} className={inp} style={{ colorScheme: 'dark' }} /></div>
            <div><p className="text-[10px] text-white/50 mb-1">Fin (compte à rebours)</p>
              <input type="datetime-local" value={f.ends_at} onChange={(e) => setF({ ...f, ends_at: e.target.value })} className={inp} style={{ colorScheme: 'dark' }} data-testid="promo-ends-input" /></div>
          </div>
          <input value={f.cta_url || ''} onChange={(e) => setF({ ...f, cta_url: e.target.value })} placeholder="Lien du bouton « J'en profite » (optionnel)" className={inp} />
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10.5px] text-white/55">Lieux d'affichage :</span>
            {PLACES.map((p) => (
              <button key={p.k} type="button" onClick={() => togglePlace(p.k)} data-testid={`promo-place-${p.k}`}
                className={`px-2.5 py-1 rounded-full text-[10.5px] font-semibold border ${
                  (f.placements || []).includes(p.k) ? 'bg-[#D9B35A]/20 border-[#D9B35A] text-[#E9CF8E]' : 'border-white/20 text-white/55'
                }`}>{p.label}</button>
            ))}
          </div>
          <button type="button" onClick={save} data-testid="promo-save-btn"
            className="w-full py-2.5 rounded-xl text-xs font-bold"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            {initial ? 'Enregistrer' : 'Lancer la promo'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const FlashPromosTab = () => {
  const [items, setItems] = useState([]);
  const [modal, setModal] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/admin/flash-promos`, opts()).then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggle = async (p) => {
    await fetch(`${API}/admin/flash-promos/${p.id}`, jsonOpts('PUT', { active: !p.active }));
    load();
  };
  const remove = async (p) => {
    if (!window.confirm(`Supprimer « ${p.title} » ?`)) return;
    await fetch(`${API}/admin/flash-promos/${p.id}`, { method: 'DELETE', ...opts() });
    load();
  };
  const now = Date.now();

  return (
    <div className="space-y-4" data-testid="flash-promos-tab">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Zap className="w-4 h-4 text-[#D9B35A]" /> Promos flash — compte à rebours
        </h2>
        <button type="button" onClick={() => setModal('new')} data-testid="promo-create-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold"
          style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
          <Plus className="w-3.5 h-3.5" /> Nouvelle promo
        </button>
      </div>
      <div className="space-y-2">
        {!items.length && <p className="text-xs text-white/45">Aucune promo flash.</p>}
        {items.map((p) => {
          const running = p.active && new Date(p.starts_at) <= now && new Date(p.ends_at) >= now;
          const ended = new Date(p.ends_at) < now;
          return (
            <div key={p.id} className="glass-panel-soft rounded-[14px] p-3 flex flex-wrap items-center gap-3" data-testid={`promo-row-${p.id}`}>
              <div className="flex-1 min-w-[200px]">
                <p className="text-sm font-bold text-white flex items-center gap-2">
                  {p.title} {p.discount_pct ? <span className="text-[#E9CF8E]">-{p.discount_pct} %</span> : null}
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                    running ? 'bg-[#7BC94E]/15 text-[#7BC94E]' : ended ? 'bg-white/10 text-white/40' : p.active ? 'bg-[#60A5FA]/15 text-[#60A5FA]' : 'bg-red-500/15 text-red-400'
                  }`}>{running ? 'EN COURS' : ended ? 'TERMINÉE' : p.active ? 'PROGRAMMÉE' : 'MASQUÉE'}</span>
                </p>
                <p className="text-[10px] text-white/40 mt-0.5">
                  Du {String(p.starts_at).slice(0, 16).replace('T', ' ')} au {String(p.ends_at).slice(0, 16).replace('T', ' ')} ·
                  Affichage : {(p.placements || []).map((k) => (PLACES.find((x) => x.k === k) || { label: k }).label).join(' + ') || '—'}
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                <button type="button" onClick={() => toggle(p)} data-testid={`promo-toggle-${p.id}`}
                  className="px-2.5 py-1.5 rounded-lg text-[10.5px] font-bold bg-white/10 text-white/65 hover:text-white">
                  {p.active ? 'Masquer' : 'Activer'}
                </button>
                <button type="button" onClick={() => setModal(p)} className="p-1.5 rounded-lg bg-white/10 text-white/65 hover:text-[#E9CF8E]"><Pencil className="w-3.5 h-3.5" /></button>
                <button type="button" onClick={() => remove(p)} className="p-1.5 rounded-lg bg-white/10 text-white/65 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
          );
        })}
      </div>
      {modal && <Modal initial={modal === 'new' ? null : modal} onClose={() => setModal(null)} onSaved={() => { setModal(null); load(); }} />}
    </div>
  );
};
