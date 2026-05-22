import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { Heart } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Context for favorites state management
const FavoritesContext = createContext(null);

export function FavoritesProvider({ children }) {
  const [favoriteIds, setFavoriteIds] = useState(new Set());
  const [loading, setLoading] = useState(true);

  const getAuthHeaders = useCallback(() => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  }, []);

  const fetchFavoriteIds = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/user-prefs/favorites/ids`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setFavoriteIds(new Set(data.product_ids || []));
      }
    } catch (error) {
      console.error('Error fetching favorites:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFavoriteIds();
  }, [fetchFavoriteIds]);

  const toggleFavorite = useCallback(async (productId, productName) => {
    const token = localStorage.getItem('token');
    if (!token) {
      toast.error('Veuillez vous connecter pour ajouter des favoris');
      return false;
    }

    try {
      const res = await fetch(`${API_URL}/api/user-prefs/favorites/${productId}/toggle`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (res.ok) {
        const data = await res.json();
        setFavoriteIds(prev => {
          const newSet = new Set(prev);
          if (data.is_favorite) {
            newSet.add(productId);
            toast.success(`${productName || 'Produit'} ajouté aux favoris`, {
              icon: '❤️'
            });
          } else {
            newSet.delete(productId);
            toast.info(`${productName || 'Produit'} retiré des favoris`);
          }
          return newSet;
        });
        return data.is_favorite;
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
      toast.error('Erreur lors de la mise à jour des favoris');
    }
    return false;
  }, [getAuthHeaders]);

  const isFavorite = useCallback((productId) => {
    return favoriteIds.has(productId);
  }, [favoriteIds]);

  const clearAllFavorites = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/user-prefs/favorites`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        setFavoriteIds(new Set());
        toast.info('Tous les favoris ont été supprimés');
      }
    } catch (error) {
      console.error('Error clearing favorites:', error);
    }
  }, [getAuthHeaders]);

  return (
    <FavoritesContext.Provider value={{
      favoriteIds,
      loading,
      toggleFavorite,
      isFavorite,
      clearAllFavorites,
      refreshFavorites: fetchFavoriteIds,
      count: favoriteIds.size
    }}>
      {children}
    </FavoritesContext.Provider>
  );
}

export function useFavorites() {
  const context = useContext(FavoritesContext);
  if (!context) {
    throw new Error('useFavorites must be used within a FavoritesProvider');
  }
  return context;
}

// Standalone favorite button component
export function FavoriteButton({ 
  productId, 
  productName,
  size = 'md',
  showLabel = false,
  className = ''
}) {
  const { isFavorite, toggleFavorite, loading } = useFavorites();
  const [isAnimating, setIsAnimating] = useState(false);
  
  const favorite = isFavorite(productId);

  const handleClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    setIsAnimating(true);
    await toggleFavorite(productId, productName);
    setTimeout(() => setIsAnimating(false), 300);
  };

  const sizeClasses = {
    sm: 'w-7 h-7',
    md: 'w-9 h-9',
    lg: 'w-11 h-11'
  };

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  };

  if (loading) {
    return (
      <button
        disabled
        className={`${sizeClasses[size]} rounded-full flex items-center justify-center bg-white/10 ${className}`}
      >
        <Heart className={`${iconSizes[size]} text-white/30`} />
      </button>
    );
  }

  return (
    <button
      onClick={handleClick}
      className={`
        ${sizeClasses[size]} rounded-full flex items-center justify-center gap-2
        transition-all duration-200
        ${favorite 
          ? 'bg-red-500/20 hover:bg-red-500/30' 
          : 'bg-white/10 hover:bg-white/20'
        }
        ${isAnimating ? 'scale-125' : 'scale-100'}
        ${className}
      `}
      title={favorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
      data-testid={`favorite-btn-${productId}`}
    >
      <Heart 
        className={`
          ${iconSizes[size]} 
          transition-all duration-200
          ${favorite 
            ? 'fill-red-500 text-red-500' 
            : 'text-white/60 hover:text-red-400'
          }
        `}
      />
      {showLabel && (
        <span className={`text-sm ${favorite ? 'text-red-400' : 'text-white/60'}`}>
          {favorite ? 'Favori' : 'Ajouter'}
        </span>
      )}
    </button>
  );
}

// Compact favorite icon for lists/tables
export function FavoriteIcon({ productId, size = 'sm' }) {
  const { isFavorite, toggleFavorite } = useFavorites();
  const favorite = isFavorite(productId);

  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggleFavorite(productId);
  };

  const iconSizes = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-5 h-5'
  };

  return (
    <button onClick={handleClick} className="p-1 hover:bg-white/10 rounded">
      <Heart 
        className={`
          ${iconSizes[size]}
          ${favorite 
            ? 'fill-red-500 text-red-500' 
            : 'text-white/40 hover:text-red-400'
          }
        `}
      />
    </button>
  );
}

export default FavoriteButton;
