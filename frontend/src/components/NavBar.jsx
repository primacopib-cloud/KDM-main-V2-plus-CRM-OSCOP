import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { partners } from '../data/mock';
import { 
  Menu, X, User, LogIn, LogOut, 
  LayoutDashboard, ShoppingCart, Package, FileText, 
  Wallet, Settings, Users, Shield, BarChart3,
  Store, Building2, ChevronDown, Bell, Search,
  FileSignature, MapPin, CreditCard, Home, Heart, Truck, HeartHandshake
} from 'lucide-react';
import { authAPI } from '../services/api';
import { useNotificationWebSocket, ConnectionStatus } from './NotificationToast';
import NavigationHistoryDropdown from './NavigationHistoryDropdown';
import QuickShortcuts from './QuickShortcuts';
import { useFavorites } from './FavoriteButton';
import LanguageSwitcher from './LanguageSwitcher';

// Favorites nav button with count
function FavoritesNavButton() {
  const { count } = useFavorites();
  
  return (
    <Link 
      to="/favoris" 
      className="relative p-2 rounded-lg hover:bg-white/[0.06] transition-colors"
      data-testid="favorites-nav-link"
      title="Mes favoris"
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
const getNavItems = (userRole, isAdmin) => {
  const baseItems = [
    { href: '/', label: 'Accueil', icon: Home, public: true },
    { href: '/logiscop', label: "LOGI'SCOP", icon: Truck, public: true, accent: '#0B4D87' },
    { href: '/oscop', label: "O'SCOP", icon: HeartHandshake, public: true, accent: '#8CC63E' },
    { href: '/offres', label: 'Offres', icon: CreditCard, public: true },
  ];

  const buyerItems = [
    { href: '/espace-acheteur', label: 'Mon Espace', icon: LayoutDashboard },
    { href: '/catalogue', label: 'Catalogue', icon: ShoppingCart },
    { href: '/commandes', label: 'Commandes', icon: Package },
    { href: '/wallet', label: 'Wallet', icon: Wallet },
    { href: '/documents', label: 'Documents', icon: FileText },
    { href: '/listes-achats', label: 'Listes d\'achats', icon: ShoppingCart },
  ];

  const vendorItems = [
    { href: '/espace-vendeur', label: 'Espace Vendeur', icon: Store },
  ];

  const adminItems = [
    { href: '/superadmin', label: 'Super Admin', icon: Shield },
    { href: '/admin/plans', label: 'Plans & Crédits', icon: CreditCard },
    { href: '/admin-v2', label: 'Admin Orgs', icon: Building2 },
    { href: '/admin/produits', label: 'Validation Produits', icon: Package },
  ];

  if (isAdmin) {
    return [...baseItems, ...buyerItems, ...vendorItems, ...adminItems];
  }

  if (userRole === 'vendor') {
    return [...baseItems, ...vendorItems, ...buyerItems];
  }

  return [...baseItems, ...buyerItems];
};

const NavBar = ({ variant = 'default' }) => {
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

  const navItems = getNavItems(user?.role, isAdmin);
  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <header 
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300`}
      style={{
        background: isScrolled ? 'rgba(255,253,247,0.96)' : 'rgba(255,253,247,0.86)',
        backdropFilter: 'blur(14px)',
        borderBottom: '1px solid rgba(212,175,55,0.32)',
        boxShadow: isScrolled ? '0 8px 24px rgba(11,77,135,0.06)' : 'none'
      }}
    >
      <div className="max-w-[1400px] mx-auto px-4 lg:px-6">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-3 flex-shrink-0">
            <div className="flex items-center gap-2">
              <img 
                src={partners.kdmarche.logo} 
                alt="KDMARCHE" 
                className="h-8 w-auto object-contain"
                style={{ filter: 'drop-shadow(0 1px 4px rgba(217,179,90,0.3))' }}
              />
              <span className="text-white/30 text-sm hidden sm:inline">×</span>
              <img 
                src={partners.oscop.logo} 
                alt="O'SCOP" 
                className="h-5 w-auto object-contain hidden sm:block"
                style={{ filter: 'drop-shadow(0 1px 4px rgba(87,209,154,0.3))' }}
              />
            </div>
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
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Right Section */}
          <div className="flex items-center gap-2">
            <LanguageSwitcher className="hidden md:flex" />
            {isAuthenticated ? (
              <>
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

                {/* User Menu */}
                <div className="relative">
                  <button 
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/[0.06] transition-colors"
                  >
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#D9B35A] to-[#57D19A] flex items-center justify-center">
                      <User className="w-3.5 h-3.5 text-black" />
                    </div>
                    <span className="text-sm text-white/90 hidden md:block max-w-[120px] truncate">
                      {user?.contact_name || user?.email?.split('@')[0] || 'Mon compte'}
                    </span>
                    <ChevronDown className="w-3.5 h-3.5 text-white/50" />
                  </button>

                  {showUserMenu && (
                    <div 
                      className="absolute right-0 mt-2 w-56 rounded-xl overflow-hidden shadow-xl z-50"
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid rgba(212,175,55,0.34)',
                        boxShadow: '0 18px 48px rgba(11,77,135,0.18), 0 4px 12px rgba(31,42,58,0.08)',
                        backdropFilter: 'blur(20px)'
                      }}
                    >
                      <div className="p-3 border-b border-white/10">
                        <p className="text-sm font-medium text-white">{user?.contact_name || 'Utilisateur'}</p>
                        <p className="text-xs text-white/50 truncate">{user?.email}</p>
                        {user?.company_name && (
                          <p className="text-xs text-[#D9B35A] mt-1">{user.company_name}</p>
                        )}
                      </div>
                      <div className="p-2">
                        <Link 
                          to="/espace-acheteur" 
                          className="flex items-center gap-2 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] rounded-lg"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <LayoutDashboard className="w-4 h-4" />
                          Mon Espace
                        </Link>
                        <Link 
                          to="/commandes" 
                          className="flex items-center gap-2 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] rounded-lg"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Package className="w-4 h-4" />
                          Mes Commandes
                        </Link>
                        <Link 
                          to="/wallet" 
                          className="flex items-center gap-2 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] rounded-lg"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Wallet className="w-4 h-4" />
                          Wallet ({user?.credits || 0} crédits)
                        </Link>
                        <Link 
                          to="/legal" 
                          className="flex items-center gap-2 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] rounded-lg"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <FileText className="w-4 h-4" />
                          Documents légaux
                        </Link>
                        <Link 
                          to="/notifications" 
                          className="flex items-center gap-2 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] rounded-lg"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Bell className="w-4 h-4" />
                          Notifications
                        </Link>
                        {isAdmin && (
                          <>
                            <div className="my-2 border-t border-white/10" />
                            <Link 
                              to="/superadmin" 
                              className="flex items-center gap-2 px-3 py-2 text-sm text-[#D9B35A] hover:bg-[#D9B35A]/10 rounded-lg"
                              onClick={() => setShowUserMenu(false)}
                            >
                              <Shield className="w-4 h-4" />
                              Super Admin
                            </Link>
                          </>
                        )}
                      </div>
                      <div className="p-2 border-t border-white/10">
                        <button 
                          onClick={() => {
                            setShowUserMenu(false);
                            handleLogout();
                          }}
                          className="flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-lg w-full"
                        >
                          <LogOut className="w-4 h-4" />
                          Déconnexion
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/connexion">
                  <button className="btn-ghost inline-flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium">
                    <LogIn className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Connexion</span>
                  </button>
                </Link>
                <Link to="/adhesion">
                  <button className="btn-gold inline-flex items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium">
                    <User className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Adhérer</span>
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
              boxShadow: '0 24px 56px rgba(11,77,135,0.18)',
              maxHeight: 'calc(100vh - 100px)',
              overflowY: 'auto'
            }}
          >
            {isAuthenticated && user && (
              <div className="p-3 mb-3 rounded-xl bg-white/[0.04] border border-white/10">
                <p className="text-sm font-medium text-white">{user.contact_name || 'Utilisateur'}</p>
                <p className="text-xs text-white/50">{user.email}</p>
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
                    {item.label}
                  </Link>
                );
              })}
            </nav>

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
                  Déconnexion
                </button>
              ) : (
                <div className="flex flex-col gap-2">
                  <Link to="/connexion" onClick={() => setIsMobileMenuOpen(false)}>
                    <button className="btn-ghost w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold">
                      <LogIn className="w-4 h-4" />
                      Connexion
                    </button>
                  </Link>
                  <Link to="/adhesion" onClick={() => setIsMobileMenuOpen(false)}>
                    <button className="btn-gold w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold">
                      <User className="w-4 h-4" />
                      Adhérer
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
