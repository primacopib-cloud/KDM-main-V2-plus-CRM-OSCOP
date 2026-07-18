import { getSessionToken } from '../services/http';
import { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import {
  Loader2, Download, RefreshCw, ExternalLink, ArrowLeft, AlertTriangle, Lock, Unlock,
  RotateCcw, ChevronLeft, ChevronRight,
} from "lucide-react";
import NavBar from "../components/NavBar";

import {
  API, ACCOUNT_LABEL, ACCOUNT_COLOR, KIND_LABEL, STATUS_FILTERS, PAGE_SIZE,
  formatEur, isoToday, isoNDaysAgo, fmtDateTime,
} from "../components/reconciliation/reconciliationUtils";
import {
  ModeBadge, TotalCard, AccountTotalCard, RefundStat, RefundBadge, ByKindCard,
} from "../components/reconciliation/ReconciliationCards";

const CHART_MARGIN = { top: 10, right: 12, left: 0, bottom: 8 };
const TICK_11 = { fontSize: 11 };
const TOOLTIP_STYLE = { background: "#fff", border: "1px solid rgba(212,175,55,0.3)", borderRadius: 12 };
const BAR_RADIUS_FLAT = [0, 0, 0, 0];
const BAR_RADIUS_TOP = [6, 6, 0, 0];


export default function StripeReconciliationPage() {
  const navigate = useNavigate();
  const [dateFrom, setDateFrom] = useState(isoNDaysAgo(30));
  const [dateTo, setDateTo] = useState(isoToday());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Transactions table state
  const [txStatus, setTxStatus] = useState("all");
  const [txAccount, setTxAccount] = useState("");
  const [txPage, setTxPage] = useState(0);
  const [txData, setTxData] = useState({ items: [], total: 0 });
  const [txLoading, setTxLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const token = getSessionToken();
      const resp = await fetch(
        `${API}/admin/stripe/reconciliation?date_from=${dateFrom}&date_to=${dateTo}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (resp.status === 403) {
        setError("Accès réservé aux administrateurs.");
        setData(null);
        return;
      }
      if (!resp.ok) {
        const j = await resp.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${resp.status}`);
      }
      const json = await resp.json();
      setData(json);
    } catch (e) {
      setError(e.message || "Erreur de chargement");
      toast.error(e.message || "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  const fetchTransactions = useCallback(async () => {
    setTxLoading(true);
    try {
      const token = getSessionToken();
      const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo,
        status_filter: txStatus,
        limit: String(PAGE_SIZE),
        skip: String(txPage * PAGE_SIZE),
      });
      if (txAccount) params.set("account", txAccount);
      const resp = await fetch(
        `${API}/admin/stripe/reconciliation/transactions?${params.toString()}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      setTxData(json);
    } catch (e) {
      toast.error(e.message || "Erreur transactions");
    } finally {
      setTxLoading(false);
    }
  }, [dateFrom, dateTo, txStatus, txAccount, txPage]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  // Reset pagination when filters change
  useEffect(() => {
    setTxPage(0);
  }, [txStatus, txAccount, dateFrom, dateTo]);

  const handleExportCsv = async () => {
    try {
      const token = getSessionToken();
      const resp = await fetch(
        `${API}/admin/stripe/reconciliation/export.csv?date_from=${dateFrom}&date_to=${dateTo}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!resp.ok) {
        throw new Error("Export refusé");
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `stripe_reconciliation_${dateFrom}_${dateTo}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Export CSV téléchargé");
    } catch (e) {
      toast.error(e.message || "Erreur d'export");
    }
  };

  const grandTotalCents = useMemo(() => {
    if (!data) return 0;
    return (data.totals?.oscop?.amount_cents || 0) + (data.totals?.kdmarche?.amount_cents || 0);
  }, [data]);

  const grandTotalCount = useMemo(() => {
    if (!data) return 0;
    return (data.totals?.oscop?.count || 0) + (data.totals?.kdmarche?.count || 0);
  }, [data]);

  const grandRefundCents = useMemo(() => {
    if (!data) return 0;
    const o = data.totals?.oscop || {};
    const k = data.totals?.kdmarche || {};
    return (o.refund_full_cents || 0) + (o.refund_partial_cents || 0)
      + (k.refund_full_cents || 0) + (k.refund_partial_cents || 0);
  }, [data]);

  const grandNetCents = grandTotalCents - grandRefundCents;
  const totalPages = Math.max(1, Math.ceil((txData.total || 0) / PAGE_SIZE));

  return (
    <div className="min-h-screen" data-testid="stripe-reconciliation-page">
      <NavBar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <button
              type="button"
              onClick={() => navigate("/admin")}
              data-testid="reco-back-btn"
              className="inline-flex items-center gap-2 text-sm mb-3 opacity-70 hover:opacity-100 transition-opacity"
            >
              <ArrowLeft size={14} /> Admin
            </button>
            <h1 className="font-display text-3xl sm:text-4xl" style={{ color: "#F7F2E9" }}>
              Réconciliation Stripe
            </h1>
            <p className="text-sm opacity-70 mt-2">
              Paiements et remboursements par compte Stripe — destiné à votre comptable
            </p>
          </div>

          <ModeBadge mode={data?.stripe_mode} />
        </div>

        {/* Filters */}
        <div className="glass-panel rounded-2xl p-5 mb-6">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-xs uppercase tracking-wide opacity-60 mb-1.5">Du</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                data-testid="reco-date-from"
                className="px-3 py-2 rounded-lg bg-white border"
                style={{ borderColor: "rgba(212,175,55,0.30)" }}
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wide opacity-60 mb-1.5">Au</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                data-testid="reco-date-to"
                className="px-3 py-2 rounded-lg bg-white border"
                style={{ borderColor: "rgba(212,175,55,0.30)" }}
              />
            </div>
            <button
              type="button"
              onClick={() => { fetchData(); fetchTransactions(); }}
              data-testid="reco-refresh-btn"
              className="btn-ghost h-10 px-4 rounded-lg inline-flex items-center gap-2"
            >
              <RefreshCw size={14} /> Actualiser
            </button>
            <div className="flex-1" />
            <button
              type="button"
              onClick={handleExportCsv}
              data-testid="reco-export-csv-btn"
              className="btn-gold h-10 px-5 rounded-lg inline-flex items-center gap-2"
            >
              <Download size={14} /> Exporter CSV
            </button>
          </div>
        </div>

        {error && (
          <div className="glass-panel rounded-2xl p-6 text-center" data-testid="reco-error">
            <AlertTriangle className="mx-auto mb-3 text-orange-500" size={32} />
            <p className="font-medium">{error}</p>
          </div>
        )}

        {loading && !error && (
          <div className="glass-panel rounded-2xl p-10 text-center">
            <Loader2 className="animate-spin mx-auto" size={32} style={{ color: "var(--kdm-or-metallise)" }} />
            <p className="text-sm opacity-60 mt-3">Calcul en cours…</p>
          </div>
        )}

        {!loading && !error && data && (
          <>
            {/* Global totals row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <TotalCard
                title="Total encaissé brut"
                amount={grandTotalCents}
                count={grandTotalCount}
                accent="var(--kdm-or-metallise)"
                testid="reco-total-global"
              />
              <TotalCard
                title="Total remboursé"
                amount={grandRefundCents}
                count={null}
                accent="#E64432"
                testid="reco-total-refunds"
                negative
              />
              <TotalCard
                title="Net comptable (brut − remboursé)"
                amount={grandNetCents}
                count={null}
                accent="var(--kdm-bleu-logistique)"
                testid="reco-total-net"
              />
            </div>

            {/* Per-account totals */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <AccountTotalCard account="oscop" data={data.totals?.oscop} link={data.dashboard_links?.oscop} testid="reco-total-oscop" />
              <AccountTotalCard account="kdmarche" data={data.totals?.kdmarche} link={data.dashboard_links?.kdmarche} testid="reco-total-kdmarche" />
            </div>

            {/* Daily chart */}
            <div className="glass-panel rounded-2xl p-5 mb-6" data-testid="reco-daily-chart">
              <h2 className="font-display text-xl mb-4" style={{ color: "#F7F2E9" }}>
                Encaissements quotidiens (net après remboursement)
              </h2>
              <div style={{ width: "100%", height: 320 }}>
                <ResponsiveContainer>
                  <BarChart data={data.by_day} margin={CHART_MARGIN}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,42,58,0.08)" />
                    <XAxis dataKey="day" tick={TICK_11} stroke="rgba(31,42,58,0.6)" />
                    <YAxis tick={TICK_11} stroke="rgba(31,42,58,0.6)" tickFormatter={(v) => `${v} €`} />
                    <Tooltip
                      formatter={(value, name) => {
                        const a = name.replace("_net_eur", "").replace("_eur", "");
                        return [`${Number(value).toFixed(2)} €`, ACCOUNT_LABEL[a] || name];
                      }}
                      labelFormatter={(d) => `Jour : ${d}`}
                      contentStyle={TOOLTIP_STYLE}
                    />
                    <Legend
                      formatter={(v) => ACCOUNT_LABEL[v.replace("_net_eur", "").replace("_eur", "")] || v}
                    />
                    <Bar dataKey="oscop_net_eur" stackId="x" fill={ACCOUNT_COLOR.oscop} radius={BAR_RADIUS_FLAT} />
                    <Bar dataKey="kdmarche_net_eur" stackId="x" fill={ACCOUNT_COLOR.kdmarche} radius={BAR_RADIUS_TOP} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* By kind table */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {["oscop", "kdmarche"].map((account) => (
                <ByKindCard
                  key={account}
                  account={account}
                  byKind={data.by_kind?.[account] || {}}
                  testid={`reco-bykind-${account}`}
                />
              ))}
            </div>

            {/* Transactions list */}
            <div className="glass-panel rounded-2xl p-5" data-testid="reco-transactions">
              <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
                <h2 className="font-display text-xl" style={{ color: "#F7F2E9" }}>
                  Détail des transactions
                </h2>
                <div className="flex flex-wrap items-end gap-3">
                  <div>
                    <label className="block text-xs uppercase tracking-wide opacity-60 mb-1.5">Statut</label>
                    <select
                      value={txStatus}
                      onChange={(e) => setTxStatus(e.target.value)}
                      data-testid="reco-tx-status-filter"
                      className="px-3 py-2 rounded-lg bg-white border text-sm"
                      style={{ borderColor: "rgba(212,175,55,0.30)" }}
                    >
                      {STATUS_FILTERS.map((s) => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-wide opacity-60 mb-1.5">Compte</label>
                    <select
                      value={txAccount}
                      onChange={(e) => setTxAccount(e.target.value)}
                      data-testid="reco-tx-account-filter"
                      className="px-3 py-2 rounded-lg bg-white border text-sm"
                      style={{ borderColor: "rgba(212,175,55,0.30)" }}
                    >
                      <option value="">Tous les comptes</option>
                      <option value="oscop">O&apos;SCOP OUTREMER</option>
                      <option value="kdmarche">KDMARCHE</option>
                    </select>
                  </div>
                </div>
              </div>

              {txLoading && (
                <div className="text-center py-8 opacity-60">
                  <Loader2 className="animate-spin inline" size={20} />
                </div>
              )}

              {!txLoading && txData.items.length === 0 && (
                <div className="text-center py-10 opacity-60 text-sm">
                  Aucune transaction sur la période.
                </div>
              )}

              {!txLoading && txData.items.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" data-testid="reco-tx-table">
                    <thead>
                      <tr className="border-b" style={{ borderColor: "rgba(212,175,55,0.25)" }}>
                        <th className="text-left py-2 pr-3 font-medium opacity-70">Date</th>
                        <th className="text-left py-2 pr-3 font-medium opacity-70">Compte</th>
                        <th className="text-left py-2 pr-3 font-medium opacity-70">Type</th>
                        <th className="text-left py-2 pr-3 font-medium opacity-70">Email</th>
                        <th className="text-right py-2 pr-3 font-medium opacity-70">Brut</th>
                        <th className="text-right py-2 pr-3 font-medium opacity-70">Remboursé</th>
                        <th className="text-right py-2 pr-3 font-medium opacity-70">Net</th>
                        <th className="text-left py-2 font-medium opacity-70">Statut</th>
                      </tr>
                    </thead>
                    <tbody>
                      {txData.items.map((tx) => (
                        <tr
                          key={tx.id}
                          className="border-b transition-colors hover:bg-amber-50/40"
                          style={{ borderColor: "rgba(212,175,55,0.12)" }}
                          data-testid={`reco-tx-row-${tx.id}`}
                        >
                          <td className="py-2 pr-3 tabular-nums whitespace-nowrap">
                            {fmtDateTime(tx.applied_at)}
                          </td>
                          <td className="py-2 pr-3">
                            <span
                              className="inline-block px-2 py-0.5 rounded text-xs font-medium"
                              style={{
                                color: ACCOUNT_COLOR[tx.stripe_account],
                                background: ACCOUNT_COLOR[tx.stripe_account] + "1A",
                              }}
                            >
                              {ACCOUNT_LABEL[tx.stripe_account] || tx.stripe_account}
                            </span>
                          </td>
                          <td className="py-2 pr-3">{tx.kind}</td>
                          <td className="py-2 pr-3 max-w-[200px] truncate" title={tx.user_email}>
                            {tx.user_email || "—"}
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums">
                            {formatEur(tx.amount_cents)}
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums" style={{ color: tx.refund_amount_cents ? "#E64432" : "inherit" }}>
                            {tx.refund_amount_cents ? `− ${formatEur(tx.refund_amount_cents)}` : "—"}
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums font-medium">
                            {formatEur(tx.net_amount_cents)}
                          </td>
                          <td className="py-2">
                            <RefundBadge status={tx.refund_status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {!txLoading && txData.total > PAGE_SIZE && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t" style={{ borderColor: "rgba(212,175,55,0.18)" }}>
                  <div className="text-xs opacity-60">
                    {txData.total} transaction{txData.total > 1 ? "s" : ""} — page {txPage + 1} / {totalPages}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setTxPage((p) => Math.max(0, p - 1))}
                      disabled={txPage === 0}
                      data-testid="reco-tx-prev"
                      className="btn-ghost h-8 px-3 rounded-lg inline-flex items-center gap-1 disabled:opacity-30"
                    >
                      <ChevronLeft size={14} /> Précédent
                    </button>
                    <button
                      type="button"
                      onClick={() => setTxPage((p) => Math.min(totalPages - 1, p + 1))}
                      disabled={txPage >= totalPages - 1}
                      data-testid="reco-tx-next"
                      className="btn-ghost h-8 px-3 rounded-lg inline-flex items-center gap-1 disabled:opacity-30"
                    >
                      Suivant <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

