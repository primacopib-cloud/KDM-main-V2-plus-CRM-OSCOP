import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import i18n from '@/i18n';

// Route configuration with labels and parent paths
const routeConfig = {
  '/': { label: 'nav.home', icon: Home },
  '/offres': { label: 'footer.our_offers', parent: '/' },
  '/connexion': { label: 'nav.login', parent: '/' },
  '/inscription': { label: 'breadcrumb.inscription', parent: '/' },
  '/adhesion': { label: 'footer.join', parent: '/' },
  '/dashboard': { label: 'buyer.tableau_de_bord', parent: '/' },
  '/espace-acheteur': { label: 'breadcrumb.espace_acheteur', parent: '/' },
  '/catalogue': { label: 'nav.catalog', parent: '/espace-acheteur' },
  '/commandes': { label: 'buyer.commandes', parent: '/espace-acheteur' },
  '/wallet': { label: 'Wallet', parent: '/espace-acheteur' },
  '/documents': { label: 'nav.documents', parent: '/espace-acheteur' },
  '/checkout': { label: 'breadcrumb.paiement', parent: '/catalogue' },
  '/espace-vendeur': { label: 'nav.vendor_space', parent: '/' },
  '/superadmin': { label: 'nav.super_admin', parent: '/' },
  '/admin-v2': { label: 'nav.admin_orgs', parent: '/superadmin' },
  '/admin/produits': { label: 'nav.product_validation', parent: '/superadmin' },
  '/legal': { label: 'footer.legal_docs', parent: '/' },
  '/legal/cgv-kdmarche': { label: 'footer.cgv_kdmarche', parent: '/legal' },
  '/legal/cg-oscop': { label: 'footer.cg_oscop', parent: '/legal' },
  '/legal/convention': { label: 'footer.convention', parent: '/legal' },
  '/legal/charte-ess': { label: 'footer.ess_charter', parent: '/legal' },
  '/signature': { label: 'breadcrumb.signature', parent: '/espace-acheteur' },
  '/bon-de-commande': { label: 'breadcrumb.bon_commande', parent: '/catalogue' },
  '/bon-de-commande-dynamique': { label: 'breadcrumb.bon_commande', parent: '/catalogue' },
  '/fiche-produit': { label: 'breadcrumb.fiche_produit', parent: '/catalogue' },
  '/statistiques': { label: 'breadcrumb.statistiques', parent: '/espace-acheteur' },
};

// Build breadcrumb path from current route
const buildBreadcrumbPath = (pathname) => {
  const path = [];
  let currentPath = pathname;
  
  // Handle dynamic routes (e.g., /legal/:docId)
  if (pathname.startsWith('/legal/') && !routeConfig[pathname]) {
    const docId = pathname.split('/')[2];
    const docLabels = {
      'cgv-kdmarche': i18n.t('footer.cgv_kdmarche'),
      'cg-oscop': i18n.t('footer.cg_oscop'),
      'convention': i18n.t('footer.convention'),
      'charte-ess': i18n.t('footer.ess_charter'),
    };
    path.unshift({
      path: pathname,
      label: docLabels[docId] || docId,
      isLast: true
    });
    currentPath = '/legal';
  }
  
  while (currentPath && routeConfig[currentPath]) {
    const config = routeConfig[currentPath];
    path.unshift({
      path: currentPath,
      label: i18n.t(config.label),
      icon: config.icon,
      isLast: path.length === 0
    });
    currentPath = config.parent;
  }
  
  return path;
};

export default function Breadcrumb({ 
  className = '', 
  variant = 'dark', // 'dark' or 'light'
  customItems = null // Override automatic breadcrumb
}) {
  const location = useLocation();
  const items = customItems || buildBreadcrumbPath(location.pathname);
  
  // Don't show breadcrumb on home page
  if (location.pathname === '/' || items.length <= 1) {
    return null;
  }
  
  const isDark = variant === 'dark';
  
  return (
    <nav 
      className={`flex items-center gap-1 text-xs ${className}`}
      aria-label="Fil d'Ariane"
    >
      {items.map((item, index) => {
        const Icon = item.icon;
        const isLast = index === items.length - 1;
        
        return (
          <React.Fragment key={item.path}>
            {index > 0 && (
              <ChevronRight 
                className={`w-3 h-3 flex-shrink-0 ${
                  isDark ? 'text-white/30' : 'text-gray-400'
                }`} 
              />
            )}
            
            {isLast ? (
              <span 
                className={`flex items-center gap-1 font-medium ${
                  isDark ? 'text-white/90' : 'text-gray-900'
                }`}
              >
                {Icon && <Icon className="w-3 h-3" />}
                {item.label}
              </span>
            ) : (
              <Link
                to={item.path}
                className={`flex items-center gap-1 transition-colors ${
                  isDark 
                    ? 'text-white/50 hover:text-white/80' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {Icon && <Icon className="w-3 h-3" />}
                {item.label}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

// Compact version for headers
export function BreadcrumbCompact({ className = '', variant = 'dark' }) {
  const location = useLocation();
  const items = buildBreadcrumbPath(location.pathname);
  
  if (location.pathname === '/' || items.length <= 1) {
    return null;
  }
  
  const isDark = variant === 'dark';
  const lastItem = items[items.length - 1];
  const parentItem = items.length > 1 ? items[items.length - 2] : null;
  
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {parentItem && (
        <Link
          to={parentItem.path}
          className={`flex items-center gap-1 text-xs transition-colors ${
            isDark 
              ? 'text-white/50 hover:text-white/80' 
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          {parentItem.icon && <parentItem.icon className="w-3 h-3" />}
          {parentItem.label}
        </Link>
      )}
      {parentItem && (
        <ChevronRight className={`w-3 h-3 ${isDark ? 'text-white/30' : 'text-gray-400'}`} />
      )}
      <span className={`text-xs font-medium ${isDark ? 'text-white/90' : 'text-gray-900'}`}>
        {lastItem.label}
      </span>
    </div>
  );
}

// Breadcrumb with background pill style
export function BreadcrumbPill({ className = '' }) {
  const location = useLocation();
  const items = buildBreadcrumbPath(location.pathname);
  
  if (location.pathname === '/' || items.length <= 1) {
    return null;
  }
  
  return (
    <nav 
      className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs ${className}`}
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.08)'
      }}
      aria-label="Fil d'Ariane"
    >
      {items.map((item, index) => {
        const Icon = item.icon;
        const isLast = index === items.length - 1;
        
        return (
          <React.Fragment key={item.path}>
            {index > 0 && (
              <ChevronRight className="w-3 h-3 text-white/30 flex-shrink-0" />
            )}
            
            {isLast ? (
              <span className="flex items-center gap-1 text-[#D9B35A] font-medium">
                {Icon && <Icon className="w-3 h-3" />}
                {item.label}
              </span>
            ) : (
              <Link
                to={item.path}
                className="flex items-center gap-1 text-white/60 hover:text-white/90 transition-colors"
              >
                {Icon && <Icon className="w-3 h-3" />}
                {item.label}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
