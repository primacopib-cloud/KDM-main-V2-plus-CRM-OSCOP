import { ShoppingCart, Coins } from 'lucide-react';
import { formatPrice, centsToCredits } from './catalogUtils';

export const FloatingMiniCart = ({ itemCount, totalCents, onOpen }) => {
  if (!itemCount) return null;

  return (
    <button
      type="button"
      onClick={onOpen}
      data-testid="floating-mini-cart"
      className="fixed bottom-6 right-6 z-50 flex items-center gap-3 pl-3 pr-4 py-2.5 rounded-full shadow-xl transition-transform hover:scale-105 active:scale-95"
      style={{
        background: 'linear-gradient(135deg, #D9B35A 0%, #c9a34a 100%)',
        border: '1px solid rgba(255,255,255,0.35)',
        boxShadow: '0 8px 24px rgba(217,179,90,0.45)',
      }}
    >
      <span className="relative inline-flex">
        <ShoppingCart className="w-5 h-5 text-black" />
        <span
          data-testid="mini-cart-count"
          className="absolute -top-2 -right-2 min-w-[18px] h-[18px] px-1 rounded-full bg-[#1F2A3A] text-white text-[10px] font-bold flex items-center justify-center"
        >
          {itemCount}
        </span>
      </span>
      <span className="text-left leading-tight">
        <span data-testid="mini-cart-total-eur" className="block text-sm font-bold text-black">
          {formatPrice(totalCents)} HT
        </span>
        <span data-testid="mini-cart-total-credits" className="flex items-center gap-1 text-[11px] font-medium text-black/70">
          <Coins className="w-3 h-3" />
          ≈ {centsToCredits(totalCents).toLocaleString('fr-FR')} crédits
        </span>
      </span>
    </button>
  );
};
