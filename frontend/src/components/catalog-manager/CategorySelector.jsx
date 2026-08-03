import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Plus, Trash2, Check, X } from 'lucide-react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import { API, getAuthHeaders } from '../../services/http';

const NONE = '__none__';
const iconBtn = 'h-9 w-9 shrink-0 inline-flex items-center justify-center rounded-lg border transition-colors';

const InlineAdd = ({ placeholder, onSubmit, onCancel, testId }) => {
  const [val, setVal] = useState('');
  return (
    <div className="flex gap-1.5 mt-1">
      <Input autoFocus value={val} onChange={(e) => setVal(e.target.value)} placeholder={placeholder}
        onKeyDown={(e) => e.key === 'Enter' && val.trim() && onSubmit(val.trim())}
        data-testid={`${testId}-input`} className="bg-white/[0.04] border-white/10 text-white text-sm h-9" />
      <button type="button" disabled={!val.trim()} onClick={() => onSubmit(val.trim())} data-testid={`${testId}-confirm`}
        className={`${iconBtn} bg-[#D9B35A]/15 border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/25 disabled:opacity-40`}>
        <Check size={14} />
      </button>
      <button type="button" onClick={onCancel} data-testid={`${testId}-cancel`}
        className={`${iconBtn} bg-white/[0.04] border-white/10 text-white/50 hover:bg-white/10`}>
        <X size={14} />
      </button>
    </div>
  );
};

export const CategorySelector = ({ formData, handleChange }) => {
  const [categories, setCategories] = useState([]);
  const [addingCat, setAddingCat] = useState(false);
  const [addingSub, setAddingSub] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch(`${API}/taxonomy/categories`);
      if (r.ok) setCategories((await r.json()).categories || []);
    } catch { /* silencieux */ }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const call = async (url, method, body) => {
    const r = await fetch(`${API}${url}`, {
      method, credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) { toast.error(typeof data.detail === 'string' ? data.detail : 'Erreur'); return null; }
    return data;
  };

  const selectedCat = categories.find((c) => c.value === formData.category);
  const subs = selectedCat?.subcategories || [];
  const legacySub = formData.subcategory && !subs.some((s) => s.label === formData.subcategory);

  const addCategory = async (label) => {
    const data = await call('/taxonomy/categories', 'POST', { label });
    if (!data) return;
    toast.success(`Catégorie « ${label} » créée`);
    setAddingCat(false);
    await refresh();
    handleChange('category', data.category.value);
  };

  const deleteCategory = async () => {
    if (!selectedCat) return;
    if (!window.confirm(`Supprimer la catégorie « ${selectedCat.label} » ?`)) return;
    if (await call(`/taxonomy/categories/${selectedCat.id}`, 'DELETE')) {
      toast.success('Catégorie supprimée');
      handleChange('category', '');
      handleChange('subcategory', '');
      refresh();
    }
  };

  const addSubcategory = async (label) => {
    const data = await call(`/taxonomy/categories/${selectedCat.id}/subcategories`, 'POST', { label });
    if (!data) return;
    toast.success(`Sous-catégorie « ${label} » créée`);
    setAddingSub(false);
    await refresh();
    handleChange('subcategory', label);
  };

  const deleteSubcategory = async () => {
    const sub = subs.find((s) => s.label === formData.subcategory);
    if (!sub) return;
    if (!window.confirm(`Supprimer la sous-catégorie « ${sub.label} » ?`)) return;
    if (await call(`/taxonomy/categories/${selectedCat.id}/subcategories/${sub.id}`, 'DELETE')) {
      toast.success('Sous-catégorie supprimée');
      handleChange('subcategory', '');
      refresh();
    }
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      <div data-testid="category-selector">
        <Label className="text-white/70 text-xs">Catégorie *</Label>
        <div className="flex gap-1.5 mt-1">
          <Select value={formData.category || undefined} onValueChange={(v) => { handleChange('category', v); handleChange('subcategory', ''); }}>
            <SelectTrigger className="bg-white/[0.04] border-white/10 h-9" data-testid="category-select-trigger">
              <SelectValue placeholder="Choisir…" />
            </SelectTrigger>
            <SelectContent>
              {categories.map((c) => (
                <SelectItem key={c.id} value={c.value} data-testid={`category-option-${c.value}`}>{c.label}</SelectItem>
              ))}
              {formData.category && !selectedCat && (
                <SelectItem value={formData.category}>{formData.category}</SelectItem>
              )}
            </SelectContent>
          </Select>
          <button type="button" onClick={() => setAddingCat((v) => !v)} title="Créer une catégorie" data-testid="add-category-btn"
            className={`${iconBtn} bg-[#D9B35A]/15 border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/25`}>
            <Plus size={14} />
          </button>
          <button type="button" onClick={deleteCategory} disabled={!selectedCat} title="Supprimer la catégorie sélectionnée"
            data-testid="delete-category-btn"
            className={`${iconBtn} bg-red-500/10 border-red-500/25 text-red-400 hover:bg-red-500/20 disabled:opacity-30`}>
            <Trash2 size={14} />
          </button>
        </div>
        {addingCat && (
          <InlineAdd placeholder="Nouvelle catégorie…" onSubmit={addCategory} onCancel={() => setAddingCat(false)} testId="new-category" />
        )}
      </div>

      <div data-testid="subcategory-selector">
        <Label className="text-white/70 text-xs">Sous-catégorie</Label>
        <div className="flex gap-1.5 mt-1">
          <Select value={formData.subcategory || NONE} disabled={!selectedCat && !legacySub}
            onValueChange={(v) => handleChange('subcategory', v === NONE ? '' : v)}>
            <SelectTrigger className="bg-white/[0.04] border-white/10 h-9" data-testid="subcategory-select-trigger">
              <SelectValue placeholder="Aucune" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>— Aucune —</SelectItem>
              {subs.map((s) => (
                <SelectItem key={s.id} value={s.label} data-testid={`subcategory-option-${s.id}`}>{s.label}</SelectItem>
              ))}
              {legacySub && <SelectItem value={formData.subcategory}>{formData.subcategory}</SelectItem>}
            </SelectContent>
          </Select>
          <button type="button" onClick={() => setAddingSub((v) => !v)} disabled={!selectedCat} title="Créer une sous-catégorie"
            data-testid="add-subcategory-btn"
            className={`${iconBtn} bg-[#D9B35A]/15 border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/25 disabled:opacity-30`}>
            <Plus size={14} />
          </button>
          <button type="button" onClick={deleteSubcategory} disabled={!subs.some((s) => s.label === formData.subcategory)}
            title="Supprimer la sous-catégorie sélectionnée" data-testid="delete-subcategory-btn"
            className={`${iconBtn} bg-red-500/10 border-red-500/25 text-red-400 hover:bg-red-500/20 disabled:opacity-30`}>
            <Trash2 size={14} />
          </button>
        </div>
        {addingSub && selectedCat && (
          <InlineAdd placeholder={`Sous-catégorie de ${selectedCat.label}…`} onSubmit={addSubcategory}
            onCancel={() => setAddingSub(false)} testId="new-subcategory" />
        )}
      </div>
    </div>
  );
};
