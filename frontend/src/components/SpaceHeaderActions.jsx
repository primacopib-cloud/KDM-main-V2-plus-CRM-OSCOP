import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, Heart, LogOut } from 'lucide-react';
import { authAPI } from '../services/api';

// Actions communes des espaces : Assistant IA, Favoris, Déconnexion
export const SpaceHeaderActions = ({ showFavorites = true }) => {
  const navigate = useNavigate();
  const logout = () => { authAPI.logout(); navigate('/'); };
  return (
    <div className="flex items-center gap-1">
      <Link to="/assistant-ia" data-testid="space-ai-link" title="Assistant IA (SCOOPY)" className="p-2 rounded-lg hover:bg-white/[0.06] transition-colors">
        <Sparkles className="w-4 h-4 text-[#D9B35A]" />
      </Link>
      {showFavorites && (
        <Link to="/favoris" data-testid="space-favorites-link" title="Mes favoris" className="p-2 rounded-lg hover:bg-white/[0.06] transition-colors">
          <Heart className="w-4 h-4 text-white/70" />
        </Link>
      )}
      <button
        type="button"
        onClick={logout}
        data-testid="space-logout-button"
        title="Déconnexion"
        className="p-2 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
      >
        <LogOut className="w-4 h-4" />
      </button>
    </div>
  );
};
