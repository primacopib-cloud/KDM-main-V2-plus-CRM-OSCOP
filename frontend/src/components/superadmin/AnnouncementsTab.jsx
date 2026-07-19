import { useCallback, useEffect, useState } from 'react';
import { Megaphone, Plus, Trash2, Pencil, Eye, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });

const AUDIENCES = [
  { k: 'all', label: 'Tous les espaces' }, { k: 'vendor', label: 'Vendeurs Pro' },
  { k: 'buyer', label: 'Acheteurs Pro' }, { k: 'cooper', label: "COOPER'S" },
];

const Modal = ({ initial, onClose, onSaved }) => {
  const [f, setF] = useState(initial || { title: '', body: '', priority: 'normale', audiences: ['all'], active: true });
  const save = async () => {
    if (!f.title || !f.body) return toast.error('Titre et contenu requis');
    const r = initial
      ? await fetch(`${API}/admin/announcements/${initial.id}`, jsonOpts('PUT', f))
      : await fetch(`${API}/admin/announcements`, jsonOpts('POST', f));
    if (!r.ok) return toast.error('Erreur');
    toast.success(initial ? 'Annonce mise à jour' : 'Annonce publiée');
    onSaved();
  };
  const toggleAud = (k) => {
    if (k === 'all') return setF({ ...f, audiences: ['all'] });
    let next = (f.audiences || []).filter((a) => a !== 'all');
    next = next.includes(k) ? next.filter((a) => a !== k) : [...next, k];
    setF({ ...f, audiences: next.length ? next : ['all'] });
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.75)' }} data-testid="announcement-modal">
      <div className="w-full max-w-lg rounded-[18px] p-5" style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white">{initial ? 'Modifier l\'annonce' : 'Nouvelle annonce'}</h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-3">
          <input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Titre"
            data-testid="announcement-title-input" className="w-full h-10 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15" />
          <textarea rows={4} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} placeholder="Contenu de l'annonce…"
            data-testid="announcement-body-input" className="w-full rounded-lg px-2.5 py-2 text-xs text-white bg-white/[0.05] border border-white/15" />
          <div className="flex items-center gap-3">
            <span className="text-[10.5px] text-white/55">Priorité :</span>
            {['normale', 'urgente'].map((p) => (
              <button key={p} type="button" onClick={() => setF({ ...f, priority: p })}
                className={`px-2.5 py-1 rounded-full text-[10.5px] font-bold border ${
                  f.priority === p ? (p === 'urgente' ? 'bg-[#E64432]/20 border-[#E64432] text-[#E64432]' : 'bg-[#D9B35A]/20 border-[#D9B35A] text-[#E9CF8E]') : 'border-white/20 text-white/55'
                }`}>{p === 'urgente' ? 'Urgente' : 'Normale'}</button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10.5px] text-white/55">Audience :</span>
            {AUDIENCES.map((a) => (
              <button key={a.k} type="button" onClick={() => toggleAud(a.k)}
                className={`px-2.5 py-1 rounded-full text-[10.5px] font-semibold border ${
                  (f.audiences || []).includes(a.k) ? 'bg-[#D9B35A]/20 border-[#D9B35A] text-[#E9CF8E]' : 'border-white/20 text-white/55'
                }`}>{a.label}</button>
            ))}
          </div>
          <button type="button" onClick={save} data-testid="announcement-save-btn"
            className="w-full py-2.5 rounded-xl text-xs font-bold"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            {initial ? 'Enregistrer' : 'Publier l\'annonce'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const AnnouncementsTab = () => {
  const [items, setItems] = useState([]);
  const [modal, setModal] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/admin/announcements`, opts()).then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggle = async (a) => {
    await fetch(`${API}/admin/announcements/${a.id}`, jsonOpts('PUT', { active: !a.active }));
    load();
  };
  const remove = async (a) => {
    if (!window.confirm(`Supprimer « ${a.title} » ?`)) return;
    await fetch(`${API}/admin/announcements/${a.id}`, { method: 'DELETE', ...opts() });
    load();
  };

  return (
    <div className="space-y-4" data-testid="announcements-tab">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Megaphone className="w-4 h-4 text-[#D9B35A]" /> Annonces &amp; Communications
        </h2>
        <button type="button" onClick={() => setModal('new')} data-testid="announcement-create-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold"
          style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
          <Plus className="w-3.5 h-3.5" /> Nouvelle annonce
        </button>
      </div>
      <div className="space-y-2">
        {!items.length && <p className="text-xs text-white/45">Aucune annonce publiée.</p>}
        {items.map((a) => (
          <div key={a.id} className="glass-panel-soft rounded-[14px] p-3 flex flex-wrap items-center gap-3" data-testid={`announcement-row-${a.id}`}>
            <div className="flex-1 min-w-[200px]">
              <p className="text-sm font-bold text-white flex items-center gap-2">
                {a.title}
                {a.priority === 'urgente' && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#E64432]/20 text-[#E64432]">URGENTE</span>}
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${a.active ? 'bg-[#7BC94E]/15 text-[#7BC94E]' : 'bg-white/10 text-white/45'}`}>
                  {a.active ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </p>
              <p className="text-[10.5px] text-white/45 mt-0.5 line-clamp-1">{a.body}</p>
              <p className="text-[10px] text-white/35 mt-0.5 flex items-center gap-1">
                <Eye className="w-3 h-3" /> {a.views || 0} vue(s) · {(a.audiences || ['all']).join(', ')} · {String(a.created_at).slice(0, 10)}
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              <button type="button" onClick={() => toggle(a)} className="px-2.5 py-1.5 rounded-lg text-[10.5px] font-bold bg-white/10 text-white/65 hover:text-white" data-testid={`announcement-toggle-${a.id}`}>
                {a.active ? 'Masquer' : 'Publier'}
              </button>
              <button type="button" onClick={() => setModal(a)} className="p-1.5 rounded-lg bg-white/10 text-white/65 hover:text-[#E9CF8E]"><Pencil className="w-3.5 h-3.5" /></button>
              <button type="button" onClick={() => remove(a)} className="p-1.5 rounded-lg bg-white/10 text-white/65 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          </div>
        ))}
      </div>
      {modal && <Modal initial={modal === 'new' ? null : modal} onClose={() => setModal(null)} onSaved={() => { setModal(null); load(); }} />}
    </div>
  );
};
