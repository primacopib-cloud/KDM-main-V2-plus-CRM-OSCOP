import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

// Route configuration with labels and parent paths
const routeConfig = {
  '/': { label: 'Accueil', icon: Home },
  '/offres': { label: 'Offres', parent: '/' },
  '/connexion': { label: 'Connexion', parent: '/' },
  '/inscription': { label: 'Inscription', parent: '/' },
  '/adhesion': { label: 'Adhésion', parent: '/' },
  '/dashboard': { label: 'Tableau de bord', parent: '/' },
  '/espace-acheteur': { label: 'Espace Acheteur', parent: '/' },
  '/catalogue': { label: 'Catalogue', parent: '/espace-acheteur' },
  '/commandes': { label: 'Commandes', parent: '/espace-acheteur' },
  '/wallet': { label: 'Wallet', parent: '/espace-acheteur' },
  '/documents': { label: 'Documents', parent: '/espace-acheteur' },
  '/checkout': { label: 'Paiement', parent: '/catalogue' },
  '/espace-vendeur': { label: 'Espace Vendeur', parent: '/' },
  '/superadmin': { label: 'Super Admin', parent: '/' },
  '/admin-v2': { label: 'Admin Organisations', parent: '/superadmin' },
  '/admin/produits': { label: 'Validation Produits', parent: '/superadmin' },
  '/legal': { label: 'Documents Légaux', parent: '/' },
  '/legal/cgv-kdmarche': { label: 'CGV KDMARCHE', parent: '/legal' },
  '/legal/cg-oscop': { label: 'CG O\'SCOP', parent: '/legal' },
  '/legal/convention': { label: 'Convention', parent: '/legal' },
  '/legal/charte-ess': { label: 'Charte ESS', parent: '/legal' },
  '/signature': { label: 'Signature', parent: '/espace-acheteur' },
  '/bon-de-commande': { label: 'Bon de commande', parent: '/catalogue' },
  '/bon-de-commande-dynamique': { label: 'Bon de commande', parent: '/catalogue' },
  '/fiche-produit': { label: 'Fiche produit', parent: '/catalogue' },
  '/statistiques': { label: 'Statistiques', parent: '/espace-acheteur' },
};

// Build breadcrumb path from current route
const buildBreadcrumbPath = (pathname) => {
  const path = [];
  let currentPath = pathname;
  
  // Handle dynamic routes (e.g., /legal/:docId)
  if (pathname.startsWith('/legal/') && !routeConfig[pathname]) {
    const docId = pathname.split('/')[2];
    const docLabels = {
      'cgv-kdmarche': 'CGV KDMARCHE',
      'cg-oscop': 'CG O\'SCOP',
      'convention': 'Convention',
      'charte-ess': 'Charte ESS',
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
      label: config.label,
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
