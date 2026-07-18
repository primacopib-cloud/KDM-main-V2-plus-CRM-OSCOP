import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { partners } from '../data/mock';
import { 
  Menu, X, User, LogIn, LogOut, 
  LayoutDashboard, ShoppingCart, Package, FileText, 
  Wallet, Settings, Users, Shield, BarChart3,
  Store, Building2, ChevronDown, Bell, Search,
  FileSignature, MapPin, CreditCard, Home, Heart, Truck, HeartHandshake, Server
} from 'lucide-react';
import { authAPI } from '../services/api';
import { useNotificationWebSocket, ConnectionStatus } from './NotificationToast';
import NavigationHistoryDropdown from './NavigationHistoryDropdown';
import QuickShortcuts from './QuickShortcuts';
import { useFavorites } from './FavoriteButton';
import LanguageSwitcher from './LanguageSwitcher';
import CommunityplaceBadge from './CommunityplaceBadge';
import { CrediscopBadge } from './CrediscopBadge';
import { useTranslation } from 'react-i18next';

// Favorites nav button with count
function FavoritesNavButton() {
  const { count } = useFavorites();
  
  return (
    <Link 
      to="/favoris" 
      className="relative p-2 rounded-lg hover:bg-white/[0.06] transition-colors"
      data-testid="favorites-nav-link"
      title="Favoris"
    >
      <Heart className={`w-4 h-4 ${count > 0 ? 'text-red-400 fill-red-400' : 'text-white/70'}`} />
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full text-[10px] font-bold flex items-center justify-center">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </Link>
  );
}

// Navigation items for different user roles
import { getNavItems } from './navbar/navItems';
import { UserMenu } from './navbar/UserMenu';

