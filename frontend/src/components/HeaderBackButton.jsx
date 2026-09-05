import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import i18n from '@/i18n';

export const HeaderBackButton = ({ fallback = '/', withLabel = true, className = '' }) => {
  const navigate = useNavigate();
  const location = useLocation();
  if (location.pathname === '/') return null;
  const goBack = () => {
    if (window.history.length > 2) navigate(-1);
    else navigate(fallback);
  };
  return (
    <button
      type="button"
      onClick={goBack}
      data-testid="header-back-button"
      title={i18n.t('nav.back', 'Retour')}
      className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/[0.06] transition-colors ${className}`}
    >
      <ArrowLeft className="w-4 h-4" />
      {withLabel && <span className="text-sm hidden sm:inline">{i18n.t('nav.back', 'Retour')}</span>}
    </button>
  );
};
