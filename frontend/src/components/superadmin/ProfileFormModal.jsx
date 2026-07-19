import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const inputCls = 'w-full h-9 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';
const labelCls = 'block text-[10.5px] text-white/55 mb-1';

const EMPTY = {
  slug: '', titles: { fr: '', en: '', es: '' }, descriptions: { fr: '', en: '', es: '' },
  space_route: '/espace-acheteur', convention_template: 'v2_0_buyer', default_plan_slug: '',
  creates_vendor_record: false, active: true, sort_order: 10,
};

export const ProfileFormModal = ({ initial, templates, onClose, onSaved }) => {
  const isEdit = Boolean(initial);
  const [data, setData] = useState(initial ? { ...EMPTY, ...initial } : EMPTY);
  const [busy, setBusy] = useState(false);
  const [plans, setPlans] = useState([]);

  useEffect(() => {
    fetch(`${API}/public/plans`).then((r) => r.json()).then((d) => setPlans(d.plans || [])).catch(() => {});
  }, []);

  const save = async () => {
    if (!data.titles.fr) return toast.error('Le titre FR est requis');
    setBusy(true);
    try {
      const url = isEdit ? `${API}/admin/member-profiles/${initial.slug}` : `${API}/admin/member-profiles`;
      const body = isEdit
        ? { titles: data.titles, descriptions: data.descriptions, space_route: data.space_route, convention_template: data.convention_template, default_plan_slug: data.default_plan_slug || '', creates_vendor_record: data.creates_vendor_record, active: data.active, sort_order: data.sort_order }
        : data;
      const r = await fetch(url, {
        method: isEdit ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        credentials: 'include', body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(isEdit ? 'Profil mis à jour' : 'Profil créé');
      onSaved();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.75)' }} data-testid="profile-form-modal">
      <div className="w-full max-w-2xl rounded-[18px] p-5 max-h-[90vh] overflow-y-auto" style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white">{isEdit ? `Modifier « ${initial.titles?.fr} »` : 'Nouveau profil d\'adhésion'}</h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="grid sm:grid-cols-3 gap-3">
          {['fr', 'en', 'es'].map((l) => (
            <div key={l}><label className={labelCls}>Titre {l.toUpperCase()} {l === 'fr' ? '*' : ''}</label>
              <input className={inputCls} data-testid={`profile-title-${l}`} value={data.titles[l] || ''}
                onChange={(e) => setData({ ...data, titles: { ...data.titles, [l]: e.target.value } })} /></div>
          ))}
          {['fr', 'en', 'es'].map((l) => (
            <div key={l}><label className={labelCls}>Description {l.toUpperCase()}</label>
              <textarea rows={2} className={`${inputCls} h-auto py-1.5`} value={data.descriptions[l] || ''}
                onChange={(e) => setData({ ...data, descriptions: { ...data.descriptions, [l]: e.target.value } })} /></div>
          ))}
          <div><label className={labelCls}>Espace de destination</label>
            <input className={inputCls} data-testid="profile-space-route" value={data.space_route}
              onChange={(e) => setData({ ...data, space_route: e.target.value })} placeholder="/espace-acheteur" /></div>
          <div><label className={labelCls}>Formule pré-sélectionnée</label>
            <select className={inputCls} data-testid="profile-default-plan-select" value={data.default_plan_slug || ''} style={{ colorScheme: 'dark' }}
              onChange={(e) => setData({ ...data, default_plan_slug: e.target.value })}>
              <option value="" style={{ background: '#2A1045' }}>— Aucune —</option>
              {plans.map((p) => <option key={p.slug} value={p.slug} style={{ background: '#2A1045' }}>{p.name}</option>)}
            </select></div>
          <div><label className={labelCls}>Convention associée</label>
            <select className={inputCls} data-testid="profile-convention-select" value={data.convention_template} style={{ colorScheme: 'dark' }}
              onChange={(e) => setData({ ...data, convention_template: e.target.value })}>
              {(templates || []).map((tp) => (
                <option key={tp} value={tp} style={{ background: '#2A1045' }}>
                  {tp === 'v1_5_vendor' ? 'V1.5 — Fournisseur (vendeur)' : 'V2.0 — Achat volumes + attestation (acheteur)'}
                </option>
              ))}
            </select></div>
          <div><label className={labelCls}>Ordre d'affichage</label>
            <input type="number" className={inputCls} value={data.sort_order}
              onChange={(e) => setData({ ...data, sort_order: parseInt(e.target.value || 0, 10) })} /></div>
        </div>
        <div className="flex items-center gap-5 mt-3">
          <label className="flex items-center gap-2 text-[11px] text-white/70 cursor-pointer">
            <input type="checkbox" className="accent-[#D4AF37]" checked={data.creates_vendor_record}
              onChange={(e) => setData({ ...data, creates_vendor_record: e.target.checked })} />
            Crée une fiche vendeur (catalogue produits)
          </label>
          <label className="flex items-center gap-2 text-[11px] text-white/70 cursor-pointer">
            <input type="checkbox" className="accent-[#D4AF37]" data-testid="profile-active-checkbox" checked={data.active}
              onChange={(e) => setData({ ...data, active: e.target.checked })} />
            Actif (visible sur la page d'adhésion)
          </label>
        </div>
        <button type="button" onClick={save} disabled={busy} data-testid="profile-save-btn"
          className="mt-4 w-full py-2.5 rounded-xl text-xs font-bold disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
          {isEdit ? 'Enregistrer les modifications' : 'Créer le profil'}
        </button>
      </div>
    </div>
  );
};
