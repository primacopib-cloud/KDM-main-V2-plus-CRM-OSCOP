import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import i18n from '@/i18n';

const LANGS = ['fr', 'en', 'es'];

export default function Seo({ titleKey, descKey }) {
  const location = useLocation();

  useEffect(() => {
    const title = i18n.t(titleKey);
    document.title = title.includes('KDMARCH') ? title : `${title} | KDMARCHÉ`;
    document.documentElement.lang = i18n.language.split('-')[0];

    if (descKey) {
      let meta = document.querySelector('meta[name="description"]');
      if (!meta) {
        meta = document.createElement('meta');
        meta.setAttribute('name', 'description');
        document.head.appendChild(meta);
      }
      meta.setAttribute('content', i18n.t(descKey));
    }

    const origin = window.location.origin;
    const path = location.pathname;
    document.querySelectorAll('link[data-seo-hreflang]').forEach((el) => el.remove());
    const addLink = (hreflang, href) => {
      const link = document.createElement('link');
      link.setAttribute('rel', 'alternate');
      link.setAttribute('hreflang', hreflang);
      link.setAttribute('href', href);
      link.setAttribute('data-seo-hreflang', '1');
      document.head.appendChild(link);
    };
    LANGS.forEach((l) => addLink(l, `${origin}${path}?lang=${l}`));
    addLink('x-default', `${origin}${path}`);

    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.setAttribute('rel', 'canonical');
      document.head.appendChild(canonical);
    }
    canonical.setAttribute('href', `${origin}${path}`);
  }, [titleKey, descKey, location.pathname]);

  return null;
}
