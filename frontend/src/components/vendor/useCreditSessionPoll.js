import { useEffect } from 'react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const useCreditSessionPoll = (fetchCredits) => {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('credit_session');
    if (!sessionId) return;
    window.history.replaceState({}, '', '/espace-vendeur');
    const poll = async (attempt = 0) => {
      const r = await fetch(`${API_URL}/api/credit-packs/status/${sessionId}`, { credentials: 'include' });
      if (r.ok) {
        const d = await r.json();
        if (d.payment_status === 'paid') {
          if (d.credited > 0) toast.success(`Paiement confirmé : +${d.credited} crédits ajoutés !`);
          fetchCredits();
          return;
        }
      }
      if (attempt < 6) setTimeout(() => poll(attempt + 1), 2500);
    };
    poll();
  }, [fetchCredits]);
};
