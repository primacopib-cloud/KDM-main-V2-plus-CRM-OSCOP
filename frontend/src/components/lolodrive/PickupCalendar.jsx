import { useEffect, useState } from 'react';
import { API } from '../../services/http';

const MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
const jsDay = (d) => (d.getDay() + 6) % 7;
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

// Calendrier 21 jours du relais : mois/année affichés, jours fermés + créneaux complets grisés
export const PickupCalendar = ({ relayCode, relayDays, kind, pickupDate, setPickupDate, slotId, onAvailability }) => {
  const [avail, setAvail] = useState(null);

  useEffect(() => {
    if (!relayCode) { setAvail(null); onAvailability?.(null); return; }
    fetch(`${API}/lolodrive/lolo-points/${relayCode}/availability?kind=${kind}&days=21`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { setAvail(d); onAvailability?.(d); })
      .catch(() => { setAvail(null); onAvailability?.(null); });
    // eslint-disable-next-line
  }, [relayCode, kind]);

  const byDate = {};
  (avail?.days || []).forEach((d) => { byDate[d.date] = d; });
  const allowed = relayDays && relayDays.length ? new Set(relayDays) : null;
  const cells = Array.from({ length: 21 }, (_, i) => new Date(Date.now() + i * 86400000));

  const isClosed = (d) => {
    const a = byDate[iso(d)];
    if (a) return !a.open || a.full;
    return allowed ? !allowed.has(jsDay(d)) : false;
  };

  useEffect(() => {
    if (!pickupDate) return;
    const cur = cells.find((c) => iso(c) === pickupDate);
    if (cur && !isClosed(cur)) return;
    const next = cells.find((c) => !isClosed(c));
    if (next) setPickupDate(iso(next));
    // eslint-disable-next-line
  }, [avail, relayDays, pickupDate]);

  const first = cells[0];
  const last = cells[cells.length - 1];
  const header = first.getMonth() === last.getMonth()
    ? `${MONTHS[first.getMonth()]} ${first.getFullYear()}`
    : `${MONTHS[first.getMonth()]} ${first.getFullYear()} → ${MONTHS[last.getMonth()]} ${last.getFullYear()}`;
  const todayIso = iso(new Date());

  return (
    <div className="mt-1.5 mb-1 rounded-xl border border-white/10 bg-white/[0.02] p-2" data-testid="pickup-day-calendar">
      <div className="text-center text-[11px] font-bold text-[#E9CF8E] capitalize mb-1.5" data-testid="calendar-month-header">
        {header}
      </div>
      <div className="grid grid-cols-7 gap-1 mb-1">
        {['Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa', 'Di'].map((d) => (
          <span key={d} className="text-center text-[9px] font-bold text-white/35">{d}</span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((d) => {
          const id = iso(d);
          const closed = isClosed(d);
          const selected = pickupDate === id;
          const firstOfMonth = d.getDate() === 1;
          return (
            <button key={id} type="button" disabled={closed}
              data-testid={`pickup-day-${id}`} data-closed={closed || undefined}
              onClick={() => setPickupDate(id)}
              title={d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
              className={`h-9 rounded-lg text-[11px] font-bold border transition-colors disabled:opacity-25 disabled:cursor-not-allowed ${
                selected ? 'text-[#2A1045] on-gold border-[#D9B35A]' : 'text-white/60 bg-white/[0.03] border-white/10 hover:border-[#D9B35A]/40'}`}
              style={selected ? { background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' } : undefined}>
              {d.getDate()}
              <span className="block text-[7px] font-normal leading-none capitalize">
                {id === todayIso ? 'auj.' : (firstOfMonth || selected) ? MONTHS[d.getMonth()].slice(0, 4) + '.' : ''}
              </span>
            </button>
          );
        })}
      </div>
      <p className="text-[10px] text-white/40 mt-1.5" data-testid="relay-days-hint">
        Jours grisés = fermés par le relais ou complets
      </p>
    </div>
  );
};
