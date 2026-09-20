import { useEffect, useState } from 'react';
import { Globe } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const LANG_FLAGS = { fr: '🇫🇷', en: '🇬🇧', es: '🇪🇸', gcf: '🇬🇵', ar: '🇸🇦' };

// Aperçu superadmin des emails transactionnels dans les 5 langues du site
export const I18nEmailPreviews = () => {
  const [data, setData] = useState(null);
  const [sel, setSel] = useState(null);
  const [lang, setLang] = useState('fr');

  useEffect(() => {
    fetch(`${API}/admin/email-previews/i18n`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { setData(d); if (d?.templates?.length) setSel(d.templates[0].id); })
      .catch(() => {});
  }, []);

  if (!data) return null;
  const tpl = data.templates.find((t) => t.id === sel);
  const cur = tpl?.langs?.[lang];

  return (
    <div className="rounded-2xl p-5 bg-white/[0.02] border border-white/[0.08] mt-6" data-testid="i18n-email-previews">
      <h3 className="text-sm font-bold text-white flex items-center gap-2 m-0 mb-3">
        <Globe className="w-4 h-4 text-[#D9B35A]" /> Emails multilingues (fr · en · es · gcf · ar)
      </h3>
      <div className="flex flex-wrap gap-1.5 mb-3">
        {data.templates.map((t) => (
          <button key={t.id} type="button" onClick={() => setSel(t.id)} data-testid={`i18n-tpl-${t.id}`}
            className={`px-3 py-1.5 rounded-full text-[11px] font-semibold border transition-colors ${sel === t.id
              ? 'bg-[#D9B35A]/25 border-[#D9B35A]/60 text-[#E9CF8E]'
              : 'bg-white/[0.04] border-white/15 text-white/55 hover:text-white'}`}>
            {t.name}
          </button>
        ))}
      </div>
      <div className="flex gap-1.5 mb-3" data-testid="i18n-lang-tabs">
        {data.langs.map((l) => (
          <button key={l} type="button" onClick={() => setLang(l)} data-testid={`i18n-lang-${l}`}
            className={`px-2.5 py-1.5 rounded-lg text-base leading-none border transition-colors ${lang === l
              ? 'bg-[#D9B35A]/25 border-[#D9B35A]/60'
              : 'bg-white/[0.04] border-white/15 opacity-60 hover:opacity-100'}`}>
            {LANG_FLAGS[l]}
          </button>
        ))}
      </div>
      {cur && (
        <>
          <p className="text-xs text-white/70 m-0 mb-2" data-testid="i18n-email-subject">
            <span className="text-white/40">Objet :</span> <strong>{cur.subject}</strong>
          </p>
          <div className="rounded-xl overflow-hidden border border-white/10 bg-white">
            <iframe title="email-preview" srcDoc={cur.html} className="w-full h-64 border-0" data-testid="i18n-email-frame" />
          </div>
        </>
      )}
    </div>
  );
};
