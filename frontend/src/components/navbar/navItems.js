import {
  LayoutDashboard, ShoppingCart, Package, FileText,
  Wallet, Users, Shield, BarChart3,
  Store, Building2, MapPin, CreditCard, Home, Truck, HeartHandshake, Server, Settings, Plug, Heart,
} from 'lucide-react';

export const getNavItems = (userRole, isAdmin) => {
  // Top bar: keep it lean — 4 public + 2 member shortcuts.
  const baseItems = [
    { href: '/', label: 'nav.home', icon: Home, public: true },
    { href: '/tarifs', label: 'nav.pro_access', icon: CreditCard, public: true },
  ];

  // Member-only shortcuts kept in top bar (per product decision).
  const memberShortcuts = [
    { href: '/espace-acheteur', label: 'nav.my_space', icon: LayoutDashboard },
    { href: '/catalogue', label: 'nav.catalog', icon: ShoppingCart },
  ];

  // Everything below is available via the user-avatar dropdown, not the top bar.
  return {
    topBar: baseItems.concat(userRole || isAdmin ? memberShortcuts : []),
    dropdown: {
      buyer: [
        { href: '/espace-acheteur', label: 'nav.my_space', icon: LayoutDashboard },
        { href: '/commandes', label: 'nav.my_orders', icon: Package },
        { href: '/wallet', label: 'nav.wallet', icon: Wallet },
        { href: '/documents', label: 'nav.documents', icon: FileText },
        { href: '/listes-achats', label: 'nav.shopping_lists', icon: ShoppingCart },
        { href: '/alertes-favoris', label: 'nav.favorite_alerts', icon: Heart },
      ],
      vendor: userRole === 'vendor' || isAdmin ? [
        { href: '/espace-vendeur', label: 'nav.vendor_space', icon: Store },
      ] : [],
      admin: isAdmin ? [
        { href: '/superadmin', label: 'nav.super_admin', icon: Shield },
        { href: '/admin/plans', label: 'nav.plans_credits', icon: CreditCard },
        { href: '/admin-v2', label: 'nav.admin_orgs', icon: Building2 },
        { href: '/admin/produits', label: 'nav.product_validation', icon: Package },
        { href: '/admin/stripe-reconciliation', label: 'nav.stripe_recon', icon: CreditCard },
        { href: '/admin/connecteurs', label: 'nav.connectors', icon: Plug },
        { href: '/admin/ged-bridge', label: 'nav.ged_bridge', icon: Server },
        { href: '/admin/finance-bridge', label: 'nav.finance_bridge', icon: CreditCard },
      ] : [],
    },
  };
};

