import { API } from './http';

const TTL_MS = 24 * 3600 * 1000;

export const trackCta = (ctaId) => {
  try {
    localStorage.setItem('last_cta', JSON.stringify({ id: ctaId, at: Date.now() }));
  } catch {
    /* silencieux */
  }
  try {
    fetch(`${API}/public/cta-click`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cta_id: ctaId }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* silencieux : le tracking ne doit jamais bloquer la navigation */
  }
};

export const getLastCta = () => {
  try {
    const raw = localStorage.getItem('last_cta');
    if (!raw) return '';
    const { id, at } = JSON.parse(raw);
    return Date.now() - at < TTL_MS ? id : '';
  } catch {
    return '';
  }
};
