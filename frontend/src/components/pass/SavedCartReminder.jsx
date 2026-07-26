import { Link } from 'react-router-dom';
import { ShoppingCart, ArrowRight } from 'lucide-react';

export const SavedCartReminder = () => {
  let count = 0;
  try {
    const c = JSON.parse(localStorage.getItem('kdm_lolodrive_cart') || '{}') || {};
    count = Object.values(c).reduce((a, n) => a + (Number(n) || 0), 0);
  } catch { count = 0; }
  if (!count) return null;
  return (
    <Link to="/catalogue-lolodrive" data-testid="saved-cart-reminder"
      className="flex items-center justify-between gap-3 mb-6 p-3.5 rounded-2xl border border-[#D9B35A]/40 hover:border-[#D9B35A]/70 transition-colors"
      style={{ background: 'rgba(217,179,90,0.08)' }}>
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#D9B35A]/20 shrink-0">
          <ShoppingCart className="w-4 h-4 text-[#D9B35A]" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">
            Panier en attente — {count} article{count > 1 ? 's' : ''}
          </p>
          <p className="text-xs text-white/50">Reprenez votre commande LOLODRIVE là où vous l'aviez laissée.</p>
        </div>
      </div>
      <span className="text-xs font-bold text-[#D9B35A] inline-flex items-center gap-1 shrink-0">
        Reprendre <ArrowRight className="w-3.5 h-3.5" />
      </span>
    </Link>
  );
};
