import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import fr from './locales/fr.json';
import gcf from './locales/gcf.json';
import gcfExtra from './locales/gcf-extra.json';
import gcfSite from './locales/gcf-site.json';
import frSite from './locales/fr-site.json';
import frApp from './locales/fr-app.json';
import en from './locales/en.json';
import enSite from './locales/en-site.json';
import enApp from './locales/en-app.json';
import es from './locales/es.json';
import esSite from './locales/es-site.json';
import esApp from './locales/es-app.json';
import frAdmin from './locales/fr-admin.json';
import enAdmin from './locales/en-admin.json';
import esAdmin from './locales/es-admin.json';
import frData from './locales/fr-data.json';
import enData from './locales/en-data.json';
import esData from './locales/es-data.json';
import ar from './locales/ar.json';

/**
 * KDMARCHÉ × O'SCOP — i18n scaffolding.
 * Default: FR. Supports EN (Caribbean diaspora, partners) and ES (DOM hispanophones).
 *
 * Detection : URL `?lang=es` > localStorage `i18nextLng` > navigator > FR fallback.
 */
const mergeNs = (...objs) => {
  const out = {};
  for (const o of objs) {
    for (const [k, v] of Object.entries(o)) {
      out[k] = v && typeof v === 'object' && !Array.isArray(v) ? { ...(out[k] || {}), ...v } : v;
    }
  }
  return out;
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      fr: { translation: { ...fr, ...frSite, ...frApp, ...frAdmin, ...frData } },
      en: { translation: { ...en, ...enSite, ...enApp, ...enAdmin, ...enData } },
      es: { translation: { ...es, ...esSite, ...esApp, ...esAdmin, ...esData } },
      gcf: { translation: mergeNs(gcf, gcfExtra, gcfSite) },
      ar: { translation: ar },
    },
    fallbackLng: 'fr',
    supportedLngs: ['fr', 'en', 'es', 'gcf', 'ar'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['querystring', 'localStorage', 'htmlTag'],
      lookupQuerystring: 'lang',
      caches: ['localStorage'],
    },
  });

// RTL pour l'arabe (Moyen-Orient)
const applyDir = (lng) => {
  if (typeof document !== 'undefined') {
    document.documentElement.dir = (lng || '').startsWith('ar') ? 'rtl' : 'ltr';
    document.documentElement.lang = lng || 'fr';
  }
};
applyDir(i18n.language);
i18n.on('languageChanged', applyDir);

// Ping anonyme d'usage de langue (1 fois par langue et par session)
const pingLangUsage = (lng) => {
  try {
    const key = `lang_pinged_${lng}`;
    if (!lng || sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, '1');
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lang-usage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang: lng }),
    }).catch(() => {});
  } catch { /* stockage indisponible */ }
};
pingLangUsage(i18n.language);
i18n.on('languageChanged', pingLangUsage);

export default i18n;
