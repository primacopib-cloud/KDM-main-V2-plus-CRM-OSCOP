import { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight, Truck, ShoppingBag } from 'lucide-react';
import { toast } from 'sonner';
import { lolodriveAPI } from '../../services/api';
import { SectionCard, Badge, fmtEUR } from '../LolodriveLayout';

const DAY_FMT = new Intl.DateTimeFormat('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
const WEEK_FMT = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });

const toISO = (d) => d.toISOString().slice(0, 10);
const mondayOf = (offset) => {
  const d = new Date();
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7) + offset * 7);
  return toISO(d);
};

const STATUS_LABEL = { PAID: 'À préparer', PREPARING: 'En préparation', READY: 'Prête' };

// Grille hebdomadaire du gérant : commandes actives par jour et créneau, avec capacités et fermetures
export const ManagerPlanningGrid = () => {
  const [weekOffset, setWeekOffset] = useState(0);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null); // { date, slotId }

  const weekStart = useMemo(() => mondayOf(weekOffset), [weekOffset]);

  const load = useCallback(async () => {
    try {
      setData(await lolodriveAPI.managerPlanning(weekStart));
    } catch (e) {
      toast.error(e.message);
    }
  }, [weekStart]);

  useEffect(() => { load(); }, [load]);

  if (!data) return null;

  const todayISO = toISO(new Date());
  const selectedCell = selected
    ? data.days.find((d) => d.date === selected.date)?.slots?.[selected.slotId]
    : null;

  return (
    <SectionCard title="Planning de la semaine" className="mb-6" data-testid="manager-planning"
      action={
        <div className="flex items-center gap-1.5">
          <button type="button" onClick={() => setWeekOffset(weekOffset - 1)} data-testid="planning-prev-week"
            className="p-1.5 rounded-lg border border-white/15 text-white/70 hover:bg-white/[0.06]">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button type="button" onClick={() => setWeekOffset(0)} disabled={weekOffset === 0} data-testid="planning-today"
            className="px-2.5 h-7 rounded-lg text-[11px] font-bold border border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/10 disabled:opacity-40">
            Aujourd'hui
          </button>
          <button type="button" onClick={() => setWeekOffset(weekOffset + 1)} data-testid="planning-next-week"
            className="p-1.5 rounded-lg border border-white/15 text-white/70 hover:bg-white/[0.06]">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      }>
      <p className="text-[11px] text-white/45 mb-3" data-testid="planning-week-label">
        <CalendarDays className="w-3 h-3 inline mr-1" />
        Semaine du {WEEK_FMT.format(new Date(`${data.week_start}T12:00:00`))} au {WEEK_FMT.format(new Date(`${data.week_end}T12:00:00`))}
        {' '}— commandes payées, en préparation et prêtes.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-separate" style={{ borderSpacing: '3px' }}>
          <thead>
            <tr>
              <th className="w-32" />
              {data.days.map((d) => {
                const fullyClosed = !d.pickup_open && !d.delivery_open;
                return (
                  <th key={d.date} data-testid={`planning-day-${d.date}`}
                    className={`px-2 py-1.5 rounded-lg text-center font-semibold ${
                      d.date === todayISO ? 'bg-[#D9B35A]/15 text-[#E9CF8E]' :
                      fullyClosed ? 'bg-red-500/10 text-red-300/70' : 'bg-white/[0.04] text-white/70'}`}>
                    <div className="capitalize">{DAY_FMT.format(new Date(`${d.date}T12:00:00`))}</div>
                    {fullyClosed && <div className="text-[9px] uppercase tracking-wide">{d.closed ? 'Fermé (exception)' : 'Fermé'}</div>}
                    {!fullyClosed && !(d.pickup_open && d.delivery_open) && (
                      <div className="text-[9px] text-white/40">{d.pickup_open ? 'Retrait uniquement' : 'Livraison uniquement'}</div>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {data.slots.map((slot) => (
              <tr key={slot.id}>
                <td className="px-2 py-1 text-white/55 font-medium align-top">
                  <div className="font-bold text-white/70">{slot.id}</div>
                  <div className="text-[10px]">{slot.label}</div>
                </td>
                {data.days.map((d) => {
                  const cell = d.slots[slot.id] || { count: 0, orders: [] };
                  const fullyClosed = !d.pickup_open && !d.delivery_open;
                  const isSel = selected?.date === d.date && selected?.slotId === slot.id;
                  return (
                    <td key={d.date}
                      data-testid={`planning-cell-${d.date}-${slot.id}`}
                      onClick={() => cell.count > 0 && setSelected(isSel ? null : { date: d.date, slotId: slot.id })}
                      className={`px-2 py-2 rounded-lg text-center align-top transition-colors ${
                        isSel ? 'ring-2 ring-[#D9B35A] bg-[#D9B35A]/20' :
                        cell.full ? 'bg-red-500/20 text-red-200' :
                        cell.count > 0 ? 'bg-[#D9B35A]/10 text-[#E9CF8E] cursor-pointer hover:bg-[#D9B35A]/20' :
                        fullyClosed ? 'bg-white/[0.015] text-white/20' : 'bg-white/[0.03] text-white/30'}`}>
                      <div className="text-sm font-bold" data-testid={`planning-count-${d.date}-${slot.id}`}>
                        {cell.count}{cell.capacity ? `/${cell.capacity}` : ''}
                      </div>
                      {cell.full && <div className="text-[9px] uppercase">Complet</div>}
                      {cell.count > 0 && (
                        <div className="flex justify-center gap-1 mt-0.5">
                          {cell.orders.some((o) => o.fulfillment_type === 'DELIVERY')
                            ? <Truck className="w-3 h-3 text-[#a78bfa]" /> : null}
                          {cell.orders.some((o) => o.fulfillment_type !== 'DELIVERY')
                            ? <ShoppingBag className="w-3 h-3 text-[#D9B35A]" /> : null}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selected && selectedCell && (
        <div className="mt-3 p-3 rounded-lg bg-white/[0.03] border border-[#D9B35A]/25" data-testid="planning-cell-detail">
          <p className="text-[11px] font-bold text-[#E9CF8E] uppercase mb-2">
            {DAY_FMT.format(new Date(`${selected.date}T12:00:00`))} · créneau {selected.slotId} — {selectedCell.count} commande(s)
          </p>
          <div className="space-y-1.5">
            {selectedCell.orders.map((o) => (
              <div key={o.id} data-testid={`planning-order-${o.id}`}
                className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded bg-white/[0.03]">
                <div className="min-w-0">
                  <span className="font-mono text-xs">{o.order_number}</span>
                  <span className="text-white/50 text-[11px] ml-2">{o.customer} · {o.items_count} art.</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs font-semibold">{fmtEUR(o.total_cents)}</span>
                  <Badge color={o.fulfillment_type === 'DELIVERY' ? '#7c3aed' : '#D9B35A'}>
                    {o.fulfillment_type === 'DELIVERY' ? 'Livraison' : 'Retrait'}
                  </Badge>
                  <Badge color="#3b82f6">{STATUS_LABEL[o.status] || o.status}</Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </SectionCard>
  );
};
