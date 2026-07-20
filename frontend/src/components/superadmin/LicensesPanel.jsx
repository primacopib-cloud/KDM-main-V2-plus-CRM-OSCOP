import { useCallback, useEffect, useRef, useState } from 'react';
import { Building2, Plus, Trash2, Eye, EyeOff, Upload, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';
const resolveLogo = (url) => (url && url.startsWith('/api/') ? `${process.env.REACT_APP_BACKEND_URL}${url}` : url);

const EMPTY = { name: '', slug: '', territory_code: '', tagline: '', contact_email: '', primary_color: '#5B2E8C', accent_color: '#D9B35A', logo_url: '', custom_domain: '' };

export const LicensesPanel = () => {
  const [items, setItems] = useState([]);
  const [territories, setTerritories] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const fileRefs = useRef({});

  const load = useCallback(() => {
    fetch(`${API}/admin/licenses`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
    fetch(`${API}/admin/territories`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setTerritories(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.name.trim()) return toast.error('Nom requis');
    if (!form.territory_code) return toast.error('Choisissez un territoire');
    const r = await fetch(`${API}/admin/licenses`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Licence « ${d.name} » créée — vitrine : /t/${d.slug}`);
    setForm(EMPTY);
    load();
  };

  const patch = async (id, body, msg) => {
    const r = await fetch(`${API}/admin/licenses/${id}`, {
      method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    if (msg) toast.success(msg);
    load();
  };

  const remove = async (l) => {
    if (!window.confirm(`Supprimer la licence « ${l.name} » ? La page /t/${l.slug} ne sera plus accessible.`)) return;
    const r = await fetch(`${API}/admin/licenses/${l.id}`, { method: 'DELETE', credentials: 'include' });
    if (!r.ok) return toast.error('Suppression impossible');
    toast.success(`Licence ${l.name} supprimée`);
    load();
  };

  const uploadLogo = async (l, file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch(`${API}/admin/licenses/${l.id}/logo`, { method: 'POST', credentials: 'include', body: fd });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Upload impossible');
    toast.success(`Logo de ${l.name} mis à jour`);
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="licenses-panel">
      <h3 className="font-display text-lg mb-1 text-white flex items-center gap-2">
        <Building2 size={16} style={{ color: '#D9B35A' }} /> Marque Blanche — Licences territoriales
        <span className="text-sm font-normal text-white/50">({items.length})</span>
      </h3>
      <p className="text-xs text-white/45 mb-4">Chaque licence dispose d'une page vitrine à ses couleurs (ex : <code className="text-[#D9B35A]">/t/guadeloupe</code>) rattachée à un territoire. Les données restent partagées sur la plateforme.</p>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 mb-3">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nom de la licence (ex : KDMARCHÉ Guadeloupe)" data-testid="license-name-input" className={inp} />
        <input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })}
          placeholder="Slug URL (optionnel, auto)" data-testid="license-slug-input" className={inp} />
        <select value={form.territory_code} onChange={(e) => setForm({ ...form, territory_code: e.target.value })}
          data-testid="license-territory-select" className={inp}>
          <option value="">— Territoire —</option>
          {territories.map((t) => <option key={t.code} value={t.code}>{t.name} ({t.code})</option>)}
        </select>
        <input value={form.tagline} onChange={(e) => setForm({ ...form, tagline: e.target.value })}
          placeholder="Slogan (optionnel)" className={inp} />
        <input value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
          placeholder="Email de contact" className={inp} />
        <input value={form.custom_domain} onChange={(e) => setForm({ ...form, custom_domain: e.target.value })}
          placeholder="Domaine personnalisé (ex : kdmarche-gp.fr)" data-testid="license-domain-input" className={inp} />
        <div className="flex items-center gap-3">
          <label className="text-xs text-white/50 flex items-center gap-1.5">Primaire
            <input type="color" value={form.primary_color} onChange={(e) => setForm({ ...form, primary_color: e.target.value })}
              className="h-8 w-10 rounded cursor-pointer bg-transparent border border-white/15" data-testid="license-primary-color" />
          </label>
          <label className="text-xs text-white/50 flex items-center gap-1.5">Accent
            <input type="color" value={form.accent_color} onChange={(e) => setForm({ ...form, accent_color: e.target.value })}
              className="h-8 w-10 rounded cursor-pointer bg-transparent border border-white/15" data-testid="license-accent-color" />
          </label>
        </div>
      </div>
      <button onClick={create} data-testid="license-create-btn"
        className="h-10 px-4 rounded-lg text-sm font-semibold text-[#1A092D] inline-flex items-center gap-1.5 mb-2"
        style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
        <Plus size={14} /> Créer la licence
      </button>
      <p className="text-[11px] text-white/40 mb-5">
        Domaine personnalisé : faites pointer le domaine (CNAME) vers votre déploiement Emergent, puis rattachez-le
        au déploiement via Deploy &gt; Custom Domain. La plateforme détecte automatiquement le domaine et affiche la vitrine de la licence.
      </p>

      <div className="space-y-2">
        {items.map((l) => (
          <div key={l.id} className="flex items-center gap-3 p-2.5 rounded-xl bg-white/[0.04] border border-white/10" data-testid={`license-row-${l.id}`}>
            <div className="h-12 w-12 rounded-lg bg-white flex items-center justify-center p-1 flex-shrink-0"
              style={{ border: `2px solid ${l.accent_color || '#D9B35A'}` }}>
              {l.logo_url
                ? <img src={resolveLogo(l.logo_url)} alt={l.name} className="max-h-full max-w-full object-contain" />
                : <span className="text-lg font-bold" style={{ color: l.primary_color || '#5B2E8C' }}>{l.name.charAt(0)}</span>}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white font-medium truncate">{l.name}
                {!l.is_active && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/50">INACTIVE</span>}
              </p>
              <p className="text-[11px] text-white/40 truncate">
                {l.territory_name} ({l.territory_code}) · <code>/t/{l.slug}</code>
                {l.custom_domain && <code className="ml-2 px-1.5 py-0.5 rounded bg-emerald-400/10 text-emerald-300" data-testid={`license-domain-badge-${l.id}`}>{l.custom_domain}</code>}
                <span className="inline-block w-2.5 h-2.5 rounded-full ml-2 align-middle" style={{ background: l.primary_color }} />
                <span className="inline-block w-2.5 h-2.5 rounded-full ml-1 align-middle" style={{ background: l.accent_color }} />
              </p>
            </div>
            <a href={`/t/${l.slug}`} target="_blank" rel="noreferrer" title="Voir la vitrine" data-testid={`license-preview-${l.id}`}
              className="p-2 rounded-lg hover:bg-white/10 text-[#D9B35A]"><ExternalLink size={14} /></a>
            <input type="file" accept="image/*" className="hidden" ref={(el) => { fileRefs.current[l.id] = el; }}
              onChange={(e) => uploadLogo(l, e.target.files[0])} />
            <button onClick={() => fileRefs.current[l.id]?.click()} title="Uploader le logo"
              className="p-2 rounded-lg hover:bg-white/10 text-white/60"><Upload size={14} /></button>
            <button onClick={() => patch(l.id, { is_active: !l.is_active }, l.is_active ? `${l.name} désactivée` : `${l.name} activée`)}
              title={l.is_active ? 'Désactiver' : 'Activer'} data-testid={`license-toggle-${l.id}`}
              className="p-2 rounded-lg hover:bg-white/10 text-white/60">
              {l.is_active ? <Eye size={14} className="text-emerald-400" /> : <EyeOff size={14} />}
            </button>
            <button onClick={() => remove(l)} title="Supprimer" data-testid={`license-delete-${l.id}`}
              className="p-2 rounded-lg hover:bg-red-500/15 text-red-400"><Trash2 size={14} /></button>
          </div>
        ))}
        {!items.length && <p className="text-sm text-white/40 py-4 text-center">Aucune licence — créez la première marque blanche territoriale.</p>}
      </div>
    </div>
  );
};
