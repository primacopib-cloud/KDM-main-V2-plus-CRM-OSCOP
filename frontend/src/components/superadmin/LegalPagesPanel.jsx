import { useCallback, useEffect, useState } from 'react';
import { Loader2, Scale, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

export const LegalPagesPanel = () => {
  const [pages, setPages] = useState(null);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ title: '', content: '' });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const res = await fetch(`${API}/public/legal-pages`);
    if (res.ok) setPages((await res.json()).pages);
  }, []);
  useEffect(() => { load(); }, [load]);

  const openEditor = async (slug) => {
    const res = await fetch(`${API}/public/legal-pages/${slug}`);
    const page = await res.json();
    setForm({ title: page.title, content: page.content });
    setEditing(slug);
  };

  const save = async () => {
    setSaving(true);
    const res = await fetch(`${API}/admin/legal-pages/${editing}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(form),
    });
    setSaving(false);
    if (!res.ok) { toast.error('Enregistrement impossible'); return; }
    toast.success('Page juridique mise à jour');
    setEditing(null);
    load();
  };

  if (!pages) return <div className="py-8 text-center"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A] mx-auto" /></div>;

  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-6" data-testid="legal-pages-panel">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-3">
        <Scale className="w-5 h-5 text-[#D9B35A]" /> Pages juridiques administrables
      </h3>
      <div className="grid md:grid-cols-2 gap-1.5">
        {pages.map((p) => (
          <div key={p.slug} className="flex items-center justify-between gap-2 bg-white/5 rounded px-2.5 py-1.5 text-xs">
            <span className="text-white/80 truncate">{p.title}</span>
            <div className="flex gap-1 shrink-0">
              <a href={`/${p.slug}`} target="_blank" rel="noreferrer" className="text-white/40 hover:text-white/70 p-1"><ExternalLink className="w-3.5 h-3.5" /></a>
              <Button size="sm" data-testid={`edit-legal-${p.slug}`} className="h-6 text-[10px] bg-white/10 hover:bg-white/20 text-white"
                onClick={() => openEditor(p.slug)}>Modifier</Button>
            </div>
          </div>
        ))}
      </div>
      {editing && (
        <div className="mt-3 p-3 rounded bg-black/25 border border-white/10 space-y-2" data-testid="legal-editor">
          <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
            data-testid="legal-editor-title" className="bg-white/5 border-white/15 text-white" />
          <textarea value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })}
            data-testid="legal-editor-content" rows={14}
            className="w-full bg-white/5 border border-white/15 rounded-md p-2 text-xs text-white font-mono" />
          <div className="flex gap-2">
            <Button size="sm" onClick={save} disabled={saving} data-testid="legal-editor-save"
              className="bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A]">
              {saving && <Loader2 className="w-3 h-3 animate-spin mr-1" />} Enregistrer
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(null)} className="text-white/60">Annuler</Button>
          </div>
        </div>
      )}
    </div>
  );
};
