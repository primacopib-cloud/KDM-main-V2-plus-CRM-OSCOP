import { useCallback, useEffect, useState } from 'react';
import { Handshake, Plus, Power } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-9 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';
const STATUS = {
  NOUVELLE: 'bg-[#60A5FA]/15 text-[#60A5FA]', EN_COURS: 'bg-[#D9B35A]/20 text-[#E9CF8E]',
  ACCEPTEE: 'bg-emerald-500/15 text-emerald-400', REFUSEE: 'bg-red-500/15 text-red-400',
};

export const PartnerApplicationsPanel = () => {
  const [apps, setApps] = useState([]);
  const [types, setTypes] = useState([]);
  const [newType, setNewType] = useState({ code: '', label: '' });

  const load = useCallback(() => {
    fetch(`${API}/admin/partners/applications`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setApps(d.items || [])).catch(() => {});
    fetch(`${API}/admin/partners/types`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setTypes(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const setStatus = async (a, status) => {
    const r = await fetch(`${API}/admin/partners/applications/${a.id}`, {
      method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!r.ok) return toast.error('Erreur');
    toast.success(`Candidature ${status.toLowerCase().replace('_', ' ')}`);
    load();
  };

  const addType = async () => {
    if (!newType.code.trim() || !newType.label.trim()) return toast.error('Code et libellé requis');
    const r = await fetch(`${API}/admin/partners/types`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newType),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Espace « ${d.label} » ajouté au formulaire partenaire`);
    setNewType({ code: '', label: '' });
    load();
  };

  const toggleType = async (t) => {
    await fetch(`${API}/admin/partners/types/${t.id}`, { method: 'PATCH', credentials: 'include' });
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="partner-apps-panel">
      <h3 className="font-display text-lg mb-1 text-white flex items-center gap-2">
        <Handshake size={16} style={{ color: '#D9B35A' }} /> Devenir partenaire — candidatures
        <span className="text-sm font-normal text-white/50">({apps.length})</span>
      </h3>
      <p className="text-xs text-white/45 mb-4">Demandes reçues via le formulaire du pied de page. Gérez aussi les espaces proposés dans le formulaire.</p>

      <div className="flex flex-wrap items-center gap-2 mb-4 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
        {types.map((t) => (
          <button key={t.id} type="button" onClick={() => toggleType(t)} data-testid={`partner-type-${t.code}`}
            title={t.active ? 'Cliquer pour masquer du formulaire' : 'Cliquer pour réafficher'}
            className={`px-2 py-1 rounded-lg text-[10px] font-bold border inline-flex items-center gap-1 transition-colors ${t.active ? 'bg-[#D9B35A]/20 text-[#E9CF8E] border-[#D9B35A]/40' : 'bg-white/[0.04] text-white/35 border-white/10 line-through'}`}>
            <Power size={10} /> {t.label}
          </button>
        ))}
        <input value={newType.code} onChange={(e) => setNewType({ ...newType, code: e.target.value })} placeholder="CODE" data-testid="partner-type-code-input" className={`${inp} w-28`} />
        <input value={newType.label} onChange={(e) => setNewType({ ...newType, label: e.target.value })} placeholder="Libellé du nouvel espace" data-testid="partner-type-label-input" className={`${inp} flex-1 min-w-[160px]`} />
        <button type="button" onClick={addType} data-testid="partner-type-add-btn"
          className="btn-gold h-9 px-3 rounded-lg text-xs font-semibold inline-flex items-center gap-1"><Plus size={13} /> Ajouter</button>
      </div>

      <div className="space-y-2">
        {apps.map((a) => (
          <div key={a.id} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid={`partner-app-${a.id}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2 py-0.5 rounded-lg text-[9px] font-bold bg-white/10 text-white/70 uppercase">{a.type}</span>
              <p className="text-sm font-bold text-white flex-1 min-w-[140px]">{a.name}{a.company ? ` — ${a.company}` : ''}</p>
              <span className="text-xs text-white/45">{a.email}{a.phone ? ` · ${a.phone}` : ''}</span>
              <span className={`px-2 py-0.5 rounded-lg text-[9px] font-bold ${STATUS[a.status] || STATUS.NOUVELLE}`} data-testid={`partner-app-status-${a.id}`}>{a.status.replace('_', ' ')}</span>
            </div>
            {a.message && <p className="text-xs text-white/55 mt-1.5">{a.message}</p>}
            <div className="flex gap-1.5 mt-2">
              {['EN_COURS', 'ACCEPTEE', 'REFUSEE'].filter((s) => s !== a.status).map((s) => (
                <button key={s} type="button" onClick={() => setStatus(a, s)} data-testid={`partner-app-${a.id}-set-${s}`}
                  className="px-2 py-1 rounded-lg text-[10px] font-bold bg-white/[0.06] border border-white/15 text-white/70 hover:text-white transition-colors">
                  {s === 'EN_COURS' ? 'En cours' : s === 'ACCEPTEE' ? 'Accepter' : 'Refuser'}
                </button>
              ))}
            </div>
          </div>
        ))}
        {!apps.length && <p className="text-sm text-white/45 py-3">Aucune candidature pour l'instant.</p>}
      </div>
    </div>
  );
};
