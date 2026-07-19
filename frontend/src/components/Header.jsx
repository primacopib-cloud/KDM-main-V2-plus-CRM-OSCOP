import i18n from '@/i18n';
import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { partners } from '../data/mock';
import { Menu, X, User, LogIn, Download } from 'lucide-react';
import CommunityplaceBadge from './CommunityplaceBadge';

const Header = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { href: '/', label: i18n.t('nav.home') },
    { href: '/offres', label: i18n.t('footer.our_offers') },
    { href: '/#contact', label: i18n.t('footer.contact') },
  ];

  return (
    <header 
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300`}
      style={{
        background: 'rgba(30,12,52,0.88)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(212,175,55,0.32)'
      }}
    >
      <div className="max-w-[1160px] mx-auto px-5">
        <div className="flex items-center justify-between h-14 gap-3">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center justify-center h-9 w-9 rounded-xl bg-white shrink-0 overflow-hidden" style={{ boxShadow: '0 1px 4px rgba(217,179,90,0.3)' }}>
                <img
                  src={partners.kdmarche.logo}
                  alt="KDMARCHE"
                  className="h-8 w-8 object-contain"
                />
              </span>
              <span className="text-white/30 text-sm leading-none">×</span>
              <span className="inline-flex items-center justify-center h-9 w-9 rounded-full bg-white shrink-0 overflow-hidden" style={{ boxShadow: '0 1px 4px rgba(212,175,55,0.3)' }}>
                <img
                  src={partners.oscop.logo}
                  alt="O'SCOP"
                  className="h-8 w-8 object-contain"
                />
              </span>
            </div>
            <div className="hidden xl:block">
              <h1 className="text-xs tracking-wider uppercase text-white/85 font-semibold m-0">
                KDMARCHE × O&apos;SCOP
              </h1>
              <p className="text-[10px] text-white/50 mt-0">{i18n.t('footer.hub_short')}</p>
            </div>
            <CommunityplaceBadge size="sm" className="hidden sm:inline-flex" />
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className={`text-xs text-white/70 px-2.5 py-1.5 rounded-lg hover:bg-white/[0.06] hover:text-white/90 transition-all ${
                  location.pathname === link.href ? 'text-white/90' : ''
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center gap-2">
            <Link to="/connexion">
              <button className="btn-ghost inline-flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium">
                <LogIn className="w-3.5 h-3.5" />
                {i18n.t('nav.login')}
              </button>
            </Link>
            <Link to="/inscription">
              <button className="btn-gold inline-flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium">
                <User className="w-3.5 h-3.5" />
                {i18n.t('footer.client_space')}
              </button>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 text-white/80"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div 
            className="md:hidden rounded-2xl mt-2 p-6 absolute left-4 right-4"
            style={{
              background: '#FFFFFF',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(212,175,55,0.34)',
              boxShadow: '0 18px 48px rgba(76,42,110,0.16)'
            }}
          >
            <nav className="flex flex-col gap-4">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  to={link.href}
                  className="text-white/80 font-medium hover:text-white transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              <hr className="border-white/10 my-2" />
              <Link to="/connexion" onClick={() => setIsMobileMenuOpen(false)}>
                <button className="btn-ghost w-full inline-flex items-center justify-center gap-2 rounded-[14px] px-4 py-3 text-sm font-semibold">
                  <LogIn className="w-4 h-4" />
                  {i18n.t('nav.login')}
                </button>
              </Link>
              <Link to="/inscription" onClick={() => setIsMobileMenuOpen(false)}>
                <button className="btn-gold w-full inline-flex items-center justify-center gap-2 rounded-[14px] px-4 py-3 text-sm font-semibold">
                  <User className="w-4 h-4" />
                  {i18n.t('footer.client_space')}
                </button>
              </Link>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
