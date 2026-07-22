import { useCallback, useEffect, useState } from 'react';
import { BookMarked, Trash2, RotateCcw, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TYPE_LABELS = { email: 'Email', whatsapp: 'WhatsApp', video_script: 'Vidéo' };

export const ProspectiaLibrary = ({ onReuse, refreshKey }) => {
  const [items, setItems] = useState([]);

  const load = useCallback(() => {
    fetch(`${API}/admin/prospectia/library`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load, refreshKey]);

  const remove = async (id) => {
    const r = await fetch(`${API}/admin/prospectia/library/${id}`, { method: 'DELETE', credentials: 'include' });
    if (r.ok) { toast.success('Script supprimé'); load(); }
  };

  if (!items.length) return null;
  return (
    <div className="mt-4 pt-4 border-t border-white/10" data-testid="prospectia-library">
      <p className="text-xs text-white/55 font-semibold mb-2 flex items-center gap-1.5">
        <BookMarked size={12} className="text-[#D9B35A]" /> Bibliothèque de scripts ({items.length}) — classés par taux de clic
      </p>
      <div className="space-y-2 max-h-72 overflow-y-auto">
        {items.map((s) => (
          <div key={s.id} className="p-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-xs" data-testid={`library-item-${s.id}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-white font-medium">{s.title}</span>
              <span className="px-1.5 py-0.5 rounded bg-white/10 text-white/60">{TYPE_LABELS[s.content_type] || s.content_type}</span>
              <span className="px-1.5 py-0.5 rounded bg-white/10 text-white/60">{s.target === 'vendor' ? 'Vendeurs' : 'Acheteurs'}</span>
              {s.click_rate !== null && s.click_rate !== undefined && (
                <span className="px-1.5 py-0.5 rounded bg-emerald-400/15 text-emerald-300 font-semibold inline-flex items-center gap-1">
                  <TrendingUp size={10} /> {s.click_rate}% de clics
                </span>
              )}
              <div className="ml-auto flex gap-1">
                <button onClick={() => onReuse(s)} data-testid={`library-reuse-${s.id}`}
                  className="p-1.5 rounded-lg hover:bg-white/10 text-[#E9CF8E]" title="Réutiliser ce script">
                  <RotateCcw size={13} />
                </button>
                <button onClick={() => remove(s.id)} className="p-1.5 rounded-lg hover:bg-red-500/15 text-white/40 hover:text-red-300" title="Supprimer">
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
            <div className="text-white/45 mt-1">
              🚀 {s.campaigns_count} campagne(s) · 📤 {s.total_sent} envoyés · 🖱 {s.total_clicks} clic(s) · ✅ {s.total_conversions} inscrit(s)
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
