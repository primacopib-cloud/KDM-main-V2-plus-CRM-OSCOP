import { useState, useEffect, useRef } from 'react';
import { TimerReset, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const WARN_MS = 5 * 60 * 1000;

// Compte à rebours de la réservation panier (30 min) avec rappel avant expiration
export const CartReservationCountdown = ({ reservedUntil, zone }) => {
  const [localUntil, setLocalUntil] = useState(null);
  const [remaining, setRemaining] = useState(null);
  const [extending, setExtending] = useState(false);
  const warnedRef = useRef(false);
  const effectiveUntil = localUntil || reservedUntil;

  useEffect(() => { setLocalUntil(null); }, [reservedUntil]);

  useEffect(() => {
    warnedRef.current = false;
    if (!effectiveUntil) { setRemaining(null); return undefined; }
    const tick = () => {
      const ms = new Date(effectiveUntil).getTime() - Date.now();
      setRemaining(ms);
      if (ms > 0 && ms <= WARN_MS && !warnedRef.current) {
        warnedRef.current = true;
        toast.warning('Votre réservation panier expire dans moins de 5 minutes — finalisez votre commande ou prolongez-la.');
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [effectiveUntil]);

  const extend = async () => {
    setExtending(true);
    try {
      const res = await fetch(`${API_URL}/api/v2/catalog/cart/reservation/extend${zone ? `?zone_code=${zone}` : ''}`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || '');
      setLocalUntil(d.reserved_until);
      warnedRef.current = false;
      toast.success('Réservation prolongée de 15 minutes');
    } catch (e) {
      toast.error(e.message || 'Impossible de prolonger la réservation');
    } finally {
      setExtending(false);
    }
  };

  const ExtendButton = () => (
    <button type="button" onClick={extend} disabled={extending} data-testid="cart-reservation-extend"
      className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors disabled:opacity-50">
      <Plus className="w-3 h-3" /> {extending ? '…' : 'Prolonger 15 min'}
    </button>
  );

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
    <p className={`mb-2 text-[11px] flex items-center gap-1.5 flex-wrap ${warning ? 'text-amber-400' : 'text-[#8CC63E]'}`}
      data-testid="cart-reservation-countdown">
      <TimerReset className="w-3.5 h-3.5" />
      Quantités réservées encore <strong className="font-mono" data-testid="cart-reservation-timer">{mm}:{ss}</strong>
      {warning && <ExtendButton />}
    </p>
  );
};
