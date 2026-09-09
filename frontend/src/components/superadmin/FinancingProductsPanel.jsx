import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Banknote, Plus, Trash2, Pencil, Loader2, Download, TrendingUp, Trophy } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;
const STATUS = {
  OPEN: ['À financer', 'text-[#E9CF8E] bg-[#D9B35A]/10 border-[#D9B35A]/40'],
  PENDING_PAYMENT: ['Paiement en cours', 'text-sky-300 bg-sky-500/10 border-sky-400/40'],
  PAID: ['Vendu et facturé par O\u2019SCOP', 'text-[#8CC63E] bg-[#8CC63E]/15 border-[#8CC63E]/50'],
};

// Superadmin : inscription de produits au financement investisseur (marge bénéficiaire O'SCOP)
export const FinancingProductsPanel = () => {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [form, setForm] = useState({ product_id: '', name: '', base_price_eur: '', margin_percent: '' });
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

  const total = (Number(form.base_price_eur) || 0) * (1 + (Number(form.margin_percent) || 0) / 100);

  const create = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/financing-products`, {
        method: 'POST', credentials: 'include', headers,
        body: JSON.stringify({
          product_id: form.product_id || null,
          name: form.product_id ? null : form.name,
          base_price_eur: Number(form.base_price_eur),
          margin_percent: Number(form.margin_percent) || 0,
        }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`${d.reference} inscrit au financement — ${eur(d.total_price_eur)}`);
      setForm({ product_id: '', name: '', base_price_eur: '', margin_percent: '' });
      load();
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
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

  const exportCsv = () => {
    const header = ['Référence', 'Produit', 'SKU', 'Prix base €', 'Marge %', 'Total €', 'Statut', 'Payé par', 'Payé le', 'Inscrit le'];
    const lines = items.map((fp) => [fp.reference, fp.name, fp.sku, fp.base_price_eur, fp.margin_percent,
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
        </div>
      )}
      <form onSubmit={create} className="flex flex-wrap items-center gap-2 mb-4">
        <select value={form.product_id} data-testid="fin-product-select"
          onChange={(e) => setForm({ ...form, product_id: e.target.value })}
          className={`${inputCls} min-w-[190px]`}>
          <option value="" className="bg-[#1F0A33]">— Produit hors catalogue —</option>
          {catalog.map((p) => (
            <option key={p.id} value={p.id} className="bg-[#1F0A33]">{p.name} ({p.sku})</option>
          ))}
        </select>
        {!form.product_id && (
          <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Nom du produit *" className={`${inputCls} min-w-[160px]`} data-testid="fin-name-input" />
        )}
        <input required type="number" min="0.01" step="0.01" value={form.base_price_eur}
          onChange={(e) => setForm({ ...form, base_price_eur: e.target.value })}
          placeholder="Prix base € *" className={`${inputCls} w-28`} data-testid="fin-price-input" />
        <input required type="number" min="0" step="0.1" value={form.margin_percent}
          onChange={(e) => setForm({ ...form, margin_percent: e.target.value })}
          placeholder="Marge % *" className={`${inputCls} w-24`} data-testid="fin-margin-input" />
        <span className="text-[11px] text-[#8CC63E] font-bold" data-testid="fin-total-preview">
          {form.base_price_eur ? `= ${eur(total)}` : ''}
        </span>
        <button type="submit" disabled={busy} data-testid="fin-create-btn"
          className="inline-flex items-center gap-1.5 px-3 h-9 rounded-lg text-[11px] font-bold text-[#1F0A33] bg-[#D9B35A] hover:brightness-110 disabled:opacity-60">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />} Inscrire au financement
        </button>
      </form>
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
                  <span className="text-white font-semibold">{fp.reference} · {fp.name}</span>
                  <span className="text-white/40">base {eur(fp.base_price_eur)} · marge {fp.margin_percent}%</span>
                  <span className="font-mono text-[#D9B35A] font-bold">{eur(fp.total_price_eur)}</span>
                  <span className={`px-2 py-0.5 rounded-full border font-semibold ${cls}`} data-testid={`fin-status-${fp.reference}`}>{label}</span>
                  {fp.status === 'PAID' && fp.paid_by && (
                    <span className="text-white/45">payé par {fp.paid_by} le {String(fp.paid_at || '').slice(0, 10)}</span>
                  )}
                  <span className="ml-auto flex gap-1.5">
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
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
