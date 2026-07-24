import React from 'react';
import { useTranslation } from 'react-i18next';
import { API, getAuthHeaders, getSessionToken } from '../services/http';

const saveLangToProfile = (code) => {
  if (!getSessionToken()) return Promise.resolve();
  return fetch(`${API}/profile/language`, {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ language: code }),
  }).catch(() => {});
};

const LANGS = [
  { code: 'fr', label: 'Français', flag: 'fr' },
  { code: 'en', label: 'English', flag: 'gb' },
  { code: 'es', label: 'Español', flag: 'es' },
  { code: 'gcf', label: 'Kréyòl', flag: 'gp' },
];

/**
 * Language switcher with country flags (FR · EN · ES · Kréyòl).
 * Persisted via i18next-browser-languagedetector → localStorage.
 */
export default function LanguageSwitcher({ className = '' }) {
  const { i18n } = useTranslation();
  const lng = i18n.language || 'fr';
  const current = lng.startsWith('gcf') ? 'gcf' : lng.slice(0, 2);

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`} data-testid="language-switcher">
      {LANGS.map((l) => (
        <button
          key={l.code}
          onClick={() => Promise.all([i18n.changeLanguage(l.code), saveLangToProfile(l.code)]).then(() => window.location.reload())}
          data-testid={`language-${l.code}`}
          className={`p-1 rounded-md transition-all ${
            current === l.code
              ? 'ring-2 ring-[#D9B35A] bg-[#D9B35A]/10'
              : 'opacity-50 hover:opacity-100 hover:bg-white/[0.05]'
          }`}
          title={l.label}
          aria-label={l.label}
          aria-current={current === l.code ? 'true' : 'false'}
        >
          <img
            src={`https://flagcdn.com/w40/${l.flag}.png`}
            srcSet={`https://flagcdn.com/w80/${l.flag}.png 2x`}
            alt={l.label}
            className="w-5 h-auto rounded-[2px] block"
            style={{ boxShadow: '0 0 0 1px rgba(0,0,0,0.12)' }}
          />
        </button>
      ))}
    </div>
  );
}
