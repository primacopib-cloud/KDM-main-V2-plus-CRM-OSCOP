import { Link } from 'react-router-dom';
import {
  Sparkles, ArrowRight, ShoppingCart, Package, Wallet, FileText,
  CreditCard, LayoutDashboard, Store, ClipboardList, Users,
} from 'lucide-react';
import { authAPI } from '../services/api';

// Message de bienvenue + 3 actions prioritaires par espace de rôle
const SPACE_CONFIG = {
  buyer: {
    subtitle: 'Vos 3 actions prioritaires pour vos achats au tarif adhérent.',
    actions: [
      { href: '/catalogue', label: 'Parcourir le catalogue', icon: ShoppingCart },
      { href: '/commandes', label: 'Suivre mes commandes', icon: Package },
      { href: '/wallet', label: 'Recharger mes crédits', icon: Wallet },
    ],
  },
  vendor: {
    subtitle: 'Vos 3 actions prioritaires pour vendre sereinement.',
    actions: [
      { href: '/espace-vendeur?tab=products', label: 'Gérer mes produits', icon: Package },
      { href: '/espace-vendeur?tab=orders', label: 'Commandes reçues', icon: ShoppingCart },
      { href: '/espace-vendeur?tab=invoices', label: 'Mes factures', icon: FileText },
    ],
  },
  pass: {
    subtitle: 'Vos 3 actions prioritaires avec votre PASS LOLODRIVE.',
    actions: [
      { href: '/catalogue-lolodrive', label: 'Commander au relais', icon: ShoppingCart },
      { href: '/commandes', label: 'Suivre mes commandes', icon: Package },
      { href: '/espace-pass', label: 'Mon espace PASS', icon: CreditCard },
    ],
  },
  pos: {
    subtitle: 'Vos 3 actions prioritaires en caisse aujourd’hui.',
    actions: [
      { href: '/pos', label: 'Caisse & retraits', icon: CreditCard },
      { href: '/commandes', label: 'Commandes du point', icon: ClipboardList },
      { href: '/catalogue-lolodrive', label: 'Catalogue LOLODRIVE', icon: ShoppingCart },
    ],
  },
  gerant: {
    subtitle: 'Vos 3 actions prioritaires pour piloter votre relais.',
    actions: [
      { href: '/lolo-point/dashboard', label: 'Tableau de bord relais', icon: LayoutDashboard },
      { href: '/pos', label: 'Caisse POS', icon: CreditCard },
      { href: '/commandes', label: 'Réassort B2B', icon: Package },
    ],
  },
  cooper: {
    subtitle: 'Vos 3 actions prioritaires au service de la coopérative.',
    actions: [
      { href: '/espace-cooper', label: 'Adhésions & validations', icon: Users },
      { href: '/catalogue', label: 'Catalogue B2B', icon: ShoppingCart },
      { href: '/commandes', label: 'Commandes & transport', icon: Package },
    ],
  },
  investor: {
    subtitle: 'Vos 3 actions prioritaires pour suivre vos opérations.',
    actions: [
      { href: '/espace-investisseur', label: 'Mes opérations', icon: LayoutDashboard },
      { href: '/catalogue', label: 'Offres O’SCOP', icon: Store },
      { href: '/documents', label: 'Mes documents', icon: FileText },
    ],
  },
};

export const WelcomeBanner = ({ space, className = '' }) => {
  const cfg = SPACE_CONFIG[space];
  if (!cfg) return null;
  const user = authAPI.getCurrentUser();
  const name = user?.first_name || user?.company_name || (user?.email || '').split('@')[0] || 'membre';
  const hour = new Date().getHours();
  const greet = hour >= 18 || hour < 5 ? 'Bonsoir' : 'Bonjour';
  return (
    <div
      className={`rounded-[16px] border border-[#D9B35A]/30 p-4 sm:p-5 ${className}`}
      style={{ background: 'linear-gradient(135deg, rgba(217,179,90,0.12), rgba(255,255,255,0.03))' }}
      data-testid="welcome-banner"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className="w-10 h-10 rounded-xl bg-[#D9B35A]/15 border border-[#D9B35A]/30 flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-[#D9B35A]" />
          </span>
          <div className="min-w-0">
            <p className="text-base sm:text-lg font-bold text-white truncate" data-testid="welcome-greeting">
              {greet} {name}
            </p>
            <p className="text-xs text-white/60">{cfg.subtitle}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {cfg.actions.map((a, i) => (
            <Link
              key={a.href}
              to={a.href}
              data-testid={`welcome-action-${i}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-white/[0.06] border border-white/15 text-white/85 hover:bg-[#D9B35A]/20 hover:border-[#D9B35A]/40 hover:text-white transition-colors"
            >
              <a.icon className="w-3.5 h-3.5 text-[#D9B35A]" />
              {a.label}
              <ArrowRight className="w-3 h-3 opacity-50" />
            </Link>
          ))}
        </div>
      </div>
    </div>
    );
};
