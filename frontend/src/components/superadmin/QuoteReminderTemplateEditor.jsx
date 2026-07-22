import { useEffect, useState } from 'react';
import { FileEdit, ChevronDown, ChevronUp, Save, Loader2, RotateCcw, Eye, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const LANGS = [['fr', 'Français'], ['en', 'English'], ['es', 'Español']];
const EMPTY = { fr: { subject: '', body: '' }, en: { subject: '', body: '' }, es: { subject: '', body: '' } };

export const QuoteReminderTemplateEditor = () => {
  const [open, setOpen] = useState(false);
  const [lang, setLang] = useState('fr');
  const [tpl, setTpl] = useState(EMPTY);
  const [defaults, setDefaults] = useState(null);
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState(null);
  const [previewing, setPreviewing] = useState(false);

  const showPreview = async () => {
    setPreviewing(true);
    try {
      const r = await fetch(`${API}/admin/quotes/reminder-template/preview`, {
        method: 'POST', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang, subject: cur.subject, body: cur.body }),
      });
      if (!r.ok) throw new Error();
      setPreview(await r.json());
    } catch { toast.error('Aperçu indisponible'); }
    setPreviewing(false);
  };

  useEffect(() => {
    fetch(`${API}/admin/quotes/reminder-template`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setDefaults(d.defaults || null);
        setTpl({ ...EMPTY, ...(d.templates || {}) });
      }).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/admin/quotes/reminder-template`, {
        method: 'PUT', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ templates: tpl }),
      });
      if (!r.ok) throw new Error();
      toast.success('Modèle de relance enregistré');
    } catch { toast.error('Enregistrement impossible'); }
    setSaving(false);
  };

  const cur = tpl[lang] || { subject: '', body: '' };
  const setCur = (patch) => setTpl({ ...tpl, [lang]: { ...cur, ...patch } });
  const isCustom = !!(cur.subject || cur.body);

  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/[0.08]">
      <button type="button" onClick={() => setOpen(!open)} data-testid="quote-template-toggle"
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-white/70 hover:text-white transition-colors">
        <span className="flex items-center gap-1.5">
          <FileEdit size={13} className="text-[#D9B35A]" /> Modèle de relance email
          {isCustom && <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-[#D4AF37]/15 text-[#E9CF8E] border border-[#D4AF37]/30">personnalisé</span>}
        </span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2.5" data-testid="quote-template-panel">
          <div className="flex gap-1.5">
            {LANGS.map(([k, label]) => (
              <button key={k} type="button" onClick={() => setLang(k)} data-testid={`template-lang-${k}`}
                className={`px-2.5 py-1 rounded-full text-[10px] font-bold border transition-colors ${lang === k ? 'bg-[#D9B35A]/20 border-[#D9B35A]/50 text-[#E9CF8E]' : 'bg-white/[0.04] border-white/10 text-white/50'}`}>
                {label}{(tpl[k]?.subject || tpl[k]?.body) ? ' •' : ''}
              </button>
            ))}
          </div>
          <input value={cur.subject} data-testid="template-subject-input"
            onChange={(e) => setCur({ subject: e.target.value })}
            placeholder={defaults?.[lang]?.subject ? `Objet par défaut : ${defaults[lang].subject}` : 'Objet de l\'email…'}
            className="w-full h-9 px-3 rounded-lg text-xs text-white bg-white/[0.06] border border-white/15 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60" />
          <textarea value={cur.body} rows={5} data-testid="template-body-input"
            onChange={(e) => setCur({ body: e.target.value })}
            placeholder={defaults?.[lang]?.body || 'Corps du message…'}
            className="w-full px-3 py-2 rounded-lg text-xs text-white bg-white/[0.06] border border-white/15 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60 resize-y" />
          <div className="flex items-center justify-between flex-wrap gap-2">
            <p className="text-[10px] text-white/40">
              Variables : <code className="text-[#E9CF8E]">{'{name}'}</code> (contact) et <code className="text-[#E9CF8E]">{'{company}'}</code> (société).
              Laissez vide pour utiliser le modèle par défaut.
            </p>
            <span className="flex gap-1.5">
              <button type="button" onClick={showPreview} disabled={previewing} data-testid="template-preview-btn"
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-bold text-[#93C5FD] border border-[#60A5FA]/40 bg-[#60A5FA]/10 hover:bg-[#60A5FA]/20 transition-colors disabled:opacity-50">
                {previewing ? <Loader2 size={10} className="animate-spin" /> : <Eye size={10} />} Aperçu
              </button>
              <button type="button" onClick={() => setCur({ subject: '', body: '' })} data-testid="template-reset-btn"
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-bold text-white/50 border border-white/15 hover:text-white transition-colors">
                <RotateCcw size={10} /> Défaut
              </button>
              <button type="button" onClick={save} disabled={saving} data-testid="template-save-btn"
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-[10px] font-bold disabled:opacity-50"
                style={{ background: '#D4AF37', color: '#1F0A33' }}>
                {saving ? <Loader2 size={10} className="animate-spin" /> : <Save size={10} />} Enregistrer
              </button>
            </span>
          </div>
        </div>
      )}
      {preview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setPreview(null)} data-testid="template-preview-modal">
          <div className="w-full max-w-[640px] rounded-2xl bg-[#2A1045] border border-[#D9B35A]/30 shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
              <div className="min-w-0">
                <p className="text-[10px] uppercase tracking-wide text-white/40">
                  Aperçu de l'email de relance ({preview.lang?.toUpperCase()}) — {preview.custom ? 'modèle personnalisé' : 'modèle par défaut'}
                </p>
                <p className="text-sm font-semibold text-white truncate" data-testid="template-preview-subject">
                  Objet : {preview.subject}
                </p>
              </div>
              <button type="button" onClick={() => setPreview(null)} data-testid="template-preview-close"
                className="p-1.5 rounded-lg text-white/50 hover:text-white border border-white/15 flex-shrink-0 ml-3">
                <X size={14} />
              </button>
            </div>
            <iframe title="Aperçu email" srcDoc={preview.html} sandbox=""
              className="w-full h-[420px] bg-white" data-testid="template-preview-frame" />
            <p className="px-4 py-2 text-[10px] text-white/40">
              Variables remplacées par un exemple : Jean Dupont / Ma Société SARL.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
