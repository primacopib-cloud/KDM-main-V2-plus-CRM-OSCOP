import { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';

// Route labels for display
const routeLabels = {
  '/': 'Accueil',
  '/offres': 'Offres',
  '/connexion': 'Connexion',
  '/inscription': 'Inscription',
  '/adhesion': 'Adhésion',
  '/dashboard': 'Tableau de bord',
  '/espace-acheteur': 'Espace Acheteur',
  '/catalogue': 'Catalogue',
  '/commandes': 'Commandes',
  '/wallet': 'Wallet',
  '/documents': 'Documents',
  '/checkout': 'Paiement',
  '/espace-vendeur': 'Espace Vendeur',
  '/superadmin': 'Super Admin',
  '/admin-v2': 'Admin Organisations',
  '/admin/produits': 'Validation Produits',
  '/legal': 'Documents Légaux',
  '/legal/cgv-kdmarche': 'CGV KDMARCHE',
  '/legal/cg-oscop': 'CG O\'SCOP',
  '/legal/convention': 'Convention',
  '/legal/charte-ess': 'Charte ESS',
  '/signature': 'Signature',
  '/bon-de-commande': 'Bon de commande',
  '/bon-de-commande-dynamique': 'Bon de commande',
  '/fiche-produit': 'Fiche produit',
  '/statistiques': 'Statistiques',
};

// Route icons mapping
const routeIcons = {
  '/': 'Home',
  '/offres': 'CreditCard',
  '/connexion': 'LogIn',
  '/espace-acheteur': 'LayoutDashboard',
  '/catalogue': 'ShoppingCart',
  '/commandes': 'Package',
  '/wallet': 'Wallet',
  '/documents': 'FileText',
  '/checkout': 'CreditCard',
  '/espace-vendeur': 'Store',
  '/superadmin': 'Shield',
  '/admin-v2': 'Building2',
  '/legal': 'Scale',
};

const STORAGE_KEY = 'nav_history';
const MAX_HISTORY_ITEMS = 10;

// Get label for a path
export const getRouteLabel = (path) => {
  // Direct match
  if (routeLabels[path]) return routeLabels[path];
  
  // Check for dynamic routes (e.g., /fiche-produit/123)
  const basePath = '/' + path.split('/').filter(Boolean)[0];
  if (routeLabels[basePath]) return routeLabels[basePath];
  
  // Fallback to path name
  const pathName = path.split('/').filter(Boolean).pop() || 'Page';
  return pathName.charAt(0).toUpperCase() + pathName.slice(1).replace(/-/g, ' ');
};

// Get icon name for a path
export const getRouteIcon = (path) => {
  if (routeIcons[path]) return routeIcons[path];
  const basePath = '/' + path.split('/').filter(Boolean)[0];
  return routeIcons[basePath] || 'FileText';
};

// Custom hook for navigation history
export function useNavigationHistory() {
  const location = useLocation();
  const [history, setHistory] = useState([]);

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored) {
        setHistory(JSON.parse(stored));
      }
    } catch (e) {
      console.error('Failed to load navigation history:', e);
    }
  }, []);

  // Add current page to history when location changes
  useEffect(() => {
    const currentPath = location.pathname;
    
    // Skip certain paths
    if (currentPath === '/connexion' || currentPath === '/inscription') {
      return;
    }

    setHistory(prev => {
      // Remove duplicates of current path
      const filtered = prev.filter(item => item.path !== currentPath);
      
      // Create new history entry
      const newEntry = {
        path: currentPath,
        label: getRouteLabel(currentPath),
        icon: getRouteIcon(currentPath),
        timestamp: Date.now(),
      };
      
      // Add to beginning and limit size
      const newHistory = [newEntry, ...filtered].slice(0, MAX_HISTORY_ITEMS);
      
      // Save to localStorage
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory));
      } catch (e) {
        console.error('Failed to save navigation history:', e);
      }
      
      return newHistory;
    });
  }, [location.pathname]);

  // Clear history
  const clearHistory = useCallback(() => {
    setHistory([]);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  // Remove single item
  const removeItem = useCallback((path) => {
    setHistory(prev => {
      const newHistory = prev.filter(item => item.path !== path);
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory));
      return newHistory;
    });
  }, []);

  // Get recent history (excluding current page)
  const getRecentHistory = useCallback((limit = 5) => {
    return history
      .filter(item => item.path !== location.pathname)
      .slice(0, limit);
  }, [history, location.pathname]);

  return {
    history,
    recentHistory: getRecentHistory(),
    clearHistory,
    removeItem,
    currentPath: location.pathname,
  };
}

export default useNavigationHistory;
