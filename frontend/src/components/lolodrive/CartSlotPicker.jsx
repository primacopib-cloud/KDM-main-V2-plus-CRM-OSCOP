import { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { lolodriveAPI } from '../../services/api';

// Choix du créneau de retrait Drive / livraison + frais UC par article & catégorie (config super admin)
export const CartSlotPicker = ({ fulfillment, cartItems, products, slotId, setSlotId }) => {
  const [cfg, setCfg] = useState(null);
  useEffect(() => {
    lolodriveAPI.feesConfig().then(setCfg).catch(() => {});
  }, []);

  const kind = fulfillment === 'DELIVERY' ? 'delivery' : 'pickup';
  const slots = cfg?.[`${kind}_slots`] || [];

  useEffect(() => {
    if (slots.length && !slots.some((s) => s.id === slotId)) setSlotId(slots[0].id);
    // eslint-disable-next-line
  }, [cfg, fulfillment]);

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
      </label>
      <Select value={slotId || ''} onValueChange={setSlotId}>
        <SelectTrigger className="bg-white/[0.04] border-white/10 mt-1" data-testid="slot-select">
          <SelectValue placeholder="Choisir un créneau" />
        </SelectTrigger>
        <SelectContent>
          {slots.map((s) => {
            const f = Math.round(feeFor(s.id) * 100) / 100;
            return (
              <SelectItem key={s.id} value={s.id} data-testid={`slot-option-${s.id}`}>
                {s.label}{f > 0 ? ` · +${f} UC` : ''}
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
