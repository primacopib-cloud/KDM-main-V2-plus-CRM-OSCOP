import { useEffect, useState } from 'react';
import { Mail, Loader2 } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const EmailPreviewsTab = () => {
  const [templates, setTemplates] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/admin/email-previews`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => r.json())
      .then((d) => {
        setTemplates(d.templates || []);
        setSelected((d.templates || [])[0] || null);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" /></div>;
  }

  const categories = [...new Set(templates.map((t) => t.category))];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4" data-testid="email-previews-tab">
      <div className="glass-panel-soft rounded-[18px] p-4 max-h-[75vh] overflow-y-auto">
        <h3 className="flex items-center gap-2 text-sm font-semibold mb-3 text-[#D9B35A]">
          <Mail className="w-4 h-4" /> Modèles d'emails ({templates.length})
        </h3>
        {categories.map((cat) => (
          <div key={cat} className="mb-3">
            <p className="text-[11px] uppercase tracking-wider text-white/50 mb-1.5">{cat}</p>
            <div className="space-y-1">
              {templates.filter((t) => t.category === cat).map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setSelected(t)}
                  data-testid={`email-template-${t.id}`}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    selected?.id === t.id
                      ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/40'
                      : 'text-white/75 hover:bg-white/[0.06] border border-transparent'
                  }`}
                >
                  {t.name}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="glass-panel-soft rounded-[18px] p-4">
        {selected ? (
          <>
            <div className="mb-3 pb-3 border-b border-white/10">
              <p className="text-[11px] uppercase tracking-wider text-white/50">Objet</p>
              <p className="text-sm font-medium" data-testid="email-preview-subject">{selected.subject}</p>
            </div>
            <iframe
              title="email-preview"
              srcDoc={selected.html}
              data-testid="email-preview-frame"
              className="w-full rounded-xl border border-white/10 bg-[#1E0C34]"
              style={{ height: '65vh' }}
            />
          </>
        ) : (
          <p className="text-white/50 text-sm">Sélectionnez un modèle</p>
        )}
      </div>
    </div>
  );
};
