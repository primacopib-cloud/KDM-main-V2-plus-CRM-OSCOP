import { API } from './http';

export const trackCta = (ctaId) => {
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
