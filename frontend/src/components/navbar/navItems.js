import {
  LayoutDashboard, ShoppingCart, Package, FileText,
  Wallet, Users, Shield, BarChart3,
  Store, Building2, MapPin, CreditCard, Home, Truck, HeartHandshake, Server, Settings,
} from 'lucide-react';

export const getNavItems = (userRole, isAdmin) => {
  // Top bar: keep it lean — 4 public + 2 member shortcuts.
  const baseItems = [
    { href: '/', label: 'Accueil', icon: Home, public: true },
    { href: '/logiscop', label: "LOGI'SCOP", icon: Truck, public: true, accent: '#5B2E8C' },
    { href: '/oscop', label: "O'SCOP", icon: HeartHandshake, public: true, accent: '#8CC63E' },
    { href: '/tarifs', label: 'Accès Pro Mutualisé', icon: CreditCard, public: true },
  ];

  // Member-only shortcuts kept in top bar (per product decision).
  const memberShortcuts = [
    { href: '/espace-acheteur', label: 'Mon Espace', icon: LayoutDashboard },
    { href: '/catalogue', label: 'Catalogue', icon: ShoppingCart },
  ];

  // Everything below is available via the user-avatar dropdown, not the top bar.
  return {
    topBar: baseItems.concat(userRole || isAdmin ? memberShortcuts : []),
    dropdown: {
      buyer: [
        { href: '/espace-acheteur', label: 'Mon Espace', icon: LayoutDashboard },
        { href: '/commandes', label: 'Mes Commandes', icon: Package },
        { href: '/wallet', label: 'Wallet', icon: Wallet },
        { href: '/documents', label: 'Documents', icon: FileText },
        { href: '/listes-achats', label: 'Listes d\'achats', icon: ShoppingCart },
      ],
      vendor: userRole === 'vendor' || isAdmin ? [
        { href: '/espace-vendeur', label: 'Espace Vendeur', icon: Store },
      ] : [],
      admin: isAdmin ? [
        { href: '/superadmin', label: 'Super Admin', icon: Shield },
        { href: '/admin/plans', label: 'Plans & Crédits', icon: CreditCard },
        { href: '/admin-v2', label: 'Admin Orgs', icon: Building2 },
        { href: '/admin/produits', label: 'Validation Produits', icon: Package },
        { href: '/admin/stripe-reconciliation', label: 'Réconciliation Stripe', icon: CreditCard },
        { href: '/admin/ged-bridge', label: 'Pont GED ESS', icon: Server },
        { href: '/admin/finance-bridge', label: 'Pont Finance', icon: CreditCard },
      ] : [],
    },
  };
};

