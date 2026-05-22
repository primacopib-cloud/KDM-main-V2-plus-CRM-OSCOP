import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Home, ShoppingCart, Package, Wallet, FileText, 
  Store, Shield, LayoutDashboard, ArrowLeft
} from 'lucide-react';

const quickNavItems = [
  { href: '/', label: 'Accueil', icon: Home },
  { href: '/espace-acheteur', label: 'Mon Espace', icon: LayoutDashboard },
  { href: '/catalogue', label: 'Catalogue', icon: ShoppingCart },
  { href: '/commandes', label: 'Commandes', icon: Package },
  { href: '/wallet', label: 'Wallet', icon: Wallet },
  { href: '/espace-vendeur', label: 'Vendeur', icon: Store },
  { href: '/superadmin', label: 'Admin', icon: Shield },
];

export default function QuickNav({ showBack = true, backTo = '/espace-acheteur', backLabel = 'Retour' }) {
  const location = useLocation();

  return (
    <div 
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 px-2 py-1.5 rounded-full flex items-center gap-1"
      style={{
        background: 'rgba(10,15,25,0.95)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255,255,255,0.1)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
      }}
    >
      {showBack && (
        <>
          <Link 
            to={backTo}
            className="flex items-center gap-1.5 px-3 py-2 rounded-full text-white/60 hover:text-white hover:bg-white/10 transition-all text-xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{backLabel}</span>
          </Link>
          <div className="w-px h-5 bg-white/10 mx-1" />
        </>
      )}
      
      {quickNavItems.map((item) => {
        const Icon = item.icon;
        const isActive = location.pathname === item.href;
        return (
          <Link
            key={item.href}
            to={item.href}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-full transition-all text-xs ${
              isActive 
                ? 'bg-[#D9B35A]/20 text-[#D9B35A]' 
                : 'text-white/60 hover:text-white hover:bg-white/10'
            }`}
            title={item.label}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="hidden md:inline">{item.label}</span>
          </Link>
        );
      })}
    </div>
  );
}
