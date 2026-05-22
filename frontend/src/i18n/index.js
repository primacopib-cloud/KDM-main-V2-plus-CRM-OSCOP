import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import fr from './locales/fr.json';
import en from './locales/en.json';
import es from './locales/es.json';

/**
 * KDMARCHÉ × O'SCOP — i18n scaffolding.
 * Default: FR. Supports EN (Caribbean diaspora, partners) and ES (DOM hispanophones).
 *
 * Detection : URL `?lang=es` > localStorage `i18nextLng` > navigator > FR fallback.
 */
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      fr: { translation: fr },
      en: { translation: en },
      es: { translation: es },
    },
    fallbackLng: 'fr',
    supportedLngs: ['fr', 'en', 'es'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['querystring', 'localStorage', 'navigator', 'htmlTag'],
      lookupQuerystring: 'lang',
      caches: ['localStorage'],
    },
  });

export default i18n;
