import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Banknote, Plus, Trash2, Pencil, Loader2, Download, TrendingUp, Trophy, Truck, Package, CalendarClock, Save, X } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;
const STATUS = {
  OPEN: ['À financer', 'text-[#E9CF8E] bg-[#D9B35A]/10 border-[#D9B35A]/40'],
  PENDING_PAYMENT: ['Paiement en cours', 'text-sky-300 bg-sky-500/10 border-sky-400/40'],
  PAID: ['Vendu et facturé par O\u2019SCOP', 'text-[#8CC63E] bg-[#8CC63E]/15 border-[#8CC63E]/50'],
};
const TRACK_STEPS = [['CONFIRMEE', 'Confirmée'], ['PREPARATION', 'Préparation'], ['EXPEDITION', 'Expédiée'], ['TRANSIT', 'En transit'], ['LIVREE', 'Livrée']];

// Superadmin : inscription de produits au financement investisseur (marge bénéficiaire O'SCOP)
export const FinancingProductsPanel = () => {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [form, setForm] = useState({ kind: 'PRODUIT', product_id: '', name: '', base_price_eur: '', margin_percent: '',
    logistics_enabled: false, logistics_cost_eur: '', logistics_margin_percent: '',
    repayment_amount_eur: '', repayment_duration_months: '', repayment_date: '' });
  const [repayFor, setRepayFor] = useState(null); // fp.id dont on édite les modalités
  const [repayForm, setRepayForm] = useState({ repayment_amount_eur: '', repayment_duration_months: '', repayment_date: '' });
  const [busy, setBusy] = useState(false);

  const headers = { 'Content-Type': 'application/json', ...getAuthHeaders() };
  const load = () => {
    fetch(`${API_URL}/api/admin/financing-products`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { products: [] })).then((d) => setItems(d.products || [])).catch(() => {});
    fetch(`${API_URL}/api/admin/financing-products/stats`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then((d) => d && setStats(d)).catch(() => {});
  };
  useEffect(() => {
    load();
    fetch(`${API_URL}/api/admin/financing-products/catalog`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { products: [] })).then((d) => setCatalog(d.products || [])).catch(() => {});
  }, []);

  const logiTotal = form.logistics_enabled
    ? (Number(form.logistics_cost_eur) || 0) * (1 + (Number(form.logistics_margin_percent) || 0) / 100) : 0;
  const total = (Number(form.base_price_eur) || 0) * (1 + (Number(form.margin_percent) || 0) / 100) + logiTotal;

  const create = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/financing-products`, {
        method: 'POST', credentials: 'include', headers,
        body: JSON.stringify({
          kind: form.kind,
          product_id: form.kind === 'PRODUIT' ? form.product_id || null : null,
          name: form.kind === 'PRODUIT' && form.product_id ? null : form.name,
          base_price_eur: Number(form.base_price_eur),
          margin_percent: Number(form.margin_percent) || 0,
          logistics_cost_eur: form.logistics_enabled && form.logistics_cost_eur ? Number(form.logistics_cost_eur) : null,
          logistics_margin_percent: form.logistics_enabled && form.logistics_cost_eur ? Number(form.logistics_margin_percent) || 0 : null,
          repayment_amount_eur: form.repayment_amount_eur ? Number(form.repayment_amount_eur) : null,
          repayment_duration_months: form.repayment_duration_months ? Number(form.repayment_duration_months) : null,
          repayment_date: form.repayment_date || null,
        }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`${d.reference} inscrit au financement — ${eur(d.total_price_eur)}`);
      setForm({ kind: 'PRODUIT', product_id: '', name: '', base_price_eur: '', margin_percent: '',
        logistics_enabled: false, logistics_cost_eur: '', logistics_margin_percent: '',
        repayment_amount_eur: '', repayment_duration_months: '', repayment_date: '' });
      load();
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };

  const openRepay = (fp) => {
    setRepayFor(repayFor === fp.id ? null : fp.id);
    setRepayForm({
      repayment_amount_eur: fp.repayment_amount_eur ?? '',
      repayment_duration_months: fp.repayment_duration_months ?? '',
      repayment_date: fp.repayment_date ?? '',
    });
  };

  const saveRepay = async (fp) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/financing-products/${fp.id}`, {
        method: 'PUT', credentials: 'include', headers,
        body: JSON.stringify({
          repayment_amount_eur: repayForm.repayment_amount_eur ? Number(repayForm.repayment_amount_eur) : null,
          repayment_duration_months: repayForm.repayment_duration_months ? Number(repayForm.repayment_duration_months) : null,
          repayment_date: repayForm.repayment_date || null,
        }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`Modalités de remboursement enregistrées — ${fp.reference}`);
      setRepayFor(null);
      load();
    } catch (err) { toast.error(err.message); }
  };

  const editMargin = async (fp) => {
    const m = window.prompt(`Marge bénéficiaire O'SCOP (%) pour ${fp.name} :`, String(fp.margin_percent));
    if (m === null || m === '') return;
    try {
      const res = await fetch(`${API_URL}/api/admin/financing-products/${fp.id}`, {
        method: 'PUT', credentials: 'include', headers,
        body: JSON.stringify({ margin_percent: Number(m) }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`Marge mise à jour — total ${eur(d.total_price_eur)}`);
      load();
    } catch (err) { toast.error(err.message); }
  };

  const remove = async (fp) => {
    if (!window.confirm(`Retirer ${fp.name} du financement ?`)) return;
    try {
      const res = await fetch(`${API_URL}/api/admin/financing-products/${fp.id}`, {
        method: 'DELETE', credentials: 'include', headers: getAuthHeaders(),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success('Produit retiré du financement');
      load();
    } catch (err) { toast.error(err.message); }
  };

  const updateTracking = async (fp, payload) => {
    if (!payload.step && !payload.eta_delivery) return;
    try {
      const res = await fetch(`${API_URL}/api/admin/financing-products/${fp.id}/tracking`, {
        method: 'PUT', credentials: 'include', headers,
        body: JSON.stringify(payload),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(payload.eta_delivery
        ? 'Date de livraison estimée annoncée (investisseur notifié)'
        : `Suivi mis à jour — ${TRACK_STEPS.find(([k]) => k === payload.step)?.[1]} (investisseur notifié)`);
      load();
    } catch (err) { toast.error(err.message); }
  };

  const uploadProof = async (fp, file) => {
    if (!file) return;
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`${API_URL}/api/admin/financing-products/${fp.id}/delivery-proof`, {
        method: 'POST', credentials: 'include',
        headers: getAuthHeaders(),
        body: fd,
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success('Preuve de livraison jointe — visible par l\'investisseur');
      load();
    } catch (err) { toast.error(err.message); }
  };

  const exportCsv = () => {
    const header = ['Référence', 'Type', 'Produit', 'SKU', 'Prix base €', 'Marge %', 'Total €', 'Statut', 'Payé par', 'Payé le', 'Inscrit le'];
    const lines = items.map((fp) => [fp.reference, fp.kind === 'LOGISTIQUE' ? 'Logistique' : 'Produit', fp.name, fp.sku, fp.base_price_eur, fp.margin_percent,
      fp.total_price_eur, STATUS[fp.status]?.[0] || fp.status, fp.paid_by, String(fp.paid_at || '').slice(0, 10),
      String(fp.created_at || '').slice(0, 10)]);
    const csv = [header, ...lines]
      .map((l) => l.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(';')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `financements-produits-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast.success('Export CSV des financements téléchargé');
  };

  const inputCls = 'h-9 px-2.5 rounded-lg bg-white/[0.06] border border-white/15 text-white text-xs placeholder:text-white/35';

  return (
    <div className="rounded-2xl p-5 mt-6 bg-white/[0.03] border border-white/[0.08]" data-testid="financing-products-panel">
      <div className="flex items-center gap-2 mb-1">
        <Banknote className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Produits au financement investisseurs ({items.length})</h3>
        {items.length > 0 && (
          <button type="button" onClick={exportCsv} data-testid="fin-export-csv-btn"
            className="ml-auto inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-bold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1]">
            <Download className="w-3 h-3" /> Export CSV
          </button>
        )}
      </div>
      <p className="text-[11px] text-white/45 m-0 mb-3">
        Seul le superadmin inscrit un produit au financement et lui attribue une marge bénéficiaire O'SCOP.
        <b className="text-[#E9CF8E]"> Tous les produits et prestations de cet espace sont vendus et facturés par O'SCOP.</b>
        {' '}La logistique LOGI'SCOP (coût + marge) peut être ajoutée en option — elle est soumise au même financement.
        Une fois payé par un investisseur, le produit passe « Vendu et facturé par O'SCOP ».
      </p>
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4" data-testid="fin-stats-block">
          <div className="rounded-xl px-3 py-2.5 bg-[#8CC63E]/10 border border-[#8CC63E]/30" data-testid="fin-stat-total">
            <div className="text-[10px] uppercase tracking-wide text-white/50 flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-[#8CC63E]" /> Total financé
            </div>
            <div className="text-base font-bold text-[#8CC63E]">{eur(stats.total_financed_eur)}</div>
            <div className="text-[10px] text-white/45">{stats.paid_count} produit(s) payé(s)</div>
          </div>
          <div className="rounded-xl px-3 py-2.5 bg-[#D9B35A]/10 border border-[#D9B35A]/30" data-testid="fin-stat-margin">
            <div className="text-[10px] uppercase tracking-wide text-white/50">Marge cumulée O'SCOP</div>
            <div className="text-base font-bold text-[#E9CF8E]">{eur(stats.margin_cumul_eur)}</div>
            <div className="text-[10px] text-white/45">{stats.open_count} à financer · {stats.pending_count} en cours</div>
          </div>
          <div className="rounded-xl px-3 py-2.5 bg-white/[0.04] border border-white/10 col-span-2" data-testid="fin-stat-top">
            <div className="text-[10px] uppercase tracking-wide text-white/50 flex items-center gap-1 mb-1">
              <Trophy className="w-3 h-3 text-[#D9B35A]" /> Top investisseurs
            </div>
            {stats.top_investors?.length ? (
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-white/70">
                {stats.top_investors.map((t, i) => (
                  <span key={t.email} data-testid={`fin-top-investor-${i}`}>
                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`}{' '}
                    <b className="text-white/90">{t.email}</b> — {eur(t.total_eur)} ({t.products_count})
                  </span>
                ))}
              </div>
            ) : <p className="text-[11px] text-white/35 m-0">Aucun paiement pour le moment.</p>}
          </div>
          {stats.monthly?.length > 0 && (
            <div className="rounded-xl px-3 py-2.5 bg-white/[0.04] border border-white/10 col-span-2 lg:col-span-4" data-testid="fin-monthly-chart">
              <div className="text-[10px] uppercase tracking-wide text-white/50 mb-2">Montant financé par mois</div>
              <div className="flex items-end gap-2 h-20">
                {stats.monthly.map((m) => {
                  const max = Math.max(...stats.monthly.map((x) => x.total_eur), 1);
                  return (
                    <div key={m.month} className="flex-1 flex flex-col items-center gap-1 min-w-0" data-testid={`fin-month-${m.month}`}>
                      <span className="text-[9px] text-[#8CC63E] font-bold whitespace-nowrap">{Number(m.total_eur).toLocaleString('fr-FR')} €</span>
                      <div className="w-full max-w-[46px] rounded-t-md transition-[height] duration-500"
                        style={{ height: `${Math.max(8, Math.round((m.total_eur / max) * 52))}px`,
                          background: 'linear-gradient(180deg, #8CC63E, #D9B35A)' }} />
                      <span className="text-[9px] text-white/45">{m.month.slice(5)}/{m.month.slice(2, 4)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
      <form onSubmit={create} className="flex flex-wrap items-center gap-2 mb-4">
        <select value={form.kind} data-testid="fin-kind-select"
          onChange={(e) => setForm({ ...form, kind: e.target.value, product_id: '' })}
          className={`${inputCls} w-32`}>
          <option value="PRODUIT" className="bg-[#1F0A33]">📦 Produit</option>
          <option value="LOGISTIQUE" className="bg-[#1F0A33]">🚚 Logistique</option>
        </select>
        {form.kind === 'PRODUIT' && (
          <select value={form.product_id} data-testid="fin-product-select"
            onChange={(e) => setForm({ ...form, product_id: e.target.value })}
            className={`${inputCls} min-w-[190px]`}>
            <option value="" className="bg-[#1F0A33]">— Produit hors catalogue —</option>
            {catalog.map((p) => (
              <option key={p.id} value={p.id} className="bg-[#1F0A33]">{p.name} ({p.sku})</option>
            ))}
          </select>
        )}
        {(form.kind === 'LOGISTIQUE' || !form.product_id) && (
          <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder={form.kind === 'LOGISTIQUE' ? "Prestation logistique (ex. Fret conteneur 20' GP→FR) *" : 'Nom du produit *'}
            className={`${inputCls} min-w-[220px]`} data-testid="fin-name-input" />
        )}
        <input required type="number" min="0.01" step="0.01" value={form.base_price_eur}
          onChange={(e) => setForm({ ...form, base_price_eur: e.target.value })}
          placeholder="Prix base € *" className={`${inputCls} w-28`} data-testid="fin-price-input" />
        <input required type="number" min="0" step="0.1" value={form.margin_percent}
          onChange={(e) => setForm({ ...form, margin_percent: e.target.value })}
          placeholder="Marge % *" className={`${inputCls} w-24`} data-testid="fin-margin-input" />
        <span className="text-[11px] text-[#8CC63E] font-bold" data-testid="fin-total-preview">
          {form.base_price_eur ? `= ${eur(total)}${form.logistics_enabled && form.logistics_cost_eur ? ` (dont logi ${eur(logiTotal)})` : ''}` : ''}
        </span>
        <button type="submit" disabled={busy} data-testid="fin-create-btn"
          className="inline-flex items-center gap-1.5 px-3 h-9 rounded-lg text-[11px] font-bold text-[#1F0A33] bg-[#D9B35A] hover:brightness-110 disabled:opacity-60">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />} Inscrire au financement
        </button>
      </form>
      <div className="flex flex-wrap items-center gap-2 mb-4 -mt-2">
        <label className="inline-flex items-center gap-1.5 text-[11px] text-sky-300 cursor-pointer" data-testid="fin-logistics-toggle">
          <input type="checkbox" checked={form.logistics_enabled}
            onChange={(e) => setForm({ ...form, logistics_enabled: e.target.checked })} />
          <Truck className="w-3.5 h-3.5" /> Option logistique LOGI'SCOP (coût + marge, soumise au financement)
        </label>
        {form.logistics_enabled && (
          <>
            <input type="number" min="0.01" step="0.01" value={form.logistics_cost_eur}
              onChange={(e) => setForm({ ...form, logistics_cost_eur: e.target.value })}
              placeholder="Coût logistique € *" className={`${inputCls} w-36`} data-testid="fin-logistics-cost-input" />
            <input type="number" min="0" step="0.1" value={form.logistics_margin_percent}
              onChange={(e) => setForm({ ...form, logistics_margin_percent: e.target.value })}
              placeholder="Marge LOGI'SCOP %" className={`${inputCls} w-36`} data-testid="fin-logistics-margin-input" />
          </>
        )}
        <span className="inline-flex items-center gap-1 text-[11px] text-[#E9CF8E]/80 ml-2">
          <CalendarClock className="w-3.5 h-3.5" /> Remboursement :
        </span>
        <input type="number" min="0" step="0.01" value={form.repayment_amount_eur}
          onChange={(e) => setForm({ ...form, repayment_amount_eur: e.target.value })}
          placeholder="Montant €" className={`${inputCls} w-24`} data-testid="fin-repay-amount-input" />
        <input type="number" min="1" step="1" value={form.repayment_duration_months}
          onChange={(e) => setForm({ ...form, repayment_duration_months: e.target.value })}
          placeholder="Durée (mois)" className={`${inputCls} w-28`} data-testid="fin-repay-months-input" />
        <input type="date" value={form.repayment_date}
          onChange={(e) => setForm({ ...form, repayment_date: e.target.value })}
          title="Date de remboursement prévue" className={`${inputCls} [color-scheme:dark]`} data-testid="fin-repay-date-input" />
      </div>
      {!items.length ? (
        <p className="text-[11px] text-white/40 m-0">Aucun produit inscrit au financement pour le moment.</p>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {items.map((fp) => {
            const [label, cls] = STATUS[fp.status] || STATUS.OPEN;
            return (
              <div key={fp.id} className="rounded-xl px-3 py-2.5 bg-white/[0.02] border border-white/[0.06] text-[11px] text-white/70"
                data-testid={`fin-row-${fp.reference}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase border ${
                    fp.kind === 'LOGISTIQUE'
                      ? 'text-sky-300 bg-sky-500/10 border-sky-400/40'
                      : 'text-[#E9CF8E] bg-[#D9B35A]/10 border-[#D9B35A]/40'}`}
                    data-testid={`fin-kind-${fp.reference}`}>
                    {fp.kind === 'LOGISTIQUE' ? <Truck className="w-2.5 h-2.5" /> : <Package className="w-2.5 h-2.5" />}
                    {fp.kind === 'LOGISTIQUE' ? 'Logistique' : 'Produit'}
                  </span>
                  <span className="text-white font-semibold">{fp.reference} · {fp.name}</span>
                  <span className="px-2 py-0.5 rounded-full border font-semibold text-[9px] uppercase text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/40"
                    data-testid={`fin-soldby-${fp.reference}`}>Vendu & facturé par O'SCOP</span>
                  <span className="text-white/40">base {eur(fp.base_price_eur)} · marge {fp.margin_percent}%</span>
                  {fp.logistics_cost_eur > 0 && (
                    <span className="inline-flex items-center gap-1 text-sky-300" data-testid={`fin-logi-${fp.reference}`}>
                      <Truck className="w-3 h-3" /> logi {eur(fp.logistics_cost_eur)} + marge {fp.logistics_margin_percent || 0}% = {eur(fp.logistics_total_eur)}
                    </span>
                  )}
                  <span className="font-mono text-[#D9B35A] font-bold">{eur(fp.total_price_eur)}</span>
                  <span className={`px-2 py-0.5 rounded-full border font-semibold ${cls}`} data-testid={`fin-status-${fp.reference}`}>{label}</span>
                  {fp.status === 'PAID' && fp.paid_by && (
                    <span className="text-white/45">payé par {fp.paid_by} le {String(fp.paid_at || '').slice(0, 10)}</span>
                  )}
                  {fp.status === 'PAID' && (
                    <span className="inline-flex items-center gap-1.5 flex-wrap">
                      <span className="text-white/40">🚚</span>
                      <select value={fp.tracking_status || ''} data-testid={`fin-tracking-select-${fp.reference}`}
                        onChange={(e) => updateTracking(fp, { step: e.target.value })}
                        className="h-7 px-1.5 rounded-md bg-white/[0.08] border border-white/20 text-white text-[10px]">
                        <option value="" disabled className="bg-[#1F0A33]">Suivi logistique…</option>
                        {TRACK_STEPS.map(([k, l]) => (
                          <option key={k} value={k} className="bg-[#1F0A33]">{l}</option>
                        ))}
                      </select>
                      <input type="date" defaultValue={fp.eta_delivery || ''} data-testid={`fin-eta-input-${fp.reference}`}
                        title="Date de livraison estimée (annoncée à l'investisseur)"
                        onChange={(e) => e.target.value && updateTracking(fp, { eta_delivery: e.target.value })}
                        className="h-7 px-1.5 rounded-md bg-white/[0.08] border border-white/20 text-white text-[10px] [color-scheme:dark]" />
                      <label title="Joindre une preuve de livraison (photo ou bon signé PDF)"
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-[10px] cursor-pointer text-sky-300 bg-sky-500/10 border border-sky-400/40 hover:bg-sky-500/20">
                        📎 {fp.delivery_proof ? 'Preuve ✓' : 'Preuve'}
                        <input type="file" accept="image/png,image/jpeg,image/webp,application/pdf" className="hidden"
                          data-testid={`fin-proof-input-${fp.reference}`}
                          onChange={(e) => { uploadProof(fp, e.target.files?.[0]); e.target.value = ''; }} />
                      </label>
                    </span>
                  )}
                  <span className="ml-auto flex gap-1.5">
                    <button type="button" onClick={() => openRepay(fp)} data-testid={`fin-repay-${fp.reference}`}
                      title="Modalités de remboursement (montant, durée, date)"
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-sky-300 bg-sky-500/10 border border-sky-400/40 hover:bg-sky-500/20">
                      <CalendarClock className="w-3 h-3" /> Modalités
                    </button>
                    {fp.status !== 'PAID' && (
                      <>
                        <button type="button" onClick={() => editMargin(fp)} data-testid={`fin-edit-${fp.reference}`}
                          title="Modifier la marge bénéficiaire"
                          className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1]">
                          <Pencil className="w-3 h-3" /> Marge
                        </button>
                        <button type="button" onClick={() => remove(fp)} data-testid={`fin-delete-${fp.reference}`}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-red-300 bg-red-500/10 border border-red-400/40 hover:bg-red-500/20">
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </>
                    )}
                  </span>
                </div>
                {(fp.repayment_amount_eur || fp.repayment_duration_months || fp.repayment_date) && repayFor !== fp.id && (
                  <p className="m-0 mt-1.5 text-[10.5px] text-sky-200/90" data-testid={`fin-repay-info-${fp.reference}`}>
                    💶 Remboursement investisseur : <b>{fp.repayment_amount_eur ? eur(fp.repayment_amount_eur) : '—'}</b>
                    {fp.repayment_duration_months ? ` sur ${fp.repayment_duration_months} mois` : ''}
                    {fp.repayment_date ? ` — échéance ${new Date(fp.repayment_date).toLocaleDateString('fr-FR')}` : ''}
                  </p>
                )}
                {repayFor === fp.id && (
                  <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg bg-sky-500/[0.07] border border-sky-400/25 p-2"
                    data-testid={`fin-repay-editor-${fp.reference}`}>
                    <span className="text-[10px] font-bold text-sky-300 uppercase tracking-wide">Modalités de remboursement</span>
                    <input type="number" min="0" step="0.01" value={repayForm.repayment_amount_eur}
                      onChange={(e) => setRepayForm({ ...repayForm, repayment_amount_eur: e.target.value })}
                      placeholder="Montant €" className="h-7 px-1.5 rounded-md bg-white/[0.08] border border-white/20 text-white text-[10px] w-24"
                      data-testid={`fin-repay-amount-${fp.reference}`} />
                    <input type="number" min="1" step="1" value={repayForm.repayment_duration_months}
                      onChange={(e) => setRepayForm({ ...repayForm, repayment_duration_months: e.target.value })}
                      placeholder="Durée (mois)" className="h-7 px-1.5 rounded-md bg-white/[0.08] border border-white/20 text-white text-[10px] w-28"
                      data-testid={`fin-repay-months-${fp.reference}`} />
                    <input type="date" value={repayForm.repayment_date}
                      onChange={(e) => setRepayForm({ ...repayForm, repayment_date: e.target.value })}
                      className="h-7 px-1.5 rounded-md bg-white/[0.08] border border-white/20 text-white text-[10px] [color-scheme:dark]"
                      data-testid={`fin-repay-date-${fp.reference}`} />
                    <button type="button" onClick={() => saveRepay(fp)} data-testid={`fin-repay-save-${fp.reference}`}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-[10px] text-[#1F0A33] bg-[#8CC63E] hover:brightness-110">
                      <Save className="w-3 h-3" /> Enregistrer
                    </button>
                    <button type="button" onClick={() => setRepayFor(null)} data-testid={`fin-repay-cancel-${fp.reference}`}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-[10px] text-white/60 bg-white/[0.05] border border-white/15 hover:bg-white/[0.1]">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
