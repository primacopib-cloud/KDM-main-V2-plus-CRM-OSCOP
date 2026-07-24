import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { API, getAuthHeaders, getSessionToken } from '../services/http';

export const LanguagePrefSync = () => {
  const { i18n } = useTranslation();
  const token = getSessionToken();

  useEffect(() => {
    if (!token || sessionStorage.getItem('lang_synced')) return;
    sessionStorage.setItem('lang_synced', '1');
    fetch(`${API}/profile/language`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const cur = i18n.language?.startsWith('gcf') ? 'gcf' : (i18n.language || 'fr').slice(0, 2);
        if (d?.language && d.language !== cur) {
          i18n.changeLanguage(d.language).then(() => window.location.reload());
        }
      }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return null;
};
