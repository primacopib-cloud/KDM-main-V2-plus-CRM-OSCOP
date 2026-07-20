import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { CalendarClock, Plus, Trash2, Power } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const EMPTY = { unit: 'days', quantity: '', price_credits: '' };
const UNITS = [['hours', 'Heure(s)'], ['days', 'Jour(s)'], ['months', 'Mois']];

export const DiffusionGridPanel = () => {
  const [options, setOptions] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    const r = await fetch(`${API}/admin/diffusion-grid`, { credentials: 'include' });
    if (r.ok) setOptions((await r.json()).options || []);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const create = async () => {
    if (!form.quantity || !form.price_credits) { toast.error('Durée et prix requis'); return; }
    setSaving(true);
    try {
      const r = await fetch(`${API}/admin/diffusion-grid`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ unit: form.unit, quantity: parseInt(form.quantity, 10), price_credits: parseInt(form.price_credits, 10) }),
      });
      const d = await r.json();
      if (r.ok) { toast.success(`Option "${d.option.label}" créée`); setForm(EMPTY); refresh(); }
      else toast.error(d.detail || 'Erreur');
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (o) => {
    await fetch(`${API}/admin/diffusion-grid/${o.id}`, {
      method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: !o.active }),
    });
    toast.success(o.active ? 'Option désactivée' : 'Option activée');
    refresh();
  };

  const remove = async (o) => {
    if (!window.confirm(`Supprimer l'option "${o.label}" ?`)) return;
    await fetch(`${API}/admin/diffusion-grid/${o.id}`, { method: 'DELETE', credentials: 'include' });
    toast.success('Option supprimée');
    refresh();
  };

  const inputCls = 'h-9 px-2.5 rounded-lg text-xs border border-white/15 bg-white min-w-0';

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="diffusion-grid-panel">
      <h3 className="font-display text-lg text-white flex items-center gap-2 mb-1">
        <CalendarClock size={15} className="text-[#E9CF8E]" /> Grille de diffusion des spots
      </h3>
      <p className="text-[11px] opacity-50 mb-3">
        Paramètres de diffusion en galerie : durée d&apos;affichage et prix en crédits coopératifs (cc),
        soumis au vendeur pour paiement. Sans option active, la galerie reste libre.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
        <input type="number" min="1" placeholder="Durée" value={form.quantity}
          onChange={(e) => setForm({ ...form, quantity: e.target.value })}
          data-testid="grid-quantity" className={inputCls} />
        <select value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })}
          data-testid="grid-unit" className={inputCls}>
          {UNITS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <input type="number" min="1" placeholder="Prix (cc)" value={form.price_credits}
          onChange={(e) => setForm({ ...form, price_credits: e.target.value })}
          data-testid="grid-price" className={inputCls} />
        <button type="button" onClick={create} disabled={saving} data-testid="grid-create-btn"
          className="btn-gold h-9 rounded-lg text-xs font-semibold inline-flex items-center justify-center gap-1.5 disabled:opacity-40">
          <Plus size={12} /> Ajouter
        </button>
      </div>
      <div className="divide-y divide-white/[0.06]">
        {options.map((o) => (
          <div key={o.id} className="flex items-center justify-between py-2" data-testid={`grid-option-${o.id}`}>
            <div>
              <p className="text-sm font-medium text-white">
                {o.label} — <span className="text-[#E9CF8E] font-bold">{o.price_credits} cc</span>
              </p>
              <p className="text-[10px] uppercase tracking-wide opacity-45">{o.active ? 'Active' : 'Inactive'}</p>
            </div>
            <div className="flex gap-1.5">
              <button type="button" onClick={() => toggle(o)} data-testid={`grid-toggle-${o.id}`}
                title={o.active ? 'Désactiver' : 'Activer'}
                className={`p-2 rounded-lg border ${o.active ? 'border-emerald-300 text-emerald-600' : 'border-white/15 text-gray-400'}`}>
                <Power size={13} />
              </button>
              <button type="button" onClick={() => remove(o)} data-testid={`grid-delete-${o.id}`}
                className="p-2 rounded-lg border border-white/15 text-red-500 hover:border-red-300">
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
        {options.length === 0 && <p className="text-sm opacity-50 py-2">Aucune option — la galerie est en diffusion libre.</p>}
      </div>
    </div>
  );
};
