import { Link, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { Building2, ShoppingBasket, Home, Ticket, ShoppingCart, MapPin } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const LOLO_PATHS = ['/particuliers', '/pass-lolodrive', '/catalogue-lolodrive', '/points-relais'];
const LOLO_NAV = [
  { to: '/particuliers', label: 'Accueil', icon: Home, testid: 'lolo-subnav-accueil' },
  { to: '/pass-lolodrive', label: 'PASS LOLODRIVE', icon: Ticket, testid: 'lolo-subnav-pass' },
  { to: '/catalogue-lolodrive', label: 'Catalogue LOLODRIVE', icon: ShoppingCart, testid: 'lolo-subnav-catalogue' },
  { to: '/points-relais', label: 'Réseau LOLODRIVE', icon: MapPin, testid: 'lolo-subnav-reseau' },
];

export const AudienceSwitcher = () => {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const isPro = pathname === '/';
  const isLolo = LOLO_PATHS.some((p) => pathname.startsWith(p));
  useEffect(() => {
    document.body.classList.add('has-audience-switcher');
    document.body.classList.toggle('has-lolo-subnav', isLolo);
    return () => {
      document.body.classList.remove('has-audience-switcher');
      document.body.classList.remove('has-lolo-subnav');
    };
  }, [isLolo]);
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
          className={`${base} ${isLolo ? 'text-[#1F2A12]' : 'text-white/70 hover:text-white'}`}
          style={isLolo ? { background: '#8CC63E' } : {}}>
          <ShoppingBasket className="w-3.5 h-3.5" />
          <span>{t('audience.consumers')} · LOLODRIVE</span>
        </Link>
      </div>
      {isLolo && (
        <nav data-testid="lolo-subnav" className="overflow-x-auto"
          style={{ background: '#243311', borderTop: '1px solid rgba(140,198,62,0.35)' }}>
          <div className="max-w-[1160px] mx-auto flex items-center gap-1 px-2">
            {LOLO_NAV.map(({ to, label, icon: Icon, testid }) => {
              const active = pathname === to || (to !== '/particuliers' && pathname.startsWith(to));
              return (
                <Link key={to} to={to} data-testid={testid}
                  className={`inline-flex items-center gap-1.5 whitespace-nowrap px-3 py-1.5 text-[11px] sm:text-[12px] font-semibold transition-colors ${
                    active ? 'text-[#1F2A12] rounded-md' : 'text-white/75 hover:text-white'}`}
                  style={active ? { background: '#8CC63E' } : {}}>
                  <Icon className="w-3 h-3" />
                  <span>{label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </div>
  );
};
