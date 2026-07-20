import { useCallback, useEffect, useRef, useState } from 'react';
import { Images, Plus, Trash2, Eye, EyeOff, ArrowUp, ArrowDown, Upload, Pencil } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';
const resolveLogo = (url) => (url && url.startsWith('/api/') ? `${process.env.REACT_APP_BACKEND_URL}${url}` : url);

export const ShowcasePartnersPanel = () => {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ name: '', link: '', logo_url: '', category: 'vendor' });
  const fileRefs = useRef({});

  const load = useCallback(() => {
    fetch(`${API}/admin/showcase/partners`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!form.name.trim()) return toast.error('Nom requis');
    const r = await fetch(`${API}/admin/showcase/partners`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`${d.name} ajouté à la vitrine`);
    setForm({ name: '', link: '', logo_url: '', category: 'vendor' });
    load();
  };

  const patch = async (id, body, msg) => {
    const r = await fetch(`${API}/admin/showcase/partners/${id}`, {
      method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    if (msg) toast.success(msg);
    load();
  };

  const move = async (id, direction) => {
    await fetch(`${API}/admin/showcase/partners/${id}/move?direction=${direction}`, { method: 'POST', credentials: 'include' });
    load();
  };

  const remove = async (p) => {
    if (!window.confirm(`Retirer « ${p.name} » de la vitrine ?`)) return;
    const r = await fetch(`${API}/admin/showcase/partners/${p.id}`, { method: 'DELETE', credentials: 'include' });
    if (!r.ok) return toast.error('Suppression impossible');
    toast.success(`${p.name} supprimé`);
    load();
  };

  const uploadLogo = async (p, file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch(`${API}/admin/showcase/partners/${p.id}/logo`, { method: 'POST', credentials: 'include', body: fd });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Upload impossible');
    toast.success(`Logo de ${p.name} mis à jour`);
    load();
  };

  const rename = (p) => {
    const name = window.prompt('Nouveau nom :', p.name);
    if (name && name.trim() && name !== p.name) patch(p.id, { name: name.trim() }, 'Nom mis à jour');
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="showcase-partners-panel">
      <h3 className="font-display text-lg mb-1 text-white flex items-center gap-2">
        <Images size={16} style={{ color: '#D9B35A' }} /> Partenaires en vitrine
        <span className="text-sm font-normal text-white/50">({items.length})</span>
      </h3>
      <p className="text-xs text-white/45 mb-4">Carrousel de logos affiché sur la page d'accueil. Ajoutez un logo par URL ou par upload après création.</p>

      <div className="flex flex-wrap gap-2 mb-5">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nom du partenaire" data-testid="showcase-name-input" className={`${inp} w-48`} />
        <input value={form.link} onChange={(e) => setForm({ ...form, link: e.target.value })}
          placeholder="Lien (optionnel)" data-testid="showcase-link-input" className={`${inp} w-52`} />
        <input value={form.logo_url} onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
          placeholder="URL du logo (optionnel)" data-testid="showcase-logo-url-input" className={`${inp} w-56`} />
        <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className={`${inp} w-40`}>
          <option value="vendor">Vendeur</option>
          <option value="logistics">Opérateur logistique</option>
          <option value="institution">Institution</option>
        </select>
        <button onClick={add} data-testid="showcase-add-btn"
          className="h-10 px-4 rounded-lg text-sm font-semibold text-[#1A092D] inline-flex items-center gap-1.5"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
          <Plus size={14} /> Ajouter
        </button>
      </div>

      <div className="space-y-2">
        {items.map((p, idx) => (
          <div key={p.id} className="flex items-center gap-3 p-2.5 rounded-xl bg-white/[0.04] border border-white/10" data-testid={`showcase-row-${p.id}`}>
            <div className="h-12 w-12 rounded-lg bg-white flex items-center justify-center p-1 flex-shrink-0">
              {p.logo_url
                ? <img src={resolveLogo(p.logo_url)} alt={p.name} className="max-h-full max-w-full object-contain" />
                : <span className="text-lg font-bold text-[#5B2E8C]">{p.name.charAt(0)}</span>}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white font-medium truncate">{p.name}
                {!p.is_active && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white/50">MASQUÉ</span>}
              </p>
              <p className="text-[11px] text-white/40 truncate">{p.category === 'logistics' ? 'Opérateur logistique' : p.category === 'institution' ? 'Institution' : 'Vendeur'}{p.link ? ` · ${p.link}` : ''}</p>
            </div>
            <input type="file" accept="image/*" className="hidden" ref={(el) => { fileRefs.current[p.id] = el; }}
              onChange={(e) => uploadLogo(p, e.target.files[0])} />
            <button onClick={() => fileRefs.current[p.id]?.click()} title="Uploader un logo" data-testid={`showcase-upload-${p.id}`}
              className="p-2 rounded-lg hover:bg-white/10 text-white/60"><Upload size={14} /></button>
            <button onClick={() => rename(p)} title="Renommer" className="p-2 rounded-lg hover:bg-white/10 text-white/60"><Pencil size={14} /></button>
            <button onClick={() => move(p.id, 'up')} disabled={idx === 0} title="Monter"
              className="p-2 rounded-lg hover:bg-white/10 text-white/60 disabled:opacity-25"><ArrowUp size={14} /></button>
            <button onClick={() => move(p.id, 'down')} disabled={idx === items.length - 1} title="Descendre"
              className="p-2 rounded-lg hover:bg-white/10 text-white/60 disabled:opacity-25"><ArrowDown size={14} /></button>
            <button onClick={() => patch(p.id, { is_active: !p.is_active }, p.is_active ? `${p.name} masqué` : `${p.name} affiché`)}
              title={p.is_active ? 'Masquer' : 'Afficher'} data-testid={`showcase-toggle-${p.id}`}
              className="p-2 rounded-lg hover:bg-white/10 text-white/60">
              {p.is_active ? <Eye size={14} className="text-emerald-400" /> : <EyeOff size={14} />}
            </button>
            <button onClick={() => remove(p)} title="Supprimer" data-testid={`showcase-delete-${p.id}`}
              className="p-2 rounded-lg hover:bg-red-500/15 text-red-400"><Trash2 size={14} /></button>
          </div>
        ))}
        {!items.length && <p className="text-sm text-white/40 py-4 text-center">Aucun partenaire en vitrine — ajoutez le premier logo ci-dessus.</p>}
      </div>
    </div>
  );
};
