// Export CSV (Excel FR : point-virgule + BOM) et impression du planning hebdomadaire

const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
const dateFR = (d) => d.split('-').reverse().join('/');
const cellLabel = (c) => {
  if (!c) return '0';
  if (c.distinct_capacities) {
    return `R ${c.pickup_count}${c.pickup_capacity ? `/${c.pickup_capacity}` : ''} · L ${c.delivery_count}${c.delivery_capacity ? `/${c.delivery_capacity}` : ''}`;
  }
  return `${c.count}${c.capacity ? `/${c.capacity}` : ''}`;
};

export const buildPlanningCsv = (data) => {
  const rows = [
    [`Planning ${data.point.name} (${data.point.code})`, `Semaine du ${dateFR(data.week_start)} au ${dateFR(data.week_end)}`],
    [],
    ['Créneau', ...data.days.map((d) => dateFR(d.date))],
  ];
  data.slots.forEach((slot) => {
    rows.push([slot.label, ...data.days.map((d) => cellLabel(d.slots[slot.id]))]);
  });
  rows.push([]);
  rows.push(['Date', 'Créneau', 'Commande', 'Client', 'Articles', 'Total', 'Type', 'Statut']);
  data.days.forEach((d) => data.slots.forEach((s) =>
    (d.slots[s.id]?.orders || []).forEach((o) => rows.push([
      dateFR(d.date), s.id, o.order_number, o.customer, o.items_count,
      `${(o.total_cents / 100).toFixed(2)} €`,
      o.fulfillment_type === 'DELIVERY' ? 'Livraison' : 'Retrait', o.status,
    ]))));
  return '\uFEFF' + rows.map((r) => r.map(esc).join(';')).join('\n');
};

export const buildPlanningPrintHtml = (data) => {
  const head = data.days.map((d) => {
    const closed = !d.pickup_open && !d.delivery_open;
    return `<th>${dateFR(d.date)}${closed ? '<br/><small>FERMÉ</small>' : ''}</th>`;
  }).join('');
  const body = data.slots.map((slot) => {
    const cells = data.days.map((d) => {
      const c = d.slots[slot.id];
      const orders = (c?.orders || []).map((o) =>
        `<div class="o">${o.order_number} · ${o.customer} · ${o.fulfillment_type === 'DELIVERY' ? 'Liv.' : 'Ret.'}</div>`).join('');
      return `<td class="${c?.full ? 'full' : ''}"><b>${cellLabel(c)}</b>${orders}</td>`;
    }).join('');
    return `<tr><th class="slot">${slot.label}</th>${cells}</tr>`;
  }).join('');
  return `<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Planning ${data.point.name} — semaine du ${dateFR(data.week_start)}</title>
<style>
  body { font-family: Georgia, serif; color: #1a1a1a; padding: 24px; }
  h1 { font-size: 18px; margin: 0 0 2px; } p { font-size: 12px; color: #555; margin: 0 0 16px; }
  table { border-collapse: collapse; width: 100%; font-size: 11px; }
  th, td { border: 1px solid #999; padding: 6px; text-align: center; vertical-align: top; }
  thead th { background: #f3ead8; } .slot { background: #faf6ee; text-align: left; width: 130px; }
  .full { background: #fde8e8; } .o { font-size: 9px; color: #444; margin-top: 2px; text-align: left; }
  @media print { body { padding: 0; } }
</style></head><body>
<h1>Planning — ${data.point.name} (${data.point.code})</h1>
<p>Semaine du ${dateFR(data.week_start)} au ${dateFR(data.week_end)} — commandes payées, en préparation et prêtes. LOLODRIVE by O'SCOP.</p>
<table><thead><tr><th></th>${head}</tr></thead><tbody>${body}</tbody></table>
</body></html>`;
};
