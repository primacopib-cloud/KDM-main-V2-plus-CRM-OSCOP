import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Layers, Plus, Trash2, Save } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { lolodriveAPI } from '../../services/api';

// Super admin : liste fixe des catégories → sous-catégories des catalogues LOLODRIVE
export const LolodriveCategoriesPanel = () => {
  const [cats, setCats] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [newCat, setNewCat] = useState({ name: '', subs: '' });

  const load = () => lolodriveAPI.lolodriveCategories()
    .then((d) => { setCats(d.categories || []); setDrafts({}); }).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async (c) => {
    const d = drafts[c.id] || {};
    try {
      await lolodriveAPI.adminUpdateCategory(c.id, {
        name: d.name ?? c.name,
        subcategories: (d.subs ?? c.subcategories.join(', ')).split(',').map((s) => s.trim()).filter(Boolean),
      });
      toast.success('Catégorie mise à jour ✓');
      load();
    } catch (e) { toast.error(e.message); }
  };

  const remove = async (c) => {
    if (!window.confirm(`Supprimer la catégorie « ${c.name} » ?`)) return;
    try { await lolodriveAPI.adminDeleteCategory(c.id); toast.success('Catégorie supprimée ✓'); load(); }
    catch (e) { toast.error(e.message); }
  };

  const create = async () => {
    if (!newCat.name.trim()) return toast.error('Nom de catégorie requis');
    try {
      await lolodriveAPI.adminCreateCategory({
        name: newCat.name.trim(),
        subcategories: newCat.subs.split(',').map((s) => s.trim()).filter(Boolean),
      });
      toast.success('Catégorie créée ✓');
      setNewCat({ name: '', subs: '' });
      load();
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="categories-admin-panel">
      <div className="font-semibold flex items-center gap-2 mb-3">
        <Layers className="w-4 h-4 text-[#D9B35A]" /> Catégories & sous-catégories des catalogues
      </div>
      <div className="space-y-2">
        {cats.map((c) => (
          <div key={c.id} className="flex flex-wrap items-center gap-2 p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06]" data-testid={`category-row-${c.name}`}>
            <Input value={drafts[c.id]?.name ?? c.name}
              onChange={(e) => setDrafts({ ...drafts, [c.id]: { ...drafts[c.id], name: e.target.value } })}
              className="bg-white/5 border-white/10 h-8 w-40 text-xs font-semibold" />
            <Input value={drafts[c.id]?.subs ?? c.subcategories.join(', ')}
              onChange={(e) => setDrafts({ ...drafts, [c.id]: { ...drafts[c.id], subs: e.target.value } })}
              placeholder="Sous-catégories séparées par des virgules"
              className="bg-white/5 border-white/10 h-8 flex-1 min-w-[240px] text-xs" data-testid={`category-subs-${c.name}`} />
            <Button size="sm" variant="outline" onClick={() => save(c)} data-testid={`category-save-${c.name}`}
              className="h-8 border-[#D9B35A]/40 text-[#D9B35A] hover:bg-[#D9B35A]/10">
              <Save className="w-3 h-3" />
            </Button>
            <Button size="sm" variant="ghost" onClick={() => remove(c)} data-testid={`category-delete-${c.name}`}
              className="h-8 text-red-400 hover:bg-red-500/10">
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        ))}
        <div className="flex flex-wrap items-center gap-2 p-2.5 rounded-lg border border-dashed border-white/15">
          <Input value={newCat.name} onChange={(e) => setNewCat({ ...newCat, name: e.target.value })}
            placeholder="Nouvelle catégorie" className="bg-white/5 border-white/10 h-8 w-40 text-xs" data-testid="new-category-name" />
          <Input value={newCat.subs} onChange={(e) => setNewCat({ ...newCat, subs: e.target.value })}
            placeholder="Sous-catégories (virgules)" className="bg-white/5 border-white/10 h-8 flex-1 min-w-[240px] text-xs" data-testid="new-category-subs" />
          <Button size="sm" onClick={create} className="h-8 bg-[#D9B35A] hover:bg-[#c9a34a] text-black font-bold" data-testid="new-category-btn">
            <Plus className="w-3 h-3 mr-1" /> Ajouter
          </Button>
        </div>
      </div>
    </div>
  );
};
