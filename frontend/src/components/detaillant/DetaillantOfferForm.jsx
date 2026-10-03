import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../services/api.detaillant';
import { OfferPhotoPicker } from './OfferPhotoPicker';

const inputCls = 'w-full h-9 px-2.5 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs';

export const CURRENCIES = ['EUR', 'USD', 'GBP', 'CAD', 'CHF', 'JPY', 'CNY', 'AUD', 'NZD', 'BRL', 'MXN', 'ARS', 'CLP', 'COP',
  'DOP', 'HTG', 'JMD', 'TTD', 'BBD', 'XCD', 'XPF', 'XOF', 'XAF', 'MAD', 'TND', 'DZD', 'EGP', 'ZAR', 'NGN', 'KES', 'GHS',
  'INR', 'PKR', 'BDT', 'THB', 'VND', 'IDR', 'MYR', 'SGD', 'PHP', 'KRW', 'HKD', 'TWD', 'AED', 'SAR', 'QAR', 'ILS', 'TRY',
  'RUB', 'UAH', 'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'SEK', 'NOK', 'DKK', 'ISK'];

export const DetaillantOfferForm = ({ t, info, onCreated }) => {
  const [products, setProducts] = useState([]);
  const [f, setF] = useState({ product_sku: '', lot_type: 'SAME', qty_lots: 1, description: '', composed_detail: '',
    lot_price: '', currency: 'EUR', discount_mode: 'PERCENT', discount_value: 15, scheduled_start: '',
    condition: 'NEW', warranty: '', dlc: '' });
  const [photos, setPhotos] = useState([]);
  const [extraSkus, setExtraSkus] = useState(['', '']);
  const [items, setItems] = useState({});
  const [confirmedItems, setConfirmedItems] = useState({});
  const [busy, setBusy] = useState(false);
  useEffect(() => { detaillantAPI.catalog().then((r) => setProducts(r.products || [])).catch(() => {}); }, []);
  const product = products.find((p) => p.sku === f.product_sku);
  const extra = info.offers_used_this_month >= info.included_offers;
  const price = Number(f.lot_price) || 0;
  const perLot = Math.max(1, Math.ceil(price * (info.deposit_rate_pct || 2.5) / 100 * 10));
  const cost = f.qty_lots * perLot + (extra ? f.qty_lots * info.extra_offer_credits_per_lot : 0);
  const discAmount = f.discount_mode === 'PERCENT' ? price * Number(f.discount_value || 0) / 100 : Number(f.discount_value || 0);
  const discPct = price > 0 ? (discAmount / price) * 100 : 0;
  const finalPrice = Math.max(0, price - discAmount);
  const discountKo = price > 0 && discPct < 15;
  const composedProducts = f.lot_type === 'COMPOSED'
    ? [f.product_sku, ...extraSkus].filter(Boolean).map((sku) => products.find((p) => p.sku === sku)).filter(Boolean)
    : (product ? [product] : []);
  const anyPerishable = composedProducts.some((p) => p.perishable);
  const dlcKo = anyPerishable && (!f.dlc || new Date(f.dlc) < new Date(Date.now() + 90 * 86400000));
  const setItem = (sku, patch) => {
    setItems((m) => ({ ...m, [sku]: { ...(m[sku] || {}) , ...patch } }));
    setConfirmedItems((m) => { const n = { ...m }; delete n[sku]; return n; });
  };
  const itemOf = (sku) => items[sku] || {};
  // Le POP'S confirme quantité + infos d'un lot avant de sélectionner un autre produit
  const confirmItem = (sku) => {
    const p = composedProducts.find((x) => x.sku === sku);
    const d = itemOf(sku);
    if (!p) return;
    if (!(f.qty_lots >= 1)) { toast.warning("Indiquez d'abord la quantité de lots."); return; }
    if (itemKo(p, d)) { toast.error(`Complétez ${p.name} : quantité/format, ingrédients, allergènes${f.lot_type === 'COMPOSED' ? ', prix TTC' : ''}.`); return; }
    setConfirmedItems((m) => ({ ...m, [sku]: true }));
    toast.success(`Lot « ${p.name} » confirmé ✓`);
  };
  // Bloque le changement/sélection d'un autre produit tant que le lot courant n'est pas confirmé
  const gateChange = () => {
    if (f.product_sku && !confirmedItems[f.product_sku]) {
      toast.warning("Confirmez d'abord ce lot (quantité de lots + informations de l'article) avant de sélectionner un autre produit.");
      return false;
    }
    return true;
  };
  useEffect(() => {
    composedProducts.forEach((p) => {
      if (p.food_info && !items[p.sku]) {
        const fi = p.food_info;
        setItem(p.sku, { format_label: fi.format_label || '', net_qty_value: fi.net_qty_value || '',
          net_qty_unit: fi.net_qty_unit || '', ingredients: fi.ingredients || '', allergens: fi.allergens || '' });
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [composedProducts.map((p) => p.sku).join(',')]);
  const itemsDetail = composedProducts.map((p) => ({ sku: p.sku, ...itemOf(p.sku) }));
  const itemsSum = f.lot_type === 'COMPOSED'
    ? Math.round(itemsDetail.reduce((s, d) => s + (Number(d.unit_price_ttc) || 0), 0) * 100) / 100 : 0;
  const sumKo = f.lot_type === 'COMPOSED' && finalPrice > 0 && Math.abs(itemsSum - finalPrice) > 0.02;
  const itemKo = (p, d) => !(d.format_label || '').trim() || (d.ingredients || '').trim().length < 2
    || (d.allergens || '').trim().length < 2
    || (f.lot_type === 'COMPOSED' && !(Number(d.unit_price_ttc) > 0));
  const itemsKo = composedProducts.length === 0 || composedProducts.some((p) => itemKo(p, itemOf(p.sku))) || sumKo
    || composedProducts.some((p) => !confirmedItems[p.sku]);
  const submit = async () => {
    setBusy(true);
    try {
      await detaillantAPI.createOffer({
        ...f, qty_lots: Number(f.qty_lots), category: product?.category,
        lot_price: price, discount_value: Number(f.discount_value),
        scheduled_start: f.scheduled_start ? new Date(f.scheduled_start).toISOString() : null,
        photo_main: photos[0] || null, photos: photos.slice(1).filter(Boolean),
        product_skus: f.lot_type === 'COMPOSED' ? extraSkus.filter(Boolean) : [],
        items_detail: itemsDetail.map((d) => ({
          sku: d.sku, brand: (d.brand || '').trim() || null,
          format_label: (d.format_label || '').trim(),
          unit_price_ttc: Number(d.unit_price_ttc) > 0 ? Number(d.unit_price_ttc) : null,
          net_qty_value: Number(d.net_qty_value) > 0 ? Number(d.net_qty_value) : null,
          net_qty_unit: d.net_qty_unit || null,
          ingredients: (d.ingredients || '').trim(), allergens: (d.allergens || '').trim(),
          ddm_dlc: d.ddm_dlc || null,
        })),
        warranty: f.warranty.trim() || null, dlc: f.dlc || null,
      });
      toast.success(`✓ Offre déposée — ${cost} crédits`);
      setF({ product_sku: '', lot_type: 'SAME', qty_lots: 1, description: '', composed_detail: '',
        lot_price: '', currency: 'EUR', discount_mode: 'PERCENT', discount_value: 15, scheduled_start: '',
        condition: 'NEW', warranty: '', dlc: '' });
      setPhotos([]);
      setExtraSkus(['', '']);
      setItems({});
      setConfirmedItems({});
      onCreated?.();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return (
    <div className="rounded-2xl border border-[#D9B35A]/30 bg-[#D9B35A]/[0.04] p-4 space-y-3" data-testid="detaillant-offer-form">
      <h3 className="text-sm font-bold text-[#E9CF8E]">{t.newOffer}</h3>
      <p className="text-[10px] text-white/45">{t.costInfo}</p>
      {products.some((p) => p.food_info) && (
        <div data-testid="offer-quick-lots">
          <p className="text-[10px] font-bold text-white/50 uppercase tracking-wide mb-1">
            Lots prêts à déposer — catalogue de base (lot ×3, infos pré-remplies)
          </p>
          <div className="flex flex-wrap gap-1.5">
            {products.filter((p) => p.food_info).map((p) => (
              <button key={p.sku} type="button"
                onClick={() => {
                  if (!gateChange()) return;
                  setF((prev) => ({ ...prev, lot_type: 'SAME', product_sku: p.sku,
                    description: `Lot ×3 — ${p.name}. Composition : ${p.food_info.lot_composition}. Même marque, même produit, même format pour les 3 unités.` }));
                  setExtraSkus(['', '']);
                }}
                data-testid={`quick-lot-${p.sku}`}
                className={`px-2.5 py-1 rounded-full text-[10px] font-semibold border transition-colors ${f.product_sku === p.sku && f.lot_type === 'SAME'
                  ? 'text-[#1F0A33] bg-[#E9CF8E] border-[#E9CF8E]'
                  : 'text-white/70 border-white/15 hover:border-[#D9B35A]/50 hover:text-[#E9CF8E]'}`}>
                {p.name}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.product}</label>
          <select value={f.product_sku} onChange={(e) => {
              if (!gateChange()) { e.target.value = f.product_sku; return; }
              setF((p) => ({ ...p, product_sku: e.target.value }));
            }}
            className={inputCls} data-testid="offer-product">
            <option value="">—</option>
            {products.map((p) => <option key={p.sku} value={p.sku}>{p.name} · {p.category}</option>)}
          </select>
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.lotType}</label>
          <select value={f.lot_type} onChange={(e) => {
              if (!gateChange()) { e.target.value = f.lot_type; return; }
              setF((p) => ({ ...p, lot_type: e.target.value }));
            }}
            className={inputCls} data-testid="offer-lot-type">
            <option value="SAME">{t.same}</option>
            <option value="COMPOSED">{t.composed}</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.qty}</label>
          <input type="number" min="1" max="50" value={f.qty_lots}
            onChange={(e) => { setConfirmedItems({}); setF((p) => ({ ...p, qty_lots: e.target.value })); }}
            className={inputCls} data-testid="offer-qty" />
        </div>
        <div className="flex items-end">
          <span className="text-xs font-bold text-[#E9CF8E]" data-testid="offer-cost">
            {cost} {t.credits}{extra ? ' (offre supplémentaire)' : ''}
          </span>
        </div>
      </div>
      <div className="grid sm:grid-cols-4 gap-3">
        <div>
          <label className="text-[10px] text-white/50 block mb-1">Prix du lot</label>
          <input type="number" min="0" step="0.01" value={f.lot_price}
            onChange={(e) => setF((p) => ({ ...p, lot_price: e.target.value }))}
            className={inputCls} data-testid="offer-lot-price" />
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">Devise</label>
          <select value={f.currency} onChange={(e) => setF((p) => ({ ...p, currency: e.target.value }))}
            className={inputCls} data-testid="offer-currency">
            {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">Réduction (min. 15 %)</label>
          <select value={f.discount_mode} onChange={(e) => setF((p) => ({ ...p, discount_mode: e.target.value }))}
            className={inputCls} data-testid="offer-discount-mode">
            <option value="PERCENT">en %</option>
            <option value="AMOUNT">en montant ({f.currency})</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">Valeur</label>
          <input type="number" min="0" step="0.01" value={f.discount_value}
            onChange={(e) => setF((p) => ({ ...p, discount_value: e.target.value }))}
            className={inputCls} data-testid="offer-discount-value" />
        </div>
      </div>
      {price > 0 && (
        <p className={`text-[11px] font-semibold ${discountKo ? 'text-red-400' : 'text-emerald-300'}`} data-testid="offer-final-price">
          {discountKo
            ? `⛔ Réduction insuffisante : ${discPct.toFixed(1)} % — minimum 15 %, l'offre ne peut pas être publiée`
            : `Prix final du lot : ${finalPrice.toFixed(2)} ${f.currency} (−${discPct.toFixed(1)} %)`}
        </p>
      )}
      <OfferPhotoPicker photos={photos} onChange={setPhotos}
        labels={f.lot_type === 'COMPOSED' && composedProducts.length > 1 ? composedProducts.map((p) => p.name) : null} />
      <div className="grid sm:grid-cols-3 gap-3">
        <div>
          <label className="text-[10px] text-white/50 block mb-1">État du produit</label>
          <select value={f.condition} onChange={(e) => setF((p) => ({ ...p, condition: e.target.value }))}
            className={inputCls} data-testid="offer-condition">
            <option value="NEW">Neuf</option>
            <option value="USED">Occasion</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">Garantie produit (optionnel)</label>
          <input value={f.warranty} onChange={(e) => setF((p) => ({ ...p, warranty: e.target.value }))}
            placeholder="ex. 6 mois constructeur" className={inputCls} data-testid="offer-warranty" />
        </div>
        {anyPerishable && (
          <div>
            <label className="text-[10px] text-amber-300 block mb-1">DLC (périssable — min. 3 mois)</label>
            <input type="date" value={f.dlc} onChange={(e) => setF((p) => ({ ...p, dlc: e.target.value }))}
              min={new Date(Date.now() + 90 * 86400000).toISOString().slice(0, 10)}
              className={inputCls} data-testid="offer-dlc" />
            {dlcKo && f.dlc && <p className="text-[9px] text-red-400 mt-0.5">DLC insuffisante : minimum 3 mois</p>}
          </div>
        )}
      </div>
      <div>
        <label className="text-[10px] text-white/50 block mb-1">Programmer l'offre (optionnel — countdown en salle)</label>
        <input type="datetime-local" value={f.scheduled_start}
          onChange={(e) => setF((p) => ({ ...p, scheduled_start: e.target.value }))}
          className={inputCls + ' sm:w-64'} data-testid="offer-scheduled-start" />
      </div>
      {f.lot_type === 'COMPOSED' && (
        <div className="grid sm:grid-cols-2 gap-3" data-testid="offer-composed-products">
          {f.product_sku && !confirmedItems[f.product_sku] && (
            <p className="col-span-full text-[10px] text-amber-300" data-testid="offer-gate-hint">
              Confirmez d'abord le 1er produit (quantité de lots + informations ci-dessous) pour ajouter le suivant.
            </p>
          )}
          {[0, 1].map((i) => {
            const prevSku = i === 0 ? f.product_sku : extraSkus[0];
            const locked = !prevSku || !confirmedItems[prevSku];
            return (
            <div key={i}>
              <label className="text-[10px] text-white/50 block mb-1">Produit {i + 2} du lot composé {i === 0 ? '' : '(optionnel)'}</label>
              <select value={extraSkus[i]} data-testid={`offer-product-${i + 2}`}
                disabled={locked}
                title={locked ? "Confirmez le produit précédent pour continuer" : undefined}
                onChange={(e) => setExtraSkus((s) => s.map((v, j) => (j === i ? e.target.value : v)))}
                className={inputCls + ' disabled:opacity-40 disabled:cursor-not-allowed'}>
                <option value="">{locked ? '— confirmez le produit précédent —' : '—'}</option>
                {products.filter((p) => p.sku !== f.product_sku && p.sku !== extraSkus[1 - i])
                  .map((p) => <option key={p.sku} value={p.sku}>{p.name} · {p.category}</option>)}
              </select>
            </div>
            );
          })}
          {composedProducts.length > 1 && (
            <p className="col-span-full text-[10px] text-emerald-300/80" data-testid="offer-composed-summary">
              Lot composé : {composedProducts.map((p) => p.name).join(' + ')}
            </p>
          )}
        </div>
      )}
      {f.lot_type === 'COMPOSED' && (
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.composedDetail}</label>
          <input value={f.composed_detail} onChange={(e) => setF((p) => ({ ...p, composed_detail: e.target.value }))}
            className={inputCls} data-testid="offer-composed" />
        </div>
      )}
      {composedProducts.length > 0 && (
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 space-y-3" data-testid="offer-items-detail">
          <p className="text-[10px] font-bold text-white/60 uppercase tracking-wide">
            Détail des articles — prix TTC{f.lot_type === 'COMPOSED' ? ' de chaque élément' : ''}, prix au kg/L, infos alimentaires (obligatoire)
          </p>
          {f.lot_type === 'SAME' && (
            <p className="text-[9px] text-white/40">Lot à unités identiques : un seul descriptif suffit (exception d'affichage du prix par élément).</p>
          )}
          {composedProducts.map((p) => {
            const d = itemOf(p.sku);
            const qtyBase = { g: ['kg', 0.001], kg: ['kg', 1], ml: ['L', 0.001], cl: ['L', 0.01], L: ['L', 1] }[d.net_qty_unit];
            const perUnit = Number(d.unit_price_ttc) > 0 && Number(d.net_qty_value) > 0 && qtyBase
              ? (Number(d.unit_price_ttc) / (Number(d.net_qty_value) * qtyBase[1])).toFixed(2) : null;
            return (
              <div key={p.sku} className="rounded-lg border border-white/[0.07] p-2.5 space-y-2" data-testid={`offer-item-${p.sku}`}>
                <p className="text-[11px] font-semibold text-[#E9CF8E]">{p.name}</p>
                <div className="grid sm:grid-cols-4 gap-2">
                  <input value={d.brand || p.brand || ''} onChange={(e) => setItem(p.sku, { brand: e.target.value })}
                    placeholder="Marque exacte" className={inputCls} data-testid={`offer-item-brand-${p.sku}`} />
                  <input value={d.format_label || ''} onChange={(e) => setItem(p.sku, { format_label: e.target.value })}
                    placeholder="Quantité (ex. 1 kg)" className={inputCls} data-testid={`offer-item-format-${p.sku}`} />
                  {f.lot_type === 'COMPOSED' && (
                    <input type="number" min="0" step="0.01" value={d.unit_price_ttc || ''}
                      onChange={(e) => setItem(p.sku, { unit_price_ttc: e.target.value })}
                      placeholder={`Prix article TTC (${f.currency})`} className={inputCls} data-testid={`offer-item-price-${p.sku}`} />
                  )}
                  <span className="flex gap-1">
                    <input type="number" min="0" step="any" value={d.net_qty_value || ''}
                      onChange={(e) => setItem(p.sku, { net_qty_value: e.target.value })}
                      placeholder="Qté nette" className={inputCls} data-testid={`offer-item-qty-${p.sku}`} />
                    <select value={d.net_qty_unit || ''} onChange={(e) => setItem(p.sku, { net_qty_unit: e.target.value })}
                      className={inputCls + ' !w-16'} data-testid={`offer-item-qty-unit-${p.sku}`}>
                      <option value="">—</option>
                      {['g', 'kg', 'ml', 'cl', 'L'].map((u) => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </span>
                </div>
                {perUnit && (
                  <p className="text-[10px] text-emerald-300/90" data-testid={`offer-item-per-unit-${p.sku}`}>
                    soit {perUnit} {f.currency}/{qtyBase[0]}
                  </p>
                )}
                <div className="grid sm:grid-cols-2 gap-2">
                  <input value={d.ingredients || ''} onChange={(e) => setItem(p.sku, { ingredients: e.target.value })}
                    placeholder="Ingrédients (obligatoire)" className={inputCls} data-testid={`offer-item-ingredients-${p.sku}`} />
                  <input value={d.allergens || ''} onChange={(e) => setItem(p.sku, { allergens: e.target.value })}
                    placeholder="Allergènes (« Aucun » si sans)" className={inputCls} data-testid={`offer-item-allergens-${p.sku}`} />
                </div>
                {itemKo(p, d) && <p className="text-[9px] text-red-400">Quantité, ingrédients et allergènes obligatoires{f.lot_type === 'COMPOSED' ? ' + prix TTC' : ''}.</p>}
                <div className="flex items-center gap-2">
                  {confirmedItems[p.sku] ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold text-emerald-300 bg-emerald-500/15 border border-emerald-400/40"
                      data-testid={`offer-item-confirmed-${p.sku}`}>
                      ✓ Lot confirmé — {f.qty_lots} lot(s)
                    </span>
                  ) : (
                    <button type="button" onClick={() => confirmItem(p.sku)}
                      data-testid={`offer-item-confirm-${p.sku}`}
                      className="px-2.5 py-1 rounded-full text-[10px] font-bold text-[#1F0A33] bg-[#E9CF8E] hover:bg-[#F2D07A] transition-colors">
                      Confirmer ce lot (quantité + informations)
                    </button>
                  )}
                </div>
              </div>
            );
          })}
          {f.lot_type === 'COMPOSED' && finalPrice > 0 && (
            <p className={`text-[10px] font-semibold ${sumKo ? 'text-red-400' : 'text-emerald-300'}`} data-testid="offer-items-sum">
              Somme des articles : {itemsSum.toFixed(2)} {f.currency} / prix du lot : {finalPrice.toFixed(2)} {f.currency}
              {sumKo ? ' — doit être égale' : ' ✓'}
            </p>
          )}
        </div>
      )}
      <div>
        <label className="text-[10px] text-white/50 block mb-1">{t.desc}</label>
        <textarea value={f.description} onChange={(e) => setF((p) => ({ ...p, description: e.target.value }))}
          rows={2} className="w-full px-2.5 py-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs"
          data-testid="offer-description" />
      </div>
      <button onClick={submit} disabled={busy || !f.product_sku || f.description.trim().length < 10 || price <= 0 || discountKo || !photos[0] || dlcKo || itemsKo}
        data-testid="offer-submit"
        className="h-9 px-5 rounded-full bg-[#D9B35A] text-black text-xs font-bold hover:bg-[#E9CF8E] disabled:opacity-40">
        {t.submit}
      </button>
    </div>
  );
};
