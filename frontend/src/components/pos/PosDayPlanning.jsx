import { useEffect, useState } from 'react';
import { CalendarDays, Truck, ShoppingBag } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';
import { SectionCard, Badge, fmtEUR } from '../LolodriveLayout';

const STATUS_LABEL = { PAID: 'À préparer', PREPARING: 'En préparation', READY: 'Prête' };

// Vue journée POS : charge du jour par créneau au démarrage du poste
export const PosDayPlanning = () => {
  const [today, setToday] = useState(null);
  const [slots, setSlots] = useState([]);

  useEffect(() => {
    lolodriveAPI.managerPlanning().then((d) => {
      const iso = new Date().toISOString().slice(0, 10);
      const day = d.days.find((x) => x.date === iso);
      if (day) { setToday(day); setSlots(d.slots); }
    }).catch(() => {});
  }, []);

  if (!today) return null;
  const total = Object.values(today.slots).reduce((a, s) => a + s.count, 0);
  const fullyClosed = !today.pickup_open && !today.delivery_open;

  return (
    <SectionCard title="Planning du jour" className="mb-4" data-testid="pos-day-planning"
      action={<Badge color={total > 0 ? '#D9B35A' : '#10b981'}>{total} commande(s) aujourd'hui</Badge>}>
      <p className="text-[11px] text-white/45 mb-3">
        <CalendarDays className="w-3 h-3 inline mr-1" />
        {new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())}
        {fullyClosed && <span className="text-red-300 font-bold ml-2">— relais fermé aujourd'hui</span>}
      </p>
      <div className="grid sm:grid-cols-2 gap-3">
        {slots.map((slot) => {
          const cell = today.slots[slot.id] || { count: 0, pickup_count: 0, delivery_count: 0, orders: [] };
          return (
            <div key={slot.id} data-testid={`pos-day-slot-${slot.id}`}
              className={`p-3 rounded-xl border ${cell.full ? 'border-red-400/40 bg-red-500/10' : 'border-white/10 bg-white/[0.03]'}`}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-white/70">{slot.label}</span>
                <span className="text-sm font-bold text-[#E9CF8E]" data-testid={`pos-day-count-${slot.id}`}>
                  {cell.count}{cell.capacity && !cell.distinct_capacities ? `/${cell.capacity}` : ''}
                  {cell.full ? ' — COMPLET' : ''}
                </span>
              </div>
              {cell.count > 0 && (
                <div className="flex gap-3 text-[11px] text-white/50 mb-1.5">
                  <span className="inline-flex items-center gap-1">
                    <ShoppingBag className="w-3 h-3 text-[#D9B35A]" /> {cell.pickup_count} retrait(s)
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Truck className="w-3 h-3 text-[#a78bfa]" /> {cell.delivery_count} livraison(s)
                  </span>
                </div>
              )}
              <div className="space-y-1">
                {cell.orders.slice(0, 6).map((o) => (
                  <div key={o.id} className="flex items-center justify-between text-[11px] px-2 py-1 rounded bg-white/[0.03]"
                    data-testid={`pos-day-order-${o.id}`}>
                    <span className="font-mono truncate">{o.order_number} <span className="text-white/40">· {o.customer}</span></span>
                    <span className="flex items-center gap-1.5 shrink-0">
                      <span className="font-semibold">{fmtEUR(o.total_cents)}</span>
                      <Badge color="#3b82f6">{STATUS_LABEL[o.status] || o.status}</Badge>
                    </span>
                  </div>
                ))}
                {cell.orders.length > 6 && (
                  <p className="text-[10px] text-white/40">+ {cell.orders.length - 6} autre(s) — voir la file POS</p>
                )}
                {cell.count === 0 && <p className="text-[11px] text-white/30">Aucune commande sur ce créneau.</p>}
              </div>
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
};
