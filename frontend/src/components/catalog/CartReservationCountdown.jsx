import { useState, useEffect, useRef } from 'react';
import { TimerReset } from 'lucide-react';
import { toast } from 'sonner';

const WARN_MS = 5 * 60 * 1000;

// Compte à rebours de la réservation panier (30 min) avec rappel avant expiration
export const CartReservationCountdown = ({ reservedUntil }) => {
  const [remaining, setRemaining] = useState(null);
  const warnedRef = useRef(false);

  useEffect(() => {
    warnedRef.current = false;
    if (!reservedUntil) { setRemaining(null); return undefined; }
    const tick = () => {
      const ms = new Date(reservedUntil).getTime() - Date.now();
      setRemaining(ms);
      if (ms > 0 && ms <= WARN_MS && !warnedRef.current) {
        warnedRef.current = true;
        toast.warning('Votre réservation panier expire dans moins de 5 minutes — finalisez votre commande.');
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [reservedUntil]);

  if (remaining === null) {
    return (
      <p className="mb-2 text-[11px] text-[#8CC63E] flex items-center gap-1.5" data-testid="cart-reservation-note">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#8CC63E]"></span>
        Quantités réservées pour vous pendant 30 minutes
      </p>
    );
  }

  if (remaining <= 0) {
    return (
      <p className="mb-2 text-[11px] text-red-400 flex items-center gap-1.5" data-testid="cart-reservation-expired">
        <TimerReset className="w-3.5 h-3.5" />
        Réservation expirée — les quantités ne sont plus garanties
      </p>
    );
  }

  const totalSec = Math.floor(remaining / 1000);
  const mm = String(Math.floor(totalSec / 60)).padStart(2, '0');
  const ss = String(totalSec % 60).padStart(2, '0');
  const warning = remaining <= WARN_MS;
  return (
    <p className={`mb-2 text-[11px] flex items-center gap-1.5 ${warning ? 'text-amber-400' : 'text-[#8CC63E]'}`}
      data-testid="cart-reservation-countdown">
      <TimerReset className="w-3.5 h-3.5" />
      Quantités réservées encore <strong className="font-mono" data-testid="cart-reservation-timer">{mm}:{ss}</strong>
      {warning && ' — finalisez votre commande'}
    </p>
  );
};
