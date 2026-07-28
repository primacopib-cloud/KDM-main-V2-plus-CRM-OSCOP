import QRCode from 'qrcode';

// Étiquettes rayon : nom + prix € + UC (+ prix PASS) + QR produit (LOLO:{sku}) — à découper et coller en rayon
export const printShelfLabels = async (products) => {
  const qrs = await Promise.all(products.map((p) =>
    QRCode.toDataURL(`LOLO:${p.sku}`, { width: 120, margin: 0 }).catch(() => '')));
  const labels = products.map((p, i) => `
    <div class="label">
      <div class="info">
        <div class="name">${p.name}</div>
        <div class="price">${(p.price_public_cents / 100).toFixed(2)} €</div>
        <div class="uc">${p.uc_public} UC${p.price_pass_cents != null ? ` · PASS ${(p.price_pass_cents / 100).toFixed(2)} €` : ''}</div>
        <div class="sku">${p.sku}</div>
      </div>
      ${qrs[i] ? `<img src="${qrs[i]}" class="qr"/>` : ''}
    </div>`).join('');
  const w = window.open('', '_blank', 'width=820,height=920');
  w.document.write(`<html><head><title>Étiquettes rayon — ${new Date().toLocaleDateString('fr-FR')}</title><style>
    body{font-family:Arial,sans-serif;padding:14px;color:#111}
    h1{font-size:15px;margin:0 0 2px}p{font-size:10px;color:#666;margin:0 0 10px}
    .grid{display:flex;flex-wrap:wrap;gap:6px}
    .label{width:220px;border:1.5px dashed #888;border-radius:6px;padding:8px 10px;display:flex;align-items:center;gap:8px;page-break-inside:avoid}
    .info{flex:1;min-width:0}
    .name{font-size:11.5px;font-weight:bold;line-height:1.25;max-height:29px;overflow:hidden}
    .price{font-size:19px;font-weight:bold;margin-top:2px}
    .uc{font-size:9.5px;color:#555}
    .sku{font-size:8px;color:#999;margin-top:1px}
    .qr{width:58px;height:58px;flex-shrink:0}
    @media print{.label{border-color:#aaa}}
  </style></head><body>
    <h1>Étiquettes rayon — ${new Date().toLocaleDateString('fr-FR')}</h1>
    <p>Découpez chaque étiquette et collez-la en rayon. Le QR permet le comptage d'inventaire en un scan (+1 par scan).</p>
    <div class="grid">${labels}</div>
  </body></html>`);
  w.document.close();
  setTimeout(() => w.print(), 350);
};
