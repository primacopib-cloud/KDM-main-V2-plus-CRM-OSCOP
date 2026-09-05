import { Link, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { Building2, ShoppingBasket } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export const AudienceSwitcher = () => {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const isPro = pathname === '/';
  useEffect(() => {
    document.body.classList.add('has-audience-switcher');
    return () => document.body.classList.remove('has-audience-switcher');
  }, []);
  const base = 'flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 text-[12px] sm:text-[13px] font-semibold transition-colors';
  return (
    <div className="fixed top-0 left-0 right-0 z-[60]" data-testid="audience-switcher"
      style={{ background: '#1E0C34', borderBottom: '1px solid rgba(212,175,55,0.30)' }}>
      <div className="max-w-[1160px] mx-auto flex">
        <Link to="/" data-testid="audience-pro"
          className={`${base} ${isPro ? 'on-gold' : 'text-white/70 hover:text-white'}`}
          style={isPro ? { background: '#D9B35A' } : {}}>
          <Building2 className="w-3.5 h-3.5" />
          <span>{t('audience.pro')} · Centrale O'SCOP</span>
        </Link>
        <Link to="/particuliers" data-testid="audience-particuliers"
          className={`${base} ${!isPro && pathname.startsWith('/particuliers') ? 'text-[#1F2A12]' : 'text-white/70 hover:text-white'}`}
          style={!isPro && pathname.startsWith('/particuliers') ? { background: '#8CC63E' } : {}}>
          <ShoppingBasket className="w-3.5 h-3.5" />
          <span>{t('audience.consumers')} · LOLODRIVE</span>
        </Link>
      </div>
    </div>
  );
};
