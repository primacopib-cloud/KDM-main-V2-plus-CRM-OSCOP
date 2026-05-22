import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { authAPI } from "../services/api";

/**
 * Landing page after Google OAuth callback.
 *
 * Flow:
 *   Google → /api/auth/google/callback (backend) → /auth/google/return?token=<JWT>&next=/dashboard
 *
 * We read the token from the query string, persist it the SAME way the
 * email/password login does (localStorage 'token'), then fetch /api/auth/me
 * to hydrate the React user, and finally navigate to `next` (default /dashboard).
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
export default function GoogleAuthReturnPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    const next = searchParams.get("next") || "/dashboard";
    const googleError = searchParams.get("google_error");

    if (googleError) {
      setError(googleError);
      toast.error(`Connexion Google échouée : ${googleError}`);
      setTimeout(() => navigate("/connexion", { replace: true }), 2500);
      return;
    }

    if (!token) {
      setError("missing_token");
      toast.error("Token manquant après redirection Google");
      setTimeout(() => navigate("/connexion", { replace: true }), 2500);
      return;
    }

    // Persist token the exact same way email/password login does
    localStorage.setItem("token", token);

    // Hydrate user from /api/auth/me
    authAPI
      .getMe()
      .then((user) => {
        if (user?.email) localStorage.setItem("user", JSON.stringify(user));
        toast.success(`Bienvenue ${user?.contact_name || user?.email || ""}`);
        const safeNext = typeof next === "string" && next.startsWith("/") ? next : "/dashboard";
        navigate(safeNext, { replace: true });
      })
      .catch(() => {
        localStorage.removeItem("token");
        setError("hydration_failed");
        toast.error("Impossible de charger votre profil.");
        setTimeout(() => navigate("/connexion", { replace: true }), 2500);
      });
  }, [navigate, searchParams]);

  return (
    <div
      data-testid="google-auth-return-page"
      className="min-h-screen flex items-center justify-center px-6"
      style={{ background: "linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)" }}
    >
      <div className="glass-panel rounded-2xl p-10 text-center max-w-md w-full">
        {error ? (
          <>
            <h1 className="font-display text-2xl mb-2" style={{ color: "var(--kdm-bleu-logistique)" }}>
              Connexion impossible
            </h1>
            <p className="text-sm text-anthracite opacity-70">
              Redirection vers la page de connexion…
            </p>
          </>
        ) : (
          <>
            <Loader2 className="animate-spin mx-auto mb-4" size={36} style={{ color: "var(--kdm-or-metallise)" }} />
            <h1 className="font-display text-2xl mb-2" style={{ color: "var(--kdm-bleu-logistique)" }}>
              Connexion en cours…
            </h1>
            <p className="text-sm text-anthracite opacity-70">
              Authentification Google validée. Chargement de votre espace KDMARCHE.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
