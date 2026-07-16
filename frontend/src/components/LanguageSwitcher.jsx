import React from 'react';
import { useTranslation } from 'react-i18next';
import { Globe2 } from 'lucide-react';

const LANGS = [
  { code: 'fr', label: 'FR', flag: '🇫🇷' },
  { code: 'en', label: 'EN', flag: '🇬🇧' },
  { code: 'es', label: 'ES', flag: '🇪🇸' },
];

/**
 * Compact language switcher (FR · EN · ES).
 * Persisted via i18next-browser-languagedetector → localStorage.
 */
export default function LanguageSwitcher({ className = '' }) {
  const { i18n } = useTranslation();
  const current = (i18n.language || 'fr').slice(0, 2);

  return (
    <div className={`inline-flex items-center gap-1 ${className}`} data-testid="language-switcher">
      <Globe2 className="w-3.5 h-3.5 text-white/40 mr-1" />
      {LANGS.map((l) => (
        <button
          key={l.code}
          onClick={() => i18n.changeLanguage(l.code).then(() => window.location.reload())}
          data-testid={`language-${l.code}`}
          className={`px-2 py-1 rounded-md text-[11px] font-semibold transition-all ${
            current === l.code
              ? 'bg-or-metallise/20 text-or-metallise'
              : 'text-white/55 hover:text-white/90 hover:bg-white/[0.05]'
          }`}
          aria-label={l.code.toUpperCase()}
          aria-current={current === l.code ? 'true' : 'false'}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
