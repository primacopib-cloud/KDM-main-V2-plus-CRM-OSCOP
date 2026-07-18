import { useEffect, useState } from 'react';
import { Plus, Loader2, Sparkles } from 'lucide-react';
import { catalogAPI } from '../../services/api';
import { formatPrice } from './catalogUtils';

export const CartSuggestions = ({ cart, cartLoading, onAddProduct }) => {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);

  const itemsKey = (cart.items || []).map(i => i.product_id).sort().join(',');

  useEffect(() => {
    if (!itemsKey) {
      setSuggestions([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    catalogAPI.getCartSuggestions()
      .then((data) => { if (!cancelled) setSuggestions(data.suggestions || []); })
      .catch(() => { if (!cancelled) setSuggestions([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [itemsKey]);

  if (!itemsKey || (!loading && suggestions.length === 0)) return null;

  return (
    <div className="mt-4 pt-3 border-t border-white/[0.08]" data-testid="cart-suggestions">
      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[#D9B35A] mb-2">
        <Sparkles className="w-3.5 h-3.5" />
        Souvent commandés ensemble
      </p>
      {loading ? (
        <div className="flex justify-center py-3">
          <Loader2 className="w-4 h-4 animate-spin text-[#D9B35A]" />
        </div>
      ) : (
        <div className="space-y-2">
          {suggestions.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between gap-2 p-2.5 rounded-xl bg-[#D9B35A]/[0.07] border border-[#D9B35A]/20"
              data-testid={`cart-suggestion-${p.id}`}
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-white/90 truncate">{p.name}</p>
                <p className="text-xs text-white/50">
                  {formatPrice(p.price_ht_cents)} HT · {p.unit}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onAddProduct({ id: p.id, min_order_qty: p.min_order_qty, price_visible: true })}
                disabled={cartLoading}
                data-testid={`cart-suggestion-add-${p.id}`}
                className="flex-shrink-0 w-8 h-8 rounded-full bg-[#D9B35A] hover:bg-[#c9a34a] text-black flex items-center justify-center transition-colors disabled:opacity-50"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
