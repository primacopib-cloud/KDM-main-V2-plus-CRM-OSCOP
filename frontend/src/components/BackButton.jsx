import i18n from '@/i18n';
/**
 * Floating "back to previous page" button.
 *
 * - Mounted once in App.js inside the Router.
 * - Visible only on back-office / admin routes (see BACK_OFFICE_PATTERNS).
 * - Hidden when the user has no history to go back to (fresh tab).
 * - Sits below the top NavBar so it never overlaps content.
 */
import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { popPrevious } from "../utils/backStack";

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
  const { pathname, search } = useLocation();
  const visible = useMemo(() => isBackOfficeRoute(pathname), [pathname]);

  if (!visible) return null;

  const handleClick = () => {
    // Pile interne : évite de retomber sur une page externe (ex : Stripe)
    const prev = popPrevious(pathname + search);
    navigate(prev || "/admin");
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      data-testid="back-office-back-btn"
      aria-label={i18n.t('common.back')}
      title={i18n.t('common.back')}
      className="back-office-back-btn"
    >
      <ArrowLeft size={14} aria-hidden="true" />
      <span>{i18n.t('common.back')}</span>
    </button>
  );
}
