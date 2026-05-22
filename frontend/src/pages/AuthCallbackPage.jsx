import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { authAPI } from '../services/api';
import { toast } from 'sonner';

/**
 * Emergent OAuth landing page.
 *
 * Emergent redirects users to /auth/callback#session_id=XYZ after Google auth.
 * We extract the fragment, exchange it server-side, then route to the dashboard.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
export default function AuthCallbackPage() {
  const navigate = useNavigate();
  const hasProcessed = useRef(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const hash = window.location.hash || '';
    const m = hash.match(/session_id=([^&]+)/);
    if (!m) {
      setError("Aucun identifiant de session reçu d'Emergent.");
      return;
    }
    const sessionId = m[1];
    (async () => {
      try {
        await authAPI.exchangeEmergentSession(sessionId);
        toast.success('Connexion Google réussie');
        // Clear the hash before navigating
        window.history.replaceState(null, '', window.location.pathname);
        navigate('/dashboard', { replace: true });
      } catch (e) {
        setError(e.message || 'Échec de la connexion Google.');
      }
    })();
  }, [navigate]);

  return (
    <div
      data-testid="auth-callback-page"
      className="min-h-screen flex items-center justify-center p-4 text-white"
      style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}
    >
      <div className="text-center max-w-md">
        {!error ? (
          <>
            <Loader2 className="w-10 h-10 animate-spin mx-auto mb-4 text-[#D9B35A]" />
            <h1 className="text-xl font-semibold mb-2">Connexion en cours…</h1>
            <p className="text-sm text-white/60">Validation de votre session Google avec Emergent.</p>
          </>
        ) : (
          <>
            <h1 className="text-xl font-semibold mb-2 text-red-300">Connexion impossible</h1>
            <p className="text-sm text-white/60 mb-4">{error}</p>
            <button
              onClick={() => navigate('/connexion', { replace: true })}
              data-testid="auth-callback-retry"
              className="btn-gold inline-flex items-center justify-center px-5 h-10 rounded-xl text-sm font-semibold"
            >
              Retour à la connexion
            </button>
          </>
        )}
      </div>
    </div>
  );
}
