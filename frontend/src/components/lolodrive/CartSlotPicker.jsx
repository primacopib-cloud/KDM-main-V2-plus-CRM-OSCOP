import { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { lolodriveAPI } from '../../services/api';

// Choix du jour (aujourd'hui/demain) + créneau de retrait Drive / livraison + frais UC (config super admin)
export const CartSlotPicker = ({ fulfillment, cartItems, products, slotId, setSlotId, pickupDate, setPickupDate }) => {
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

  useEffect(() => {
    if (!setPickupDate || !cfg) return;
    const t = new Date();
    const isoD = (d) => d.toISOString().slice(0, 10);
    const sel = (cfg[`${kind}_slots`] || []).find((s) => s.id === slotId);
    const over = Boolean(sel?.end && t.toISOString().slice(11, 16) >= sel.end);
    const target = over ? isoD(new Date(t.getTime() + 86400000)) : isoD(t);
    if (!pickupDate || (over && pickupDate === isoD(t))) setPickupDate(target);
    // eslint-disable-next-line
  }, [cfg, slotId, fulfillment]);

  const feeFor = (sid) => cartItems.reduce((acc, { sku, qty }) => {
    const p = products.find((x) => x.sku === sku);
    const rates = cfg?.[`${kind}_rates`] || {};
    const r = rates[p?.category]?.[sid] ?? rates['*']?.[sid] ?? 0;
    return acc + r * qty;
  }, 0);

  if (!cfg || slots.length === 0) return null;
  const fee = Math.round(feeFor(slotId) * 100) / 100;

  const iso = (d) => d.toISOString().slice(0, 10);
  const today = new Date();
  const tomorrow = new Date(today.getTime() + 86400000);
  const selSlot = slots.find((s) => s.id === slotId);
  const todayOver = Boolean(selSlot?.end && today.toISOString().slice(11, 16) >= selSlot.end);
  const days = [
    { id: iso(today), label: "Aujourd'hui", disabled: todayOver },
    { id: iso(tomorrow), label: 'Demain', disabled: false },
  ];

  return (
    <div data-testid="slot-picker">
      <label className="text-xs text-white/60 flex items-center gap-1">
        <Clock className="w-3 h-3" /> {fulfillment === 'DELIVERY' ? 'Créneau de livraison' : 'Créneau de retrait'}
      </label>
      {setPickupDate && (
        <div className="flex gap-2 mt-1.5 mb-1" data-testid="pickup-day-picker">
          {days.map((d) => (
            <button key={d.id} type="button" disabled={d.disabled} data-testid={`pickup-day-${d.label === 'Demain' ? 'tomorrow' : 'today'}`}
              onClick={() => setPickupDate(d.id)}
              className={`flex-1 py-1.5 rounded-lg border text-xs font-bold transition-colors disabled:opacity-35 disabled:cursor-not-allowed ${pickupDate === d.id ? 'text-[#D9B35A] bg-[#D9B35A]/15 border-[#D9B35A]/40' : 'text-white/50 bg-white/[0.03] border-white/10'}`}>
              {d.label}
              <span className="block text-[9px] font-normal text-white/35">
                {new Date(d.id).toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' })}
              </span>
            </button>
          ))}
        </div>
      )}
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
