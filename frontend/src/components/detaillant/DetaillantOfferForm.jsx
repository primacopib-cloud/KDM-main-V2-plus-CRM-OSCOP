import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../services/api.detaillant';

const inputCls = 'w-full h-9 px-2.5 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs';

export const CURRENCIES = ['EUR', 'USD', 'GBP', 'CAD', 'CHF', 'JPY', 'CNY', 'AUD', 'NZD', 'BRL', 'MXN', 'ARS', 'CLP', 'COP',
  'DOP', 'HTG', 'JMD', 'TTD', 'BBD', 'XCD', 'XPF', 'XOF', 'XAF', 'MAD', 'TND', 'DZD', 'EGP', 'ZAR', 'NGN', 'KES', 'GHS',
  'INR', 'PKR', 'BDT', 'THB', 'VND', 'IDR', 'MYR', 'SGD', 'PHP', 'KRW', 'HKD', 'TWD', 'AED', 'SAR', 'QAR', 'ILS', 'TRY',
  'RUB', 'UAH', 'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'SEK', 'NOK', 'DKK', 'ISK'];

export const DetaillantOfferForm = ({ t, info, onCreated }) => {
  const [products, setProducts] = useState([]);
  const [f, setF] = useState({ product_sku: '', lot_type: 'SAME', qty_lots: 1, description: '', composed_detail: '',
    lot_price: '', currency: 'EUR', discount_mode: 'PERCENT', discount_value: 15, scheduled_start: '' });
  const [busy, setBusy] = useState(false);
  useEffect(() => { detaillantAPI.catalog().then((r) => setProducts(r.products || [])).catch(() => {}); }, []);
  const product = products.find((p) => p.sku === f.product_sku);
  const extra = info.offers_used_this_month >= info.included_offers;
  const cost = f.qty_lots * info.credits_per_lot + (extra ? f.qty_lots * info.extra_offer_credits_per_lot : 0);
  const price = Number(f.lot_price) || 0;
  const discAmount = f.discount_mode === 'PERCENT' ? price * Number(f.discount_value || 0) / 100 : Number(f.discount_value || 0);
  const discPct = price > 0 ? (discAmount / price) * 100 : 0;
  const finalPrice = Math.max(0, price - discAmount);
  const discountKo = price > 0 && discPct < 15;
  const submit = async () => {
    setBusy(true);
    try {
      await detaillantAPI.createOffer({
        ...f, qty_lots: Number(f.qty_lots), category: product?.category,
        lot_price: price, discount_value: Number(f.discount_value),
        scheduled_start: f.scheduled_start ? new Date(f.scheduled_start).toISOString() : null,
      });
      toast.success(`✓ Offre déposée — ${cost} crédits`);
      setF({ product_sku: '', lot_type: 'SAME', qty_lots: 1, description: '', composed_detail: '',
        lot_price: '', currency: 'EUR', discount_mode: 'PERCENT', discount_value: 15, scheduled_start: '' });
      onCreated?.();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return (
    <div className="rounded-2xl border border-[#D9B35A]/30 bg-[#D9B35A]/[0.04] p-4 space-y-3" data-testid="detaillant-offer-form">
      <h3 className="text-sm font-bold text-[#E9CF8E]">{t.newOffer}</h3>
      <p className="text-[10px] text-white/45">{t.costInfo}</p>
      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.product}</label>
          <select value={f.product_sku} onChange={(e) => setF((p) => ({ ...p, product_sku: e.target.value }))}
            className={inputCls} data-testid="offer-product">
            <option value="">—</option>
            {products.map((p) => <option key={p.sku} value={p.sku}>{p.name} · {p.category}</option>)}
          </select>
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.lotType}</label>
          <select value={f.lot_type} onChange={(e) => setF((p) => ({ ...p, lot_type: e.target.value }))}
            className={inputCls} data-testid="offer-lot-type">
            <option value="SAME">{t.same}</option>
            <option value="COMPOSED">{t.composed}</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.qty}</label>
          <input type="number" min="1" max="50" value={f.qty_lots}
            onChange={(e) => setF((p) => ({ ...p, qty_lots: e.target.value }))}
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
            ? `Réduction insuffisante : ${discPct.toFixed(1)} % (minimum 15 %)`
            : `Prix final du lot : ${finalPrice.toFixed(2)} ${f.currency} (−${discPct.toFixed(1)} %)`}
        </p>
      )}
      <div>
        <label className="text-[10px] text-white/50 block mb-1">Programmer l'offre (optionnel — countdown en salle)</label>
        <input type="datetime-local" value={f.scheduled_start}
          onChange={(e) => setF((p) => ({ ...p, scheduled_start: e.target.value }))}
          className={inputCls + ' sm:w-64'} data-testid="offer-scheduled-start" />
      </div>
      {f.lot_type === 'COMPOSED' && (
        <div>
          <label className="text-[10px] text-white/50 block mb-1">{t.composedDetail}</label>
          <input value={f.composed_detail} onChange={(e) => setF((p) => ({ ...p, composed_detail: e.target.value }))}
            className={inputCls} data-testid="offer-composed" />
        </div>
      )}
      <div>
        <label className="text-[10px] text-white/50 block mb-1">{t.desc}</label>
        <textarea value={f.description} onChange={(e) => setF((p) => ({ ...p, description: e.target.value }))}
          rows={2} className="w-full px-2.5 py-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs"
          data-testid="offer-description" />
      </div>
      <button onClick={submit} disabled={busy || !f.product_sku || f.description.trim().length < 10 || price <= 0 || discountKo}
        data-testid="offer-submit"
        className="h-9 px-5 rounded-full bg-[#D9B35A] text-black text-xs font-bold hover:bg-[#E9CF8E] disabled:opacity-40">
        {t.submit}
      </button>
    </div>
  );
};
