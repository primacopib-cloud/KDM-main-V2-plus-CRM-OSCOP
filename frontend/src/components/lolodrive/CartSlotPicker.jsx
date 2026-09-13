import { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { PickupCalendar } from './PickupCalendar';

// Créneau de retrait Drive / livraison : calendrier du relais + créneaux complets grisés + frais UC
export const CartSlotPicker = ({ fulfillment, cartItems, products, slotId, setSlotId, pickupDate, setPickupDate, relayDays, relayName, relayCode }) => {
  const [cfg, setCfg] = useState(null);
  const [avail, setAvail] = useState(null);
  useEffect(() => {
    lolodriveAPI.feesConfig().then(setCfg).catch(() => {});
  }, []);

  const kind = fulfillment === 'DELIVERY' ? 'delivery' : 'pickup';
  const slots = cfg?.[`${kind}_slots`] || [];
  const dayInfo = (avail?.days || []).find((d) => d.date === pickupDate);
  const slotFull = (sid) => Boolean(dayInfo?.slots?.[sid]?.full);

  useEffect(() => {
    if (!slots.length) return;
    const cur = slots.find((s) => s.id === slotId);
    if (!cur || slotFull(slotId)) {
      const free = slots.find((s) => !slotFull(s.id));
      if (free) setSlotId(free.id);
    }
    // eslint-disable-next-line
  }, [cfg, fulfillment, avail, pickupDate]);

  const feeFor = (sid) => cartItems.reduce((acc, { sku, qty }) => {
    const p = products.find((x) => x.sku === sku);
    const rates = cfg?.[`${kind}_rates`] || {};
    const r = rates[p?.category]?.[sid] ?? rates['*']?.[sid] ?? 0;
    return acc + r * qty;
  }, 0);

  if (!cfg || slots.length === 0) return null;
  const fee = Math.round(feeFor(slotId) * 100) / 100;

  return (
    <div data-testid="slot-picker">
      <label className="text-xs text-white/60 flex items-center gap-1">
        <Clock className="w-3 h-3" /> {fulfillment === 'DELIVERY' ? 'Créneau de livraison' : 'Créneau de retrait'}
        {relayName && <span className="text-[#D9B35A]/80">· calendrier {relayName}</span>}
      </label>
      {setPickupDate && (
        <PickupCalendar relayCode={relayCode} relayDays={relayDays} kind={kind}
          pickupDate={pickupDate} setPickupDate={setPickupDate} slotId={slotId}
          onAvailability={setAvail} />
      )}
      <Select value={slotId} onValueChange={setSlotId}>
        <SelectTrigger className="mt-1 h-9 bg-white/[0.04] border-white/15 text-white text-xs" data-testid="slot-select">
          <SelectValue placeholder="Choisir un créneau" />
        </SelectTrigger>
        <SelectContent>
          {slots.map((s) => {
            const f = Math.round(feeFor(s.id) * 100) / 100;
            const full = slotFull(s.id);
            return (
              <SelectItem key={s.id} value={s.id} disabled={full} data-testid={`slot-option-${s.id}`}>
                {s.label}{f > 0 ? ` · +${f} UC` : ''}{full ? ' — COMPLET' : ''}
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
      {fee > 0 && (
        <div className="flex justify-between text-xs text-[#D9B35A] mt-1.5 px-0.5" data-testid="slot-fee-line">
          <span>Frais de {fulfillment === 'DELIVERY' ? 'livraison' : 'retrait'} (créneau, par article & catégorie)</span>
          <span className="font-bold">+{fee} UC <span className="text-white/40 font-normal">(≈ {(fee / 10).toFixed(2)} €)</span></span>
        </div>
      )}
    </div>
  );
};
