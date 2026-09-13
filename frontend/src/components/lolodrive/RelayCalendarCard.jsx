import { useState } from 'react';
import { X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { SectionCard } from '../LolodriveLayout';

const DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

const DayRow = ({ label, days, toggle, testPrefix }) => (
  <div>
    <p className="text-[11px] font-bold text-white/55 uppercase mb-1.5">{label}</p>
    <div className="flex flex-wrap gap-1.5">
      {DAYS.map((d, i) => (
        <button key={d} type="button" onClick={() => toggle(i)} data-testid={`${testPrefix}-${i}`}
          className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-colors ${
            days.includes(i)
              ? 'text-[#2A1045] on-gold border-[#D9B35A]'
              : 'text-white/50 bg-white/[0.04] border-white/15 hover:border-[#D9B35A]/40'}`}
          style={days.includes(i) ? { background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' } : undefined}>
          {d.slice(0, 3)}
        </button>
      ))}
    </div>
  </div>
);

// Le gérant programme jours de retrait/livraison, fermetures exceptionnelles et capacité par créneau
export const RelayCalendarCard = ({ point, onSaved }) => {
  const [pickupDays, setPickupDays] = useState(point.pickup_days || []);
  const [deliveryDays, setDeliveryDays] = useState(point.delivery_days || []);
  const [closedDates, setClosedDates] = useState(point.closed_dates || []);
  const [capacity, setCapacity] = useState(point.slot_capacity || 0);
  const [deliveryCapacity, setDeliveryCapacity] = useState(
    point.delivery_slot_capacity == null ? '' : point.delivery_slot_capacity);
  const [newDate, setNewDate] = useState('');
  const [busy, setBusy] = useState(false);

  const toggle = (list, set) => (i) => set(list.includes(i) ? list.filter((x) => x !== i) : [...list, i]);

  const save = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/lolodrive/manager/my-point/calendar`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ pickup_days: pickupDays, delivery_days: deliveryDays,
          closed_dates: closedDates, slot_capacity: Number(capacity) || 0,
          delivery_slot_capacity: deliveryCapacity === '' ? null : (Number(deliveryCapacity) || 0) }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(d.members_notified > 0
        ? `Calendrier enregistré — ${d.members_notified} membre(s) prévenu(s) par email`
        : 'Calendrier du relais enregistré');
      onSaved?.();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <SectionCard title="Calendrier du relais" data-testid="relay-calendar-config">
      <p className="text-[11px] text-white/45 mb-3" data-testid="relay-calendar-hint">
        Programmez vos jours de retrait Drive et de livraison, vos fermetures exceptionnelles et la
        capacité par créneau. Aucun jour coché = ouvert tous les jours. Les membres ne peuvent choisir
        que vos jours ouverts.
      </p>
      <div className="space-y-4">
        <DayRow label="Jours de retrait (Drive / relais)" days={pickupDays}
          toggle={toggle(pickupDays, setPickupDays)} testPrefix="relay-pickup-day" />
        <DayRow label="Jours de livraison" days={deliveryDays}
          toggle={toggle(deliveryDays, setDeliveryDays)} testPrefix="relay-delivery-day" />
        <div>
          <p className="text-[11px] font-bold text-white/55 uppercase mb-1.5">Fermetures exceptionnelles (fériés, congés)</p>
          <div className="flex items-center gap-2 mb-2">
            <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)}
              data-testid="relay-closed-date-input"
              className="h-9 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs" />
            <button type="button" data-testid="relay-closed-date-add"
              onClick={() => { if (newDate && !closedDates.includes(newDate)) { setClosedDates([...closedDates, newDate].sort()); setNewDate(''); } }}
              className="px-3 h-9 rounded-lg text-xs font-bold border border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/10">
              Ajouter
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {closedDates.map((d) => (
              <span key={d} data-testid={`relay-closed-date-${d}`}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-semibold bg-red-500/15 text-red-200 border border-red-400/30">
                {d.split('-').reverse().join('/')}
                <button type="button" onClick={() => setClosedDates(closedDates.filter((x) => x !== d))}
                  data-testid={`relay-closed-date-remove-${d}`}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {closedDates.length === 0 && <span className="text-[11px] text-white/35">Aucune fermeture programmée</span>}
          </div>
        </div>
        <div>
          <p className="text-[11px] font-bold text-white/55 uppercase mb-1.5">Capacité par créneau (commandes max / jour / créneau)</p>
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <span className="text-[10px] text-white/45 block mb-0.5">Retrait (Drive / relais)</span>
              <input type="number" min="0" value={capacity} onChange={(e) => setCapacity(e.target.value)}
                data-testid="relay-slot-capacity"
                className="h-9 w-28 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs" />
            </div>
            <div>
              <span className="text-[10px] text-white/45 block mb-0.5">Livraison (vide = même que retrait)</span>
              <input type="number" min="0" value={deliveryCapacity} placeholder="—"
                onChange={(e) => setDeliveryCapacity(e.target.value)}
                data-testid="relay-delivery-slot-capacity"
                className="h-9 w-28 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs" />
            </div>
          </div>
          <span className="text-[11px] text-white/40 block mt-1">0 = illimitée. Les créneaux complets sont grisés côté membre.</span>
        </div>
      </div>
      <button type="button" onClick={save} disabled={busy} data-testid="relay-calendar-save"
        className="mt-4 px-4 h-9 rounded-lg text-xs font-bold text-[#2A1045] on-gold disabled:opacity-50"
        style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
        {busy ? 'Enregistrement…' : 'Enregistrer le calendrier'}
      </button>
    </SectionCard>
  );
};
