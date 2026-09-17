import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Store, Gavel, Coins, Globe2, QrCode, CalendarClock, BadgePercent, ArrowRight } from 'lucide-react';
import { CONCEPT_I18N } from './conceptI18n';

const ICONS = [Gavel, Coins, BadgePercent, Globe2, CalendarClock, QrCode];
const LANGS = [['fr', '🇫🇷 FR'], ['en', '🇬🇧 EN'], ['es', '🇪🇸 ES'], ['gcf', '🌺 KR']];

export default function DetaillantConceptPage() {
  const [lang, setLang] = useState('fr');
  const t = CONCEPT_I18N[lang];
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white" data-testid="detaillant-concept-page">
      <div className="max-w-5xl mx-auto px-6 py-14">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2 text-[#D9B35A] text-xs font-bold uppercase tracking-[0.2em]">
            <Store className="w-4 h-4" /> {t.tag}
          </div>
          <div className="flex gap-1" data-testid="concept-lang-switch">
            {LANGS.map(([code, label]) => (
              <button key={code} onClick={() => setLang(code)} data-testid={`concept-lang-${code}`}
                className={`px-2.5 h-7 rounded-full text-[11px] font-bold border transition-colors ${
                  lang === code ? 'bg-[#D9B35A] text-black border-[#D9B35A]' : 'border-white/20 text-white/60 hover:bg-white/5'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black mt-4 leading-tight">
          {t.h1a}<br />
          <span className="text-[#E9CF8E]">{t.h1b}</span>
        </h1>
        <p className="text-base text-white/60 mt-5 max-w-2xl">{t.sub}</p>
        <div className="flex flex-wrap gap-3 mt-8">
          <Link to="/espace-detaillant" data-testid="concept-cta-join"
            className="inline-flex items-center gap-2 px-6 h-11 rounded-full bg-[#D9B35A] text-black text-sm font-bold hover:bg-[#E9CF8E]">
            {t.cta} <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/coopact" data-testid="concept-cta-coopact"
            className="inline-flex items-center gap-2 px-6 h-11 rounded-full border border-white/20 text-sm font-semibold hover:bg-white/5">
            {t.cta2}
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-14">
          {t.features.map(([title, desc], i) => {
            const Icon = ICONS[i];
            return (
              <div key={title} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5" data-testid="concept-feature">
                <Icon className="w-5 h-5 text-[#D9B35A]" />
                <p className="text-sm font-bold mt-2">{title}</p>
                <p className="text-xs text-white/55 mt-1 leading-relaxed">{desc}</p>
              </div>
            );
          })}
        </div>
        <div className="rounded-2xl border border-[#D9B35A]/30 bg-[#D9B35A]/5 p-6 mt-12">
          <p className="text-sm font-bold text-[#E9CF8E]">{t.how}</p>
          <ol className="text-xs text-white/60 mt-2 space-y-1.5 list-decimal list-inside">
            {t.steps.map((s) => <li key={s}>{s}</li>)}
          </ol>
        </div>
      </div>
    </div>
  );
}
