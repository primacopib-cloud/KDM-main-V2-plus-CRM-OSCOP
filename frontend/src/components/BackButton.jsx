/**
 * Floating "back to previous page" button.
 *
 * - Mounted once in App.js inside the Router.
 * - Visible only on back-office / admin routes (see BACK_OFFICE_PATTERNS).
 * - Hidden when the user has no history to go back to (fresh tab).
 * - Sits below the top NavBar so it never overlaps content.
 */
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

const BACK_OFFICE_PATTERNS = [
  /^\/admin(\/|$)/,
  /^\/admin-v2(\/|$)/,
  /^\/super-?admin(\/|$)/,
  /^\/lolodrive(\/|$)/,
  /^\/lolo-point(\/|$)/,
  /^\/gerant(\/|$)/,
  /^\/crm(\/|$)/,
  /^\/crm-partenaires(\/|$)/,
  /^\/reporting-(impact|ess)(\/|$)/,
  /^\/espace-vendeur(\/|$)/,
  /^\/vendor(\/|$)/,
  /^\/pos(\/|$)/,
  /^\/pos-lolodrive(\/|$)/,
  /^\/statistiques(\/|$)/,
  /^\/dashboard(\/|$)/,
];

function isBackOfficeRoute(pathname) {
  return BACK_OFFICE_PATTERNS.some((rx) => rx.test(pathname));
}

export default function BackButton() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const visible = useMemo(() => isBackOfficeRoute(pathname), [pathname]);

  // Track whether the user has any "back" history we can use.
  // window.history.length starts at 1 on a fresh tab; > 1 means there is history.
  const [hasHistory, setHasHistory] = useState(false);
  useEffect(() => {
    if (typeof window !== "undefined") {
      setHasHistory(window.history.length > 1);
    }
  }, [pathname]);

  if (!visible) return null;

  const handleClick = () => {
    if (hasHistory) {
      navigate(-1);
    } else {
      navigate("/admin");
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      data-testid="back-office-back-btn"
      aria-label="Retour à la page précédente"
      title="Retour à la page précédente"
      className="back-office-back-btn"
    >
      <ArrowLeft size={14} aria-hidden="true" />
      <span>Retour</span>
    </button>
  );
}
