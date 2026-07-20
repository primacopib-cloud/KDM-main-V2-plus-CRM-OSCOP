import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Layers, Percent, Plus, Trash2, Loader2 } from 'lucide-react';
import { TerritoriesPanel } from './TerritoriesPanel';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inputCls = 'h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';

const Panel = ({ icon: Icon, title, items, renderLabel, onAdd, onDelete, addForm, testId }) => (
  <div className="glass-panel-soft rounded-[18px] p-5" data-testid={testId}>
    <h3 className="font-display text-lg mb-3 text-white flex items-center gap-2">
      <Icon size={16} style={{ color: '#D9B35A' }} /> {title}
      <span className="text-sm font-normal text-white/50">({items.length})</span>
    </h3>
    <div className="flex gap-2 mb-4">{addForm}</div>
    <div className="divide-y divide-white/[0.06]">
      {items.map((it) => (
        <div key={it.id} className="flex items-center justify-between gap-2 py-2" data-testid={`${testId}-item-${it.id}`}>
          <span className="text-sm text-white/85">{renderLabel(it)}</span>
          <div className="flex items-center gap-2">
            {it.builtin && <span className="text-[9px] uppercase font-bold px-2 py-0.5 rounded-full bg-[#D9B35A]/15 text-[#E9CF8E] border border-[#D9B35A]/30">standard</span>}
            <button
              type="button"
              onClick={() => onDelete(it)}
              data-testid={`${testId}-delete-${it.id}`}
              className="p-1.5 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 hover:bg-red-500/20 transition-colors"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      ))}
    </div>
  </div>
);

export const TaxonomyTab = () => {
  const [categories, setCategories] = useState([]);
  const [rates, setRates] = useState([]);
  const [newCat, setNewCat] = useState('');
  const [newRate, setNewRate] = useState({ value: '', label: '' });
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [cR, rR] = await Promise.all([
      fetch(`${API}/taxonomy/categories`),
      fetch(`${API}/taxonomy/tva-rates`),
    ]);
    if (cR.ok) setCategories((await cR.json()).categories || []);
    if (rR.ok) setRates((await rR.json()).rates || []);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const post = async (url, body, okMsg) => {
    setBusy(true);
    try {
      const r = await fetch(`${API}${url}`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      if (r.ok) { toast.success(okMsg); refresh(); return true; }
      toast.error(typeof data.detail === 'string' ? data.detail : 'ERROR');
      return false;
    } finally { setBusy(false); }
  };

  const del = async (url, okMsg) => {
    const r = await fetch(`${API}${url}`, { method: 'DELETE', credentials: 'include' });
    if (r.ok) { toast.success(okMsg); refresh(); }
    else toast.error('Suppression impossible');
  };

  return (
    <div className="space-y-6" data-testid="taxonomy-tab">
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Layers className="w-5 h-5 text-[#D9B35A]" /> Catégories & Taxes
        </h2>
        <p className="text-sm text-white/55 mt-1">Ajoutez ou supprimez instantanément une catégorie produit, un taux de TVA ou un territoire — appliqués immédiatement.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Panel
          icon={Layers} title="Catégories produits" items={categories} testId="taxonomy-categories"
          renderLabel={(c) => c.label}
          onDelete={(c) => window.confirm(`Supprimer la catégorie "${c.label}" ?`) && del(`/taxonomy/categories/${c.id}`, 'Catégorie supprimée')}
          addForm={(
            <>
              <input value={newCat} onChange={(e) => setNewCat(e.target.value)} placeholder="Nouvelle catégorie…"
                data-testid="taxonomy-new-category-input" className={`${inputCls} flex-1`} />
              <button
                type="button" disabled={!newCat.trim() || busy}
                onClick={async () => { if (await post('/taxonomy/categories', { label: newCat.trim() }, 'Catégorie ajoutée')) setNewCat(''); }}
                data-testid="taxonomy-add-category-btn"
                className="btn-gold h-10 px-4 rounded-lg text-sm font-semibold inline-flex items-center gap-1.5 disabled:opacity-40"
              >
                {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Ajouter
              </button>
            </>
          )}
        />
        <Panel
          icon={Percent} title="Taux de TVA" items={rates} testId="taxonomy-rates"
          renderLabel={(r) => `${r.value}% — ${r.label}`}
          onDelete={(r) => window.confirm(`Supprimer le taux ${r.value}% ?`) && del(`/taxonomy/tva-rates/${r.id}`, 'Taux supprimé')}
          addForm={(
            <>
              <input value={newRate.value} type="number" step="0.1" min="0" max="100"
                onChange={(e) => setNewRate({ ...newRate, value: e.target.value })} placeholder="%"
                data-testid="taxonomy-new-rate-value" className={`${inputCls} w-20`} />
              <input value={newRate.label} onChange={(e) => setNewRate({ ...newRate, label: e.target.value })}
                placeholder="Libellé (ex : Taux spécial)" data-testid="taxonomy-new-rate-label" className={`${inputCls} flex-1`} />
              <button
                type="button" disabled={newRate.value === '' || busy}
                onClick={async () => {
                  if (await post('/taxonomy/tva-rates', { value: parseFloat(newRate.value), label: newRate.label.trim() }, 'Taux ajouté')) setNewRate({ value: '', label: '' });
                }}
                data-testid="taxonomy-add-rate-btn"
                className="btn-gold h-10 px-4 rounded-lg text-sm font-semibold inline-flex items-center gap-1.5 disabled:opacity-40"
              >
                <Plus size={14} /> Ajouter
              </button>
            </>
          )}
        />
      </div>

      <TerritoriesPanel />
    </div>
  );
};
