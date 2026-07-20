import { useCallback, useEffect, useState } from 'react';
import { Globe2, Plus, Trash2, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';

export const TerritoriesPanel = () => {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ code: '', name: '' });

  const load = useCallback(() => {
    fetch(`${API}/admin/territories`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!form.code.trim() || !form.name.trim()) return toast.error('Code et nom requis');
    const r = await fetch(`${API}/admin/territories`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Territoire ${d.code} ajouté`);
    setForm({ code: '', name: '' });
    load();
  };

  const toggle = async (z) => {
    const r = await fetch(`${API}/admin/territories/${z.code}`, {
      method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: !z.is_active }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(z.is_active ? `${z.name} masqué du sélecteur acheteur` : `${z.name} réaffiché`);
    load();
  };

  const remove = async (z) => {
    if (!window.confirm(`Supprimer définitivement le territoire « ${z.name} » (${z.code}) ?`)) return;
    const r = await fetch(`${API}/admin/territories/${z.code}`, { method: 'DELETE', credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Suppression impossible');
    toast.success(`Territoire ${z.code} supprimé`);
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="territories-panel">
      <h3 className="font-display text-lg mb-1 text-white flex items-center gap-2">
        <Globe2 size={16} style={{ color: '#D9B35A' }} /> Territoires
        <span className="text-sm font-normal text-white/50">({items.length})</span>
      </h3>
      <p className="text-xs text-white/45 mb-4">Zones proposées aux acheteurs (catalogue, commandes). Masquer retire le territoire du sélecteur sans toucher aux données existantes.</p>
      <div className="flex flex-wrap gap-2 mb-4">
        <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })}
          placeholder="CODE (ex : ST_MARTIN)" data-testid="territory-code-input" className={`${inp} w-44 uppercase`} />
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nom affiché (ex : Saint-Martin)" data-testid="territory-name-input" className={`${inp} flex-1 min-w-[180px]`} />
        <button type="button" onClick={add} data-testid="territory-add-btn"
          className="btn-gold h-10 px-4 rounded-lg text-sm font-semibold inline-flex items-center gap-1.5">
          <Plus size={14} /> Ajouter
        </button>
      </div>
      <div className="divide-y divide-white/[0.06]">
        {items.map((z) => (
          <div key={z.code} className={`flex flex-wrap items-center gap-2 py-2.5 ${z.is_active ? '' : 'opacity-60'}`} data-testid={`territory-row-${z.code}`}>
            <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-[#D9B35A]/20 text-[#E9CF8E] border border-[#D9B35A]/30">{z.code}</span>
            <span className="text-sm font-medium text-white flex-1 min-w-[120px]">{z.name}</span>
            <span className="text-[11px] text-white/45">{z.orders_count} commande(s)</span>
            {!z.is_active && <span className="px-2 py-0.5 rounded-lg text-[9px] font-bold bg-white/10 text-white/60 uppercase" data-testid={`territory-hidden-${z.code}`}>Masqué</span>}
            <button type="button" onClick={() => toggle(z)} data-testid={`territory-toggle-${z.code}`}
              title={z.is_active ? 'Masquer du sélecteur' : 'Réafficher'}
              className="p-1.5 rounded-lg bg-white/[0.06] border border-white/15 text-white/70 hover:text-white transition-colors">
              {z.is_active ? <Eye size={14} /> : <EyeOff size={14} />}
            </button>
            <button type="button" onClick={() => remove(z)} data-testid={`territory-delete-${z.code}`}
              title="Supprimer définitivement"
              className="p-1.5 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 hover:bg-red-500/20 transition-colors">
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
