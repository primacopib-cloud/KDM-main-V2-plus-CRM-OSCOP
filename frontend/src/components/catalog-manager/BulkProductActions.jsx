import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Eye, FileEdit, Store, Truck, Tag, Trash2, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const btnCls = 'h-8 px-2.5 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 border transition-colors disabled:opacity-40';

export const BulkProductActions = ({ selected, setSelected, allIds, onDone }) => {
  const [busy, setBusy] = useState(false);
  const [catDialogOpen, setCatDialogOpen] = useState(false);
  const [categories, setCategories] = useState([]);
  const [cat, setCat] = useState('');
  const [sub, setSub] = useState('');

  useEffect(() => {
    if (!catDialogOpen) return;
    fetch(`${API_URL}/api/taxonomy/categories`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setCategories(d.categories || []))
      .catch(() => {});
  }, [catDialogOpen]);

  const run = async (action, extra = {}, okMsg) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/catalog/admin/products/bulk-action`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_ids: selected, action, ...extra }),
      });
      const d = await res.json();
      if (!res.ok) { toast.error(d.detail || 'Action échouée'); return; }
      toast.success(`${okMsg} : ${d.affected} produit(s)`);
      setSelected([]);
      onDone();
    } finally { setBusy(false); }
  };

  const allSelected = allIds.length > 0 && selected.length === allIds.length;
  const subs = (categories.find((c) => c.value === cat)?.subcategories) || [];

  return (
    <div className="flex flex-wrap items-center gap-2 p-3 rounded-xl bg-white/[0.03] border border-white/[0.08]" data-testid="bulk-product-actions">
      <label className="flex items-center gap-2 text-xs text-white/70 cursor-pointer select-none">
        <input type="checkbox" checked={allSelected} data-testid="product-select-all"
          onChange={() => setSelected(allSelected ? [] : allIds)}
          className="w-4 h-4 accent-[#D9B35A] cursor-pointer" />
        Tout sélectionner
      </label>
      <span className="text-xs text-white/45" data-testid="bulk-selected-count">{selected.length} sélectionné(s)</span>
      {selected.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 ml-auto">
          {busy && <Loader2 size={14} className="animate-spin text-[#D9B35A]" />}
          <button type="button" disabled={busy} data-testid="bulk-publish-btn"
            onClick={() => run('publish', {}, 'Affichés au catalogue')}
            className={`${btnCls} bg-emerald-500/15 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/25`}>
            <Eye size={13} /> Afficher
          </button>
          <button type="button" disabled={busy} data-testid="bulk-draft-btn"
            onClick={() => run('draft', {}, 'Passés en brouillon')}
            className={`${btnCls} bg-white/10 text-white/75 border-white/15 hover:bg-white/15`}>
            <FileEdit size={13} /> Brouillon
          </button>
          <button type="button" disabled={busy} data-testid="bulk-pro-on-btn"
            onClick={() => run('pro_on', {}, 'Ajoutés au catalogue pro')}
            className={`${btnCls} bg-[#5B9BD5]/15 text-[#8fc1ec] border-[#5B9BD5]/30 hover:bg-[#5B9BD5]/25`}>
            <Store size={13} /> + Cat. pro
          </button>
          <button type="button" disabled={busy} data-testid="bulk-pro-off-btn"
            onClick={() => run('pro_off', {}, 'Retirés du catalogue pro')}
            className={`${btnCls} bg-white/[0.05] text-white/55 border-white/15 hover:bg-white/10`}>
            <Store size={13} /> − Cat. pro
          </button>
          <button type="button" disabled={busy} data-testid="bulk-lolo-on-btn"
            onClick={() => run('lolodrive_on', {}, 'Ajoutés au catalogue LOLODRIVE')}
            className={`${btnCls} bg-[#8CC63E]/15 text-[#b5e07a] border-[#8CC63E]/30 hover:bg-[#8CC63E]/25`}>
            <Truck size={13} /> + LOLODRIVE
          </button>
          <button type="button" disabled={busy} data-testid="bulk-lolo-off-btn"
            onClick={() => run('lolodrive_off', {}, 'Retirés du catalogue LOLODRIVE')}
            className={`${btnCls} bg-white/[0.05] text-white/55 border-white/15 hover:bg-white/10`}>
            <Truck size={13} /> − LOLODRIVE
          </button>
          <button type="button" disabled={busy} data-testid="bulk-category-btn"
            onClick={() => setCatDialogOpen(true)}
            className={`${btnCls} bg-[#D9B35A]/15 text-[#E9CF8E] border-[#D9B35A]/35 hover:bg-[#D9B35A]/25`}>
            <Tag size={13} /> Catégorie…
          </button>
          <button type="button" disabled={busy} data-testid="bulk-delete-btn"
            onClick={() => window.confirm(`Supprimer définitivement ${selected.length} produit(s) ?`) && run('delete', {}, 'Supprimés')}
            className={`${btnCls} bg-red-500/15 text-red-300 border-red-500/30 hover:bg-red-500/25`}>
            <Trash2 size={13} /> Supprimer
          </button>
        </div>
      )}

      <Dialog open={catDialogOpen} onOpenChange={setCatDialogOpen}>
        <DialogContent className="max-w-sm bg-[#2A1045] border-white/15 text-white" data-testid="bulk-category-dialog">
          <DialogHeader>
            <DialogTitle className="text-base">Attribuer une catégorie ({selected.length} produit(s))</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-white/70 text-xs">Catégorie *</Label>
              <Select value={cat || undefined} onValueChange={(v) => { setCat(v); setSub(''); }}>
                <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10" data-testid="bulk-category-select">
                  <SelectValue placeholder="Choisir…" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((c) => <SelectItem key={c.id} value={c.value}>{c.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-white/70 text-xs">Sous-catégorie</Label>
              <Select value={sub || '__none__'} disabled={!cat} onValueChange={(v) => setSub(v === '__none__' ? '' : v)}>
                <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10" data-testid="bulk-subcategory-select">
                  <SelectValue placeholder="Aucune" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">— Aucune —</SelectItem>
                  {subs.map((s) => <SelectItem key={s.id} value={s.label}>{s.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setCatDialogOpen(false)} className="text-white/60">Annuler</Button>
            <Button disabled={!cat || busy} data-testid="bulk-category-apply"
              onClick={async () => { await run('set_category', { category: cat, subcategory: sub }, 'Catégorie attribuée'); setCatDialogOpen(false); }}
              className="bg-[#D9B35A] text-black hover:bg-[#c5a04b] font-semibold">
              Appliquer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
