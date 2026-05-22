import { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import {
  Loader2, Download, RefreshCw, ExternalLink, ArrowLeft, AlertTriangle, Lock, Unlock,
} from "lucide-react";
import NavBar from "../components/NavBar";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const ACCOUNT_LABEL = {
  oscop: "O'SCOP OUTREMER",
  kdmarche: "KDMARCHE",
};
const ACCOUNT_COLOR = {
  oscop: "#0B4D87",      // Bleu logistique
  kdmarche: "#D4AF37",   // Or métallisé
};
const KIND_LABEL = {
  PASS: "PASS Vie Chère (60 €)",
  RECHARGE: "Recharges UC",
  ORDER: "Commandes DRIVE",
};

function formatEur(cents) {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format((cents || 0) / 100);
}

function isoToday() {
  return new Date().toISOString().slice(0, 10);
}

function isoNDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

export default function StripeReconciliationPage() {
  const navigate = useNavigate();
  const [dateFrom, setDateFrom] = useState(isoNDaysAgo(30));
  const [dateTo, setDateTo] = useState(isoToday());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("token");
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

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExportCsv = async () => {
    try {
      const token = localStorage.getItem("token");
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
            <h1 className="font-display text-3xl sm:text-4xl" style={{ color: "var(--kdm-bleu-logistique)" }}>
              Réconciliation Stripe
            </h1>
            <p className="text-sm opacity-70 mt-2">
              Paiements encaissés par compte Stripe — destiné à votre comptable
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
              onClick={fetchData}
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
            {/* Totals row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <TotalCard
                title="Total global encaissé"
                amount={grandTotalCents}
                count={grandTotalCount}
                accent="var(--kdm-or-metallise)"
                testid="reco-total-global"
              />
              <AccountTotalCard account="oscop" data={data.totals?.oscop} link={data.dashboard_links?.oscop} testid="reco-total-oscop" />
              <AccountTotalCard account="kdmarche" data={data.totals?.kdmarche} link={data.dashboard_links?.kdmarche} testid="reco-total-kdmarche" />
            </div>

            {/* Daily chart */}
            <div className="glass-panel rounded-2xl p-5 mb-6" data-testid="reco-daily-chart">
              <h2 className="font-display text-xl mb-4" style={{ color: "var(--kdm-bleu-logistique)" }}>
                Encaissements quotidiens
              </h2>
              <div style={{ width: "100%", height: 320 }}>
                <ResponsiveContainer>
                  <BarChart data={data.by_day} margin={{ top: 10, right: 12, left: 0, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,42,58,0.08)" />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} stroke="rgba(31,42,58,0.6)" />
                    <YAxis tick={{ fontSize: 11 }} stroke="rgba(31,42,58,0.6)" tickFormatter={(v) => `${v} €`} />
                    <Tooltip
                      formatter={(value, name) => [`${Number(value).toFixed(2)} €`, ACCOUNT_LABEL[name.replace("_eur", "")] || name]}
                      labelFormatter={(d) => `Jour : ${d}`}
                      contentStyle={{ background: "#fff", border: "1px solid rgba(212,175,55,0.3)", borderRadius: 12 }}
                    />
                    <Legend formatter={(v) => ACCOUNT_LABEL[v.replace("_eur", "")] || v} />
                    <Bar dataKey="oscop_eur" stackId="x" fill={ACCOUNT_COLOR.oscop} radius={[0, 0, 0, 0]} />
                    <Bar dataKey="kdmarche_eur" stackId="x" fill={ACCOUNT_COLOR.kdmarche} radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* By kind table */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {["oscop", "kdmarche"].map((account) => (
                <ByKindCard
                  key={account}
                  account={account}
                  byKind={data.by_kind?.[account] || {}}
                  testid={`reco-bykind-${account}`}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ModeBadge({ mode }) {
  if (!mode) return null;
  const isLive = mode === "live";
  return (
    <div
      data-testid="reco-mode-badge"
      className="inline-flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-semibold uppercase tracking-wider"
      style={{
        background: isLive ? "rgba(140,198,62,0.18)" : "rgba(255,90,74,0.16)",
        border: `1px solid ${isLive ? "rgba(140,198,62,0.55)" : "rgba(255,90,74,0.45)"}`,
        color: isLive ? "#6FA82E" : "#E64432",
      }}
    >
      {isLive ? <Unlock size={12} /> : <Lock size={12} />}
      Mode {isLive ? "LIVE" : "TEST"}
    </div>
  );
}

function TotalCard({ title, amount, count, accent, testid }) {
  return (
    <div className="glass-panel rounded-2xl p-5" data-testid={testid}>
      <div className="text-xs uppercase tracking-wide opacity-60 mb-1">{title}</div>
      <div className="font-display text-3xl font-bold" style={{ color: accent }}>
        {formatEur(amount)}
      </div>
      <div className="text-xs opacity-60 mt-1">{count} transaction{count > 1 ? "s" : ""}</div>
    </div>
  );
}

function AccountTotalCard({ account, data, link, testid }) {
  return (
    <div
      className="glass-panel rounded-2xl p-5 relative overflow-hidden"
      data-testid={testid}
      style={{ borderColor: ACCOUNT_COLOR[account] + "55" }}
    >
      <div
        className="absolute top-0 left-0 right-0 h-1"
        style={{ background: ACCOUNT_COLOR[account] }}
      />
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide opacity-60 mb-1">{ACCOUNT_LABEL[account]}</div>
          <div className="font-display text-3xl font-bold" style={{ color: ACCOUNT_COLOR[account] }}>
            {formatEur(data?.amount_cents)}
          </div>
          <div className="text-xs opacity-60 mt-1">{data?.count || 0} transaction{(data?.count || 0) > 1 ? "s" : ""}</div>
        </div>
        {link && (
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-60 hover:opacity-100 transition-opacity"
            title={`Ouvrir dashboard Stripe ${ACCOUNT_LABEL[account]}`}
            data-testid={`reco-stripe-link-${account}`}
          >
            <ExternalLink size={16} />
          </a>
        )}
      </div>
    </div>
  );
}

function ByKindCard({ account, byKind, testid }) {
  return (
    <div className="glass-panel rounded-2xl p-5" data-testid={testid}>
      <h3 className="font-display text-lg mb-4" style={{ color: ACCOUNT_COLOR[account] }}>
        {ACCOUNT_LABEL[account]} — Détail par produit
      </h3>
      <div className="space-y-3">
        {Object.entries(KIND_LABEL).map(([kind, label]) => {
          const entry = byKind[kind] || { amount_cents: 0, count: 0 };
          return (
            <div
              key={kind}
              className="flex items-center justify-between py-2 border-b"
              style={{ borderColor: "rgba(212,175,55,0.18)" }}
            >
              <div>
                <div className="text-sm font-medium">{label}</div>
                <div className="text-xs opacity-50">{entry.count} paiement{entry.count > 1 ? "s" : ""}</div>
              </div>
              <div className="text-lg font-semibold tabular-nums" style={{ color: "var(--kdm-anthracite)" }}>
                {formatEur(entry.amount_cents)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
