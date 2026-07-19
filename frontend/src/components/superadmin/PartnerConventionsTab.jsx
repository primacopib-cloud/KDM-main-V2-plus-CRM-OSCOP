import { useCallback, useEffect, useState } from 'react';
import { Handshake, Plus, Trash2, Pencil, Send, Download, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });

const TYPES = [{ k: 'COOPER', label: "COOPER'S" }, { k: 'EXPERT', label: 'EXPERTS' }, { k: 'PARTNER', label: 'Partenaires' }];
const STATUS_UI = {
  DRAFT: { label: 'Brouillon', c: '#9CA3AF' }, SENT: { label: 'Envoyée pour signature', c: '#60A5FA' },
  SIGNED: { label: 'Signée', c: '#E9CF8E' }, ACTIVE: { label: 'Active', c: '#7BC94E' }, SUSPENDED: { label: 'Suspendue', c: '#E64432' },
};

const Modal = ({ initial, onClose, onSaved }) => {
  const [f, setF] = useState(initial || { title: '', partner_type: 'PARTNER', partner_name: '', partner_email: '', content: '' });
  const inp = 'w-full h-10 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15';
  const save = async () => {
    if (!f.title || !f.partner_name || !f.partner_email || !f.content) return toast.error('Tous les champs sont requis');
    const r = initial
      ? await fetch(`${API}/admin/partner-conventions/${initial.id}`, jsonOpts('PUT', f))
      : await fetch(`${API}/admin/partner-conventions`, jsonOpts('POST', f));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(initial ? 'Convention mise à jour' : 'Convention rédigée (brouillon)');
    onSaved();
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.75)' }} data-testid="partner-convention-modal">
      <div className="w-full max-w-2xl rounded-[18px] p-5 max-h-[90vh] overflow-y-auto" style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white">{initial ? 'Modifier la convention' : 'Rédiger une convention de partenariat'}</h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-3">
          <input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Titre de la convention" data-testid="pconv-title-input" className={inp} />
          <div className="grid sm:grid-cols-3 gap-2">
            <select value={f.partner_type} onChange={(e) => setF({ ...f, partner_type: e.target.value })} className={inp} style={{ colorScheme: 'dark' }} data-testid="pconv-type-select">
              {TYPES.map((tp) => <option key={tp.k} value={tp.k} style={{ background: '#2A1045' }}>{tp.label}</option>)}
            </select>
            <input value={f.partner_name} onChange={(e) => setF({ ...f, partner_name: e.target.value })} placeholder="Nom du partenaire" data-testid="pconv-name-input" className={inp} />
            <input type="email" value={f.partner_email} onChange={(e) => setF({ ...f, partner_email: e.target.value })} placeholder="Email du partenaire" data-testid="pconv-email-input" className={inp} />
          </div>
          <textarea rows={10} value={f.content} onChange={(e) => setF({ ...f, content: e.target.value })}
            placeholder={"Texte de la convention (articles, engagements, durée…)\nUn paragraphe par ligne."}
            data-testid="pconv-content-input" className="w-full rounded-lg px-2.5 py-2 text-xs text-white bg-white/[0.05] border border-white/15" />
          <button type="button" onClick={save} data-testid="pconv-save-btn"
            className="w-full py-2.5 rounded-xl text-xs font-bold"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            {initial ? 'Enregistrer' : 'Enregistrer le brouillon'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const PartnerConventionsTab = () => {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({});
  const [modal, setModal] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/admin/partner-conventions`, opts()).then((r) => r.json())
      .then((d) => { setItems(d.items || []); setStats(d.stats || {}); }).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const sendForSign = async (c) => {
    const r = await fetch(`${API}/admin/partner-conventions/${c.id}/send`, { method: 'POST', ...opts() });
    if (!r.ok) return toast.error("Échec de l'envoi");
    toast.success(`Lien de signature envoyé à ${c.partner_email}`);
    load();
  };
  const setStatus = async (c, status) => {
    await fetch(`${API}/admin/partner-conventions/${c.id}`, jsonOpts('PUT', { status }));
    load();
  };
  const remove = async (c) => {
    if (!window.confirm(`Supprimer « ${c.title} » ?`)) return;
    const r = await fetch(`${API}/admin/partner-conventions/${c.id}`, { method: 'DELETE', ...opts() });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail);
    load();
  };

  return (
    <div className="space-y-4" data-testid="partner-conventions-tab">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Handshake className="w-4 h-4 text-[#D9B35A]" /> Conventions de partenariat
        </h2>
        <button type="button" onClick={() => setModal('new')} data-testid="pconv-create-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold"
          style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
          <Plus className="w-3.5 h-3.5" /> Rédiger une convention
        </button>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2" data-testid="pconv-stats">
        {[["COOPER'S actifs", stats.COOPER], ['EXPERTS actifs', stats.EXPERT], ['Partenaires actifs', stats.PARTNER],
          ['En attente de signature', stats.pending], ['Suspendues', stats.suspended]].map(([lbl, v]) => (
          <div key={lbl} className="glass-panel-soft rounded-[12px] p-2.5 text-center">
            <p className="text-lg font-bold text-[#E9CF8E]">{v || 0}</p>
            <p className="text-[9.5px] text-white/50">{lbl}</p>
          </div>
        ))}
      </div>
      <div className="space-y-2">
        {!items.length && <p className="text-xs text-white/45">Aucune convention de partenariat.</p>}
        {items.map((c) => {
          const st = STATUS_UI[c.status] || STATUS_UI.DRAFT;
          return (
            <div key={c.id} className="glass-panel-soft rounded-[14px] p-3 flex flex-wrap items-center gap-3" data-testid={`pconv-row-${c.id}`}>
              <div className="flex-1 min-w-[220px]">
                <p className="text-sm font-bold text-white flex items-center gap-2">
                  {c.title}
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ color: st.c, background: `${st.c}20` }}>{st.label}</span>
                </p>
                <p className="text-[10.5px] text-white/45 mt-0.5">
                  {(TYPES.find((tp) => tp.k === c.partner_type) || {}).label} · {c.partner_name} ({c.partner_email})
                  {c.signature ? ` · signée par ${c.signature.nom} — code ${c.signature.verification_code}` : ''}
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                {(c.status === 'DRAFT' || c.status === 'SENT') && (
                  <button type="button" onClick={() => sendForSign(c)} data-testid={`pconv-send-${c.id}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10.5px] font-bold"
                    style={{ background: 'rgba(217,179,90,0.15)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.4)' }}>
                    <Send className="w-3 h-3" /> {c.status === 'SENT' ? 'Renvoyer' : 'Envoyer pour signature'}
                  </button>
                )}
                {c.status === 'SIGNED' && (
                  <button type="button" onClick={() => setStatus(c, 'ACTIVE')} data-testid={`pconv-activate-${c.id}`}
                    className="px-2.5 py-1.5 rounded-lg text-[10.5px] font-bold bg-[#7BC94E]/15 text-[#7BC94E]">Activer</button>
                )}
                {c.status === 'ACTIVE' && (
                  <button type="button" onClick={() => setStatus(c, 'SUSPENDED')} className="px-2.5 py-1.5 rounded-lg text-[10.5px] font-bold bg-[#E64432]/15 text-[#E64432]">Suspendre</button>
                )}
                {c.status === 'SUSPENDED' && (
                  <button type="button" onClick={() => setStatus(c, 'ACTIVE')} className="px-2.5 py-1.5 rounded-lg text-[10.5px] font-bold bg-[#7BC94E]/15 text-[#7BC94E]">Réactiver</button>
                )}
                <a href={`${API}/admin/partner-conventions/${c.id}/pdf`} target="_blank" rel="noreferrer"
                  className="p-1.5 rounded-lg bg-white/10 text-white/65 hover:text-[#E9CF8E]" title="PDF"><Download className="w-3.5 h-3.5" /></a>
                {c.status === 'DRAFT' && (
                  <button type="button" onClick={() => setModal(c)} className="p-1.5 rounded-lg bg-white/10 text-white/65 hover:text-[#E9CF8E]"><Pencil className="w-3.5 h-3.5" /></button>
                )}
                {(c.status === 'DRAFT' || c.status === 'SENT' || c.status === 'SUSPENDED') && (
                  <button type="button" onClick={() => remove(c)} className="p-1.5 rounded-lg bg-white/10 text-white/65 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {modal && <Modal initial={modal === 'new' ? null : modal} onClose={() => setModal(null)} onSaved={() => { setModal(null); load(); }} />}
    </div>
  );
};
