// Regroupe les commandes POS par jour + créneau de retrait (aujourd'hui d'abord, puis demain, puis sans créneau)
const groupOrdersBySlot = (orders) => {
  const today = new Date().toISOString().slice(0, 10);
  const map = new Map();
  for (const o of orders) {
    let g;
    if (!o.pickup_slot_label) {
      g = { k: 'z-none', title: '📦 Sans créneau', rank: '9' };
    } else {
      const day = o.pickup_date || today;
      const dayLabel = day === today
        ? "Aujourd'hui"
        : new Date(day).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'short' });
      g = {
        k: `${day}|${o.pickup_slot_id || o.pickup_slot_label}`,
        title: `🕐 ${dayLabel} — ${o.pickup_slot_label}`,
        rank: `${day < today ? '0' : day === today ? '1' : '2'}-${day}|${o.pickup_slot_id || ''}`,
      };
    }
    if (!map.has(g.k)) map.set(g.k, { ...g, items: [] });
    map.get(g.k).items.push(o);
  }
  return [...map.values()].sort((a, b) => a.rank.localeCompare(b.rank));
};

export const PosSlotGroups = ({ orders, renderOrder }) => (
  <>
    {groupOrdersBySlot(orders).map((g) => (
      <div key={g.k} className="mb-4" data-testid={`slot-group-${g.k}`}>
        <div className="text-xs font-bold text-[#D9B35A] mb-2 border-l-2 border-[#D9B35A]/50 pl-2">
          {g.title} <span className="text-white/35 font-normal">· {g.items.length} commande{g.items.length > 1 ? 's' : ''}</span>
        </div>
        <div className="space-y-2">{g.items.map(renderOrder)}</div>
      </div>
    ))}
  </>
);