const NavBar = ({ variant = 'default' }) => {
  const { t } = useTranslation();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  
  // Check if user is logged in
  const isAuthenticated = authAPI.isAuthenticated();
  const isAdmin = user?.role === 'admin' || user?.email?.includes('admin');

  // WebSocket notifications for admin
  const { isConnected, notifications } = useNotificationWebSocket(
    user?.id,
    isAdmin
  );

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const loadUser = async () => {
      if (isAuthenticated) {
        try {
          const userData = await authAPI.getMe();
          setUser(userData);
        } catch (error) {
          console.error('Failed to load user:', error);
        }
      }
    };
    loadUser();
  }, [isAuthenticated]);

  const handleLogout = () => {
    authAPI.logout();
    setUser(null);
    navigate('/');
  };

  const nav = getNavItems(user?.role, isAdmin);
  const navItems = nav.topBar;
  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <header 
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300`}
      style={{
        background: isScrolled ? 'rgba(255,253,247,0.96)' : 'rgba(255,253,247,0.86)',
        backdropFilter: 'blur(14px)',
        borderBottom: '1px solid rgba(212,175,55,0.32)',
        boxShadow: isScrolled ? '0 8px 24px rgba(76,42,110,0.06)' : 'none'
      }}
    >
      <div className="max-w-[1400px] mx-auto px-4 lg:px-6">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-3 flex-shrink-0">
            <div className="flex items-center gap-2.5">
              <img 
                src={partners.kdmarche.logo} 
                alt="KDMARCHE Pro" 
                className="h-12 w-auto object-contain"
              />
              <span className="text-white/30 text-sm hidden sm:inline">×</span>
              <img 
                src={partners.oscop.logo} 
                alt="Objectif SCOP Outremer" 
                className="h-11 w-auto object-contain hidden sm:block"
              />
            </div>
            <CommunityplaceBadge size="sm" className="hidden md:inline-flex" />
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-1 flex-1 justify-center">
            {navItems.filter(item => isAuthenticated || item.public).map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={`flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg transition-all ${
                    isActive 
                      ? 'bg-[#D9B35A]/15 text-[#D9B35A]' 
                      : 'text-white/70 hover:bg-white/[0.06] hover:text-white/90'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {item.label.startsWith('nav.') ? t(item.label) : item.label}
                </Link>
              );
            })}
          </nav>

          {/* Right Section */}
          <div className="flex items-center gap-2">
            <LanguageSwitcher className="hidden md:flex" />
            {isAuthenticated ? (
              <>
                {/* Solde CREDI'SCOP */}
                <CrediscopBadge className="hidden sm:inline-flex" />

                {/* Quick Shortcuts */}
                <div className="hidden md:block">
                  <QuickShortcuts variant="navbar" />
                </div>

                {/* Navigation History */}
                <div className="hidden md:block">
                  <NavigationHistoryDropdown variant="dark" />
                </div>

                {/* WebSocket Status (Admin only) */}
                {isAdmin && (
                  <div className="hidden md:block">
                    <ConnectionStatus isConnected={isConnected} />
                  </div>
                )}

                {/* Notifications */}
                {isAdmin && (
                  <Link 
                    to="/notifications" 
                    className="relative p-2 rounded-lg hover:bg-white/[0.06] transition-colors"
                    data-testid="notifications-link"
                  >
                    <Bell className="w-4 h-4 text-white/70" />
                    {unreadCount > 0 && (
                      <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full text-[10px] font-bold flex items-center justify-center">
                        {unreadCount > 9 ? '9+' : unreadCount}
                      </span>
                    )}
                  </Link>
                )}

                {/* Favorites */}
                <FavoritesNavButton />

                <UserMenu
                  user={user}
                  nav={nav}
                  showUserMenu={showUserMenu}
                  setShowUserMenu={setShowUserMenu}
                  handleLogout={handleLogout}
                  unreadCount={unreadCount}
                  t={t}
                />
              </>
            ) : (
              <div className="flex items-center gap-2">
                <CrediscopBadge className="hidden sm:inline-flex" />
                <Link to="/connexion">
                  <button className="btn-ghost inline-flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium">
                    <LogIn className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">{t('nav.login')}</span>
                  </button>
                </Link>
                <Link to="/adhesion">
                  <button className="btn-gold inline-flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium">
                    <User className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">{t('footer.join')}</span>
                  </button>
                </Link>
              </div>
            )}

            {/* Mobile Menu Button */}
            <button
              className="lg:hidden p-2 text-white/80 rounded-lg hover:bg-white/[0.06]"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div 
            className="lg:hidden rounded-2xl mb-4 p-4 absolute left-4 right-4 top-16"
            style={{
              background: '#FFFFFF',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(212,175,55,0.36)',
              boxShadow: '0 24px 56px rgba(76,42,110,0.18)',
              maxHeight: 'calc(100vh - 100px)',
              overflowY: 'auto'
            }}
          >
            {isAuthenticated && user && (
              <div className="p-3 mb-3 rounded-xl bg-white/[0.04] border border-white/10">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white">{user.contact_name || t('nav.user')}</p>
                    <p className="text-xs text-white/50">{user.email}</p>
                  </div>
                  <CrediscopBadge />
                </div>
              </div>
            )}

            <nav className="flex flex-col gap-1">
              {navItems.filter(item => isAuthenticated || item.public).map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
                      isActive 
                        ? 'bg-[#D9B35A]/15 text-[#D9B35A]' 
                        : 'text-white/80 hover:bg-white/[0.06]'
                    }`}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label.startsWith('nav.') ? t(item.label) : item.label}
                  </Link>
                );
              })}
            </nav>

            {isAuthenticated && (nav.dropdown.buyer.length > 0 || nav.dropdown.admin.length > 0) && (
              <>
                <div className="mt-3 pt-3 border-t border-white/10">
                  <p className="text-[10px] uppercase tracking-wider text-white/40 px-4 pb-2 font-semibold">{t('nav.my_account')}</p>
                  {nav.dropdown.buyer.map((item) => {
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.href}
                        to={item.href}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-white/80 hover:bg-white/[0.06] rounded-xl"
                        onClick={() => setIsMobileMenuOpen(false)}
                      >
                        <Icon className="w-4 h-4" />
                        {item.label.startsWith('nav.') ? t(item.label) : item.label}
                      </Link>
                    );
                  })}
                </div>
                {nav.dropdown.vendor.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-white/10">
                    <p className="text-[10px] uppercase tracking-wider text-white/40 px-4 pb-2 font-semibold">{t('nav.vendor')}</p>
                    {nav.dropdown.vendor.map((item) => {
                      const Icon = item.icon;
                      return (
                        <Link
                          key={item.href}
                          to={item.href}
                          className="flex items-center gap-3 px-4 py-2.5 text-sm text-white/80 hover:bg-white/[0.06] rounded-xl"
                          onClick={() => setIsMobileMenuOpen(false)}
                        >
                          <Icon className="w-4 h-4" />
                          {item.label.startsWith('nav.') ? t(item.label) : item.label}
                        </Link>
                      );
                    })}
                  </div>
                )}
                {nav.dropdown.admin.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-white/10">
                    <p className="text-[10px] uppercase tracking-wider text-[#D9B35A]/70 px-4 pb-2 font-semibold">{t('nav.administration')}</p>
                    {nav.dropdown.admin.map((item) => {
                      const Icon = item.icon;
                      return (
                        <Link
                          key={item.href}
                          to={item.href}
                          className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#D9B35A] hover:bg-[#D9B35A]/10 rounded-xl"
                          onClick={() => setIsMobileMenuOpen(false)}
                        >
                          <Icon className="w-4 h-4" />
                          {item.label.startsWith('nav.') ? t(item.label) : item.label}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </>
            )}

            <div className="mt-4 pt-4 border-t border-white/10">
              {isAuthenticated ? (
                <button 
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    handleLogout();
                  }}
                  className="flex items-center gap-3 px-4 py-3 text-red-400 hover:bg-red-500/10 rounded-xl w-full"
                >
                  <LogOut className="w-4 h-4" />
                  {t('nav.logout')}
                </button>
              ) : (
                <div className="flex flex-col gap-2">
                  <Link to="/connexion" onClick={() => setIsMobileMenuOpen(false)}>
                    <button className="btn-ghost w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold">
                      <LogIn className="w-4 h-4" />
                      {t('nav.login')}
                    </button>
                  </Link>
                  <Link to="/adhesion" onClick={() => setIsMobileMenuOpen(false)}>
                    <button className="btn-gold w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold">
                      <User className="w-4 h-4" />
                      {t('footer.join')}
                    </button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Click outside to close */}
      {(showUserMenu || isMobileMenuOpen) && (
        <div 
          className="fixed inset-0 z-[-1]" 
          onClick={() => {
            setShowUserMenu(false);
            setIsMobileMenuOpen(false);
          }}
        />
      )}
    </header>
  );
};

export default NavBar;
