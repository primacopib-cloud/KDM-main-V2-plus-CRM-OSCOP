import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  History, X, Clock, ChevronRight, Trash2,
  Home, ShoppingCart, Package, Wallet, FileText, 
  Store, Shield, Building2, CreditCard, LayoutDashboard,
  Scale, LogIn, Settings
} from 'lucide-react';
import { useNavigationHistory } from '../hooks/useNavigationHistory';

// Icon mapping
const iconComponents = {
  Home, ShoppingCart, Package, Wallet, FileText, 
  Store, Shield, Building2, CreditCard, LayoutDashboard,
  Scale, LogIn, Settings
};

const getIconComponent = (iconName) => {
  return iconComponents[iconName] || FileText;
};

// Format relative time
const formatRelativeTime = (timestamp) => {
  const now = Date.now();
  const diff = now - timestamp;
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return "À l'instant";
  if (minutes < 60) return `Il y a ${minutes} min`;
  if (hours < 24) return `Il y a ${hours}h`;
  if (days < 7) return `Il y a ${days}j`;
  return new Date(timestamp).toLocaleDateString('fr-FR');
};

export default function NavigationHistoryDropdown({ variant = 'dark' }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const { recentHistory, clearHistory, removeItem, currentPath } = useNavigationHistory();
  
  const isDark = variant === 'dark';

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close on escape
  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key === 'Escape') setIsOpen(false);
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  const hasHistory = recentHistory.length > 0;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-all ${
          isDark 
            ? 'text-white/60 hover:text-white/90 hover:bg-white/[0.06]' 
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
        } ${isOpen ? (isDark ? 'bg-white/[0.08] text-white/90' : 'bg-gray-100 text-gray-900') : ''}`}
        title="Historique de navigation"
      >
        <History className="w-4 h-4" />
        {hasHistory && (
          <span 
            className={`w-1.5 h-1.5 rounded-full ${
              isDark ? 'bg-[#D9B35A]' : 'bg-amber-500'
            }`}
          />
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div 
          className={`absolute right-0 mt-2 w-72 rounded-xl overflow-hidden shadow-xl z-50 ${
            isDark 
              ? 'bg-[#0f141f] border border-white/10' 
              : 'bg-white border border-gray-200'
          }`}
          style={{ backdropFilter: 'blur(20px)' }}
        >
          {/* Header */}
          <div 
            className={`px-4 py-3 flex items-center justify-between ${
              isDark ? 'border-b border-white/10' : 'border-b border-gray-100'
            }`}
          >
            <div className="flex items-center gap-2">
              <Clock className={`w-4 h-4 ${isDark ? 'text-[#D9B35A]' : 'text-amber-500'}`} />
              <span className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Historique récent
              </span>
            </div>
            {hasHistory && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  clearHistory();
                }}
                className={`p-1 rounded transition-colors ${
                  isDark 
                    ? 'text-white/40 hover:text-red-400 hover:bg-red-500/10' 
                    : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
                }`}
                title="Effacer l'historique"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* History List */}
          <div className="max-h-80 overflow-y-auto">
            {hasHistory ? (
              <div className="py-1">
                {recentHistory.map((item, index) => {
                  const IconComponent = getIconComponent(item.icon);
                  
                  return (
                    <div 
                      key={`${item.path}-${index}`}
                      className={`group relative ${
                        isDark ? 'hover:bg-white/[0.04]' : 'hover:bg-gray-50'
                      }`}
                    >
                      <Link
                        to={item.path}
                        onClick={() => setIsOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5"
                      >
                        <div 
                          className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                            isDark ? 'bg-white/[0.06]' : 'bg-gray-100'
                          }`}
                        >
                          <IconComponent 
                            className={`w-4 h-4 ${isDark ? 'text-white/60' : 'text-gray-500'}`} 
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-medium truncate ${
                            isDark ? 'text-white/90' : 'text-gray-900'
                          }`}>
                            {item.label}
                          </p>
                          <p className={`text-xs truncate ${
                            isDark ? 'text-white/40' : 'text-gray-400'
                          }`}>
                            {formatRelativeTime(item.timestamp)}
                          </p>
                        </div>
                        <ChevronRight 
                          className={`w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity ${
                            isDark ? 'text-white/40' : 'text-gray-400'
                          }`} 
                        />
                      </Link>
                      
                      {/* Remove button */}
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          removeItem(item.path);
                        }}
                        className={`absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded opacity-0 group-hover:opacity-100 transition-all ${
                          isDark 
                            ? 'text-white/30 hover:text-red-400 hover:bg-red-500/10' 
                            : 'text-gray-300 hover:text-red-500 hover:bg-red-50'
                        }`}
                        title="Retirer de l'historique"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className={`px-4 py-8 text-center ${isDark ? 'text-white/40' : 'text-gray-400'}`}>
                <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Aucun historique</p>
                <p className="text-xs mt-1">Vos pages visitées apparaîtront ici</p>
              </div>
            )}
          </div>

          {/* Footer */}
          {hasHistory && (
            <div 
              className={`px-4 py-2 ${
                isDark ? 'bg-white/[0.02] border-t border-white/10' : 'bg-gray-50 border-t border-gray-100'
              }`}
            >
              <p className={`text-xs text-center ${isDark ? 'text-white/30' : 'text-gray-400'}`}>
                {recentHistory.length} page{recentHistory.length > 1 ? 's' : ''} récente{recentHistory.length > 1 ? 's' : ''}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
