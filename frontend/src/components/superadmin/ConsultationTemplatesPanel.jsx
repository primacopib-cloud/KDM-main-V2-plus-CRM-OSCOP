import { useCallback, useEffect, useState } from 'react';
import { LayoutTemplate, Plus, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });
const inp = 'w-full h-9 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15';

const TemplateModal = ({ onClose, onSaved }) => {
  const [f, setF] = useState({ name: '', title: '', type: 'STANDARD', procedure: 'SCELLEE', category: '', products: '', territories: 'GUADELOUPE', specs: '', duration_days: 7 });
  const save = async () => {
    if (!f.name || !f.title || !f.category) return toast.error('Nom, titre et catégorie requis');
    const body = {
      ...f,
      duration_days: parseInt(f.duration_days, 10) || 7,
      products: f.products.split('\n').filter(Boolean).map((l) => ({ label: l.trim() })),
      territories: f.territories.split(',').map((t) => t.trim()).filter(Boolean),
    };
    const r = await fetch(`${API}/admin/consultation-templates`, jsonOpts('POST', body));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Modèle « ${d.name} » enregistré`);
    onSaved();
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.75)' }} data-testid="template-modal">
      <div className="w-full max-w-lg rounded-[18px] p-5 max-h-[90vh] overflow-y-auto" style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white">Nouveau modèle de consultation</h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-2.5">
          <input className={inp} placeholder="Nom du modèle (interne)" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="tpl-name-input" />
          <input className={inp} placeholder="Titre du lot pré-rempli" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} data-testid="tpl-title-input" />
          <div className="grid grid-cols-2 gap-2">
            <select className={inp} value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}>
              <option value="STANDARD">Standard</option>
              <option value="INTERTERRITORIALE">Interterritoriale</option>
            </select>
            <select className={inp} value={f.procedure} onChange={(e) => setF({ ...f, procedure: e.target.value })}>
              <option value="SCELLEE">Offres scellées</option>
              <option value="ENCHERE_INVERSEE">Enchère inversée</option>
            </select>
          </div>
          <input className={inp} placeholder="Catégorie (matrice juridique)" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} data-testid="tpl-category-input" />
          <textarea className={`${inp} h-14 py-2`} placeholder="Produits (un par ligne)" value={f.products} onChange={(e) => setF({ ...f, products: e.target.value })} />
          <div className="grid grid-cols-2 gap-2">
            <input className={inp} placeholder="Territoires (virgules)" value={f.territories} onChange={(e) => setF({ ...f, territories: e.target.value })} />
            <input className={inp} type="number" placeholder="Durée (jours)" value={f.duration_days} onChange={(e) => setF({ ...f, duration_days: e.target.value })} />
          </div>
          <textarea className={`${inp} h-14 py-2`} placeholder="Cahier des charges pré-rempli" value={f.specs} onChange={(e) => setF({ ...f, specs: e.target.value })} />
          <button type="button" onClick={save} className="w-full py-2.5 rounded-xl text-xs font-bold" style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }} data-testid="tpl-save-btn">
            Enregistrer le modèle
          </button>
        </div>
      </div>
    </div>
  );
};

export const ConsultationTemplatesPanel = ({ onCreated }) => {
  const [items, setItems] = useState([]);
  const [modal, setModal] = useState(false);

  const load = useCallback(() => {
    fetch(`${API}/admin/consultation-templates`, opts()).then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const instantiate = async (t) => {
    const r = await fetch(`${API}/admin/consultation-templates/${t.id}/instantiate`, { method: 'POST', ...opts() });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Lot ${d.ref} créé en brouillon depuis « ${t.name} » (${d.legal_status} — ${d.procedure})`);
    onCreated?.();
  };

  const remove = async (t) => {
    if (!window.confirm(`Désactiver le modèle « ${t.name} » ?`)) return;
    await fetch(`${API}/admin/consultation-templates/${t.id}`, { method: 'DELETE', ...opts() });
    load();
  };

  const setRecurrence = async (t, interval) => {
    const r = await fetch(`${API}/admin/consultation-templates/${t.id}/recurrence`, jsonOpts('POST', { interval }));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(interval === 'none'
      ? `« ${t.name} » : récurrence désactivée`
      : `« ${t.name} » : un lot sera recréé automatiquement chaque ${interval === 'monthly' ? 'mois' : 'trimestre'}`);
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[14px] p-4" data-testid="consultation-templates-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-white/70 uppercase flex items-center gap-1.5">
          <LayoutTemplate className="w-3.5 h-3.5" /> Modèles de consultations (création en 1 clic)
        </h3>
        <button type="button" onClick={() => setModal(true)} data-testid="tpl-create-btn"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold bg-white/10 text-white/70 hover:text-white">
          <Plus className="w-3 h-3" /> Nouveau modèle
        </button>
      </div>
      <div className="space-y-1.5">
        {!items.length && <p className="text-xs text-white/40">Aucun modèle.</p>}
        {items.map((t) => (
          <div key={t.id} className="flex flex-wrap items-center gap-2 text-xs py-1.5 border-b border-white/5 last:border-0" data-testid={`tpl-row-${t.id}`}>
            <span className="flex-1 min-w-[180px] text-white/85 font-semibold">{t.name}</span>
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/50">{t.procedure === 'SCELLEE' ? 'SCELLÉE' : 'ENCHÈRE'}</span>
            <span className="text-white/40">{t.category} · {t.duration_days} j · {t.type}</span>
            <button type="button" onClick={() => instantiate(t)} data-testid={`tpl-instantiate-${t.id}`}
              className="px-2.5 py-1 rounded-lg text-[10px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
              Créer un lot
            </button>
            <select value={t.recurrence?.interval || 'none'} data-testid={`tpl-recurrence-${t.id}`}
              onChange={(e) => setRecurrence(t, e.target.value)} style={{ colorScheme: 'dark' }}
              className="h-6 rounded-lg px-1.5 text-[10px] text-white/70 bg-white/[0.05] border border-white/15">
              <option value="none" style={{ background: '#2A1045' }}>Ponctuel</option>
              <option value="monthly" style={{ background: '#2A1045' }}>Récurrent · mensuel</option>
              <option value="quarterly" style={{ background: '#2A1045' }}>Récurrent · trimestriel</option>
            </select>
            <button type="button" onClick={() => remove(t)} className="p-1 rounded bg-white/5 text-white/40 hover:text-red-400" data-testid={`tpl-delete-${t.id}`}>
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
      {modal && <TemplateModal onClose={() => setModal(false)} onSaved={() => { setModal(false); load(); }} />}
    </div>
  );
};
