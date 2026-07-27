const fmtH = (min) => `${Math.floor(min / 60)}h${String(min % 60).padStart(2, '0')}`;

export const printHoursSheet = (data) => {
  const monthLabel = new Date(`${data.month}-01`).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  const rows = data.days.map((d) =>
    `<tr><td>${new Date(d.date).toLocaleDateString('fr-FR', { weekday: 'short', day: '2-digit', month: '2-digit' })}</td>
     <td style="text-align:center">${d.first}</td><td style="text-align:center">${d.last}</td>
     <td style="text-align:center">${d.break_min} min</td>
     <td style="text-align:center"><b>${fmtH(d.presence_min)}</b></td></tr>`).join('');
  const w = window.open('', '_blank', 'width=760,height=920');
  w.document.write(`<html><head><title>Relevé d'heures — ${data.operator.contact_name} — ${monthLabel}</title><style>
    body{font-family:Arial,sans-serif;padding:28px;color:#111;font-size:13px}
    h1{font-size:17px;margin:0 0 2px}h2{font-size:13px;font-weight:normal;color:#555;margin:0 0 14px}
    table{width:100%;border-collapse:collapse;margin-top:10px}
    th,td{border:1px solid #999;padding:6px 9px;text-align:left}
    th{background:#f0f0f0;font-size:11px;text-transform:uppercase}
    .tot{background:#fafafa;font-weight:bold}
    .sig{display:flex;gap:40px;margin-top:36px}
    .sig div{flex:1;border-top:1px solid #999;padding-top:6px;font-size:11px;color:#555}
    .note{font-size:10px;color:#888;margin-top:14px}
  </style></head><body>
    <h1>Relevé d'heures — ${monthLabel}</h1>
    <h2>${data.point.name} (${data.point.code}) — ${data.point.address || ''}, ${data.point.city || ''}</h2>
    <p>Salarié : <b>${data.operator.contact_name}</b> (${data.operator.email})</p>
    <table>
      <tr><th>Jour</th><th>Première activité</th><th>Dernière activité</th><th>Pauses</th><th>Présence nette</th></tr>
      ${rows || '<tr><td colspan="5" style="text-align:center;color:#888">Aucune activité enregistrée ce mois</td></tr>'}
      <tr class="tot"><td colspan="3">TOTAL DU MOIS</td><td style="text-align:center">${data.total_break_min} min</td>
      <td style="text-align:center">${fmtH(data.total_presence_min)}</td></tr>
    </table>
    <p class="note">Présence estimée automatiquement : première → dernière activité en caisse (connexions, ventes, pauses), pauses déduites. Document indicatif pour la préparation de la paie.</p>
    <div class="sig"><div>Signature du gérant</div><div>Signature du salarié</div></div>
  </body></html>`);
  w.document.close();
  w.print();
};
