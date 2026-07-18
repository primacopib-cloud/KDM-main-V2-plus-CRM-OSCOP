import { useEffect, useState } from 'react';
import { Mail, Loader2, Send } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

export const EmailPreviewsTab = () => {
  const [templates, setTemplates] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [testEmail, setTestEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [totalSent, setTotalSent] = useState(0);

  useEffect(() => {
    fetch(`${API}/admin/email-previews`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => r.json())
      .then((d) => {
        setTemplates(d.templates || []);
        setSelected((d.templates || [])[0] || null);
        setTestEmail(d.admin_email || '');
        setTotalSent(d.total_sent || 0);
      })
      .finally(() => setLoading(false));
  }, []);

  const sendTest = async () => {
    if (!selected) return;
    setSending(true);
    try {
      const r = await fetch(`${API}/admin/email-previews/${selected.id}/send-test`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: testEmail }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Envoi impossible');
      toast.success(`Email test envoyé à ${d.to}`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" /></div>;
  }

  const categories = [...new Set(templates.map((t) => t.category))];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4" data-testid="email-previews-tab">
      <div className="glass-panel-soft rounded-[18px] p-4 max-h-[75vh] overflow-y-auto">
        <h3 className="flex items-center gap-2 text-sm font-semibold mb-1 text-[#D9B35A]">
          <Mail className="w-4 h-4" /> Modèles d'emails ({templates.length})
        </h3>
        <p className="text-[11px] text-white/45 mb-3" data-testid="email-total-sent">
          {totalSent.toLocaleString('fr-FR')} envoi{totalSent > 1 ? 's' : ''} réel{totalSent > 1 ? 's' : ''} journalisé{totalSent > 1 ? 's' : ''}
        </p>
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
                  className={`w-full flex items-center justify-between gap-2 text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    selected?.id === t.id
                      ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/40'
                      : 'text-white/75 hover:bg-white/[0.06] border border-transparent'
                  }`}
                >
                  <span className="truncate">{t.name}</span>
                  <span
                    data-testid={`email-count-${t.id}`}
                    className={`flex-shrink-0 min-w-[26px] text-center text-[11px] font-semibold px-1.5 py-0.5 rounded-full ${
                      (t.stats?.count || 0) > 0
                        ? 'bg-[#D9B35A]/25 text-[#E9CF8E]'
                        : 'bg-white/[0.06] text-white/35'
                    }`}
                  >
                    {t.stats?.count || 0}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="glass-panel-soft rounded-[18px] p-4">
        {selected ? (
          <>
            <div className="mb-3 pb-3 border-b border-white/10 flex flex-wrap items-end justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[11px] uppercase tracking-wider text-white/50">Objet</p>
                <p className="text-sm font-medium" data-testid="email-preview-subject">{selected.subject}</p>
                <p className="text-[11px] text-white/45 mt-0.5" data-testid="email-preview-stats">
                  {selected.stats?.count || 0} envoi{(selected.stats?.count || 0) > 1 ? 's' : ''} réel{(selected.stats?.count || 0) > 1 ? 's' : ''}
                  {selected.stats?.last_sent && ` · dernier : ${new Date(selected.stats.last_sent).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}`}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <input
                  type="email"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                  placeholder="votre@email.fr"
                  data-testid="test-email-input"
                  className="h-9 w-56 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/40 focus:border-[#D9B35A] outline-none"
                />
                <button
                  type="button"
                  onClick={sendTest}
                  disabled={sending || !testEmail}
                  data-testid="send-test-email-btn"
                  className="h-9 inline-flex items-center gap-1.5 px-4 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
                  style={{ background: '#D4AF37', color: '#1F0A33' }}
                >
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  M'envoyer un test
                </button>
              </div>
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
