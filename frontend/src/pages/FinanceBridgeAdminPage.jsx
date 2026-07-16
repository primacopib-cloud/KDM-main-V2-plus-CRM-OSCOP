/**
 * Admin page — Bridge to the external finance-api microservice.
 *
 * Same minimalistic pattern as `GedBridgeAdminPage.jsx`:
 *   • Carte santé (OK / DEGRADED / DISABLED) + diagnostic config
 *   • 3 compteurs (Total / Succès / Erreurs)
 *   • Filtres source + statut
 *   • Tableau des sync-events
 *   • 2 actions rapides : pousser un client KDM / pousser une commande LOLODRIVE
 */
import i18n from '@/i18n';
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft, RefreshCw, Loader2, AlertTriangle, CheckCircle2, XCircle,
  Server, Lock, Unlock, AlertCircle, Send, FileText, Users,
} from "lucide-react";
import NavBar from "../components/NavBar";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_FILTERS = [
  { value: "", label: "Tous les statuts" },
  { value: "SUCCESS", label: "Succès" },
  { value: "SUCCESS_IDEMPOTENT", label: "Idempotent" },
  { value: "ERROR", label: "Erreurs" },
];

function fmtDateTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(i18n.language, {
      day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch (_e) {
    return iso;
  }
}

const authHeader = () => {
  const t = localStorage.getItem("token");
  return t ? { Authorization: `Bearer ${t}` } : {};
};

export default function FinanceBridgeAdminPage() {
  const navigate = useNavigate();
  const [health, setHealth] = useState(null);
  const [events, setEvents] = useState([]);
  const [counts, setCounts] = useState({ total: 0, success: 0, error: 0 });
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pushBusy, setPushBusy] = useState(false);
  const [customerId, setCustomerId] = useState("user-buyer-pro");
  const [orderId, setOrderId] = useState("order-lp-gerant-1");

  const fetchHealth = useCallback(async () => {
    try {
      const r = await fetch(`${API}/finance-bridge/health`, { headers: authHeader() });
      if (r.status === 403) { setError("Accès réservé aux administrateurs."); return; }
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setHealth(await r.json());
    } catch (e) { setError(e.message); }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (statusFilter) params.set("status", statusFilter);
      if (sourceFilter) params.set("source", sourceFilter);
      const r = await fetch(`${API}/finance-bridge/sync-events?${params}`, { headers: authHeader() });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      setEvents(j.events || []);
      setCounts(j.counts || { total: 0, success: 0, error: 0 });
    } catch (e) { toast.error(e.message); }
  }, [statusFilter, sourceFilter]);

  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    await Promise.all([fetchHealth(), fetchEvents()]);
    setLoading(false);
  }, [fetchHealth, fetchEvents]);

  useEffect(() => { refresh(); }, [refresh]);

  const pushCustomer = useCallback(async () => {
    const cid = customerId.trim();
    if (!cid) return;
    try {
      setPushBusy(true);
      const r = await fetch(`${API}/finance-bridge/parties/from-customer/${encodeURIComponent(cid)}`, {
        method: "POST", headers: authHeader(),
      });
      const j = await r.json();
      if (r.ok) toast.success(`Party créé/réutilisé (${j.sync_event?.status || "OK"})`);
      else toast.error(j.detail || `HTTP ${r.status}`);
      await fetchEvents();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setPushBusy(false);
    }
  }, [customerId, fetchEvents]);

  const pushOrder = useCallback(async () => {
    const oid = orderId.trim();
    if (!oid) return;
    try {
      setPushBusy(true);
      const r = await fetch(`${API}/finance-bridge/receivables/from-order/${encodeURIComponent(oid)}`, {
        method: "POST", headers: authHeader(),
      });
      const j = await r.json();
      if (r.ok) toast.success(`Créance ${j.receivable?.reference || ""} créée`);
      else toast.error(j.detail || `HTTP ${r.status}`);
      await fetchEvents();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setPushBusy(false);
    }
  }, [orderId, fetchEvents]);

  return (
    <div className="min-h-screen" data-testid="finance-bridge-admin-page">
      <NavBar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <button type="button" onClick={() => navigate("/admin")}
              data-testid="fin-back-btn"
              className="inline-flex items-center gap-2 text-sm mb-3 opacity-70 hover:opacity-100">
              <ArrowLeft size={14} /> Admin
            </button>
            <h1 className="font-display text-3xl sm:text-4xl" style={{ color: "var(--kdm-bleu-logistique)" }}>
              Pont Finance API
            </h1>
            <p className="text-sm opacity-70 mt-2">
              Synchronisation vers le microservice finance-api (PostgreSQL + journal probant).
              Le KDM appelle ce service, jamais l&apos;inverse.
            </p>
          </div>
          <button type="button" onClick={refresh}
            data-testid="fin-refresh-btn"
            className="btn-ghost h-10 px-4 rounded-lg inline-flex items-center gap-2">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Actualiser
          </button>
        </div>

        {error && (
          <div className="glass-panel rounded-2xl p-6 text-center mb-6" data-testid="fin-error">
            <AlertTriangle className="mx-auto mb-3 text-orange-500" size={28} />
            <p className="font-medium">{error}</p>
          </div>
        )}

        {health && <HealthCard health={health} />}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <StatCard label="Total tentatives" value={counts.total} accent="var(--kdm-or-metallise)" testid="fin-count-total" />
          <StatCard label="Succès" value={counts.success} accent="#6FA82E" icon={<CheckCircle2 size={18} />} testid="fin-count-success" />
          <StatCard label="Erreurs" value={counts.error} accent="#E64432" icon={<XCircle size={18} />} testid="fin-count-error" />
        </div>

        {/* Quick actions */}
        <div className="glass-panel rounded-2xl p-5 mb-6">
          <h2 className="font-display text-lg mb-4" style={{ color: "var(--kdm-bleu-logistique)" }}>Actions rapides</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl p-4 border" style={{ borderColor: "rgba(212,175,55,0.30)" }}>
              <div className="text-xs uppercase tracking-wide opacity-60 mb-1 inline-flex items-center gap-1.5">
                <Users size={14} /> Pousser un client → Finance
              </div>
              <p className="text-xs opacity-60 mb-3">Crée (ou réutilise) un <code>Party</code> dans finance-api à partir d&apos;un user KDM.</p>
              <div className="flex gap-2">
                <input value={customerId} onChange={(e) => setCustomerId(e.target.value)}
                  placeholder="user-buyer-pro" data-testid="fin-customer-id-input"
                  className="flex-1 px-3 py-2 rounded-lg bg-white border text-sm font-mono"
                  style={{ borderColor: "rgba(212,175,55,0.30)" }} />
                <button type="button" onClick={pushCustomer} disabled={pushBusy}
                  data-testid="fin-push-customer-btn"
                  className="btn-gold h-9 px-3 rounded-lg inline-flex items-center gap-1 text-xs disabled:opacity-50">
                  {pushBusy ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />} Pousser
                </button>
              </div>
            </div>

            <div className="rounded-xl p-4 border" style={{ borderColor: "rgba(212,175,55,0.30)" }}>
              <div className="text-xs uppercase tracking-wide opacity-60 mb-1 inline-flex items-center gap-1.5">
                <FileText size={14} /> Pousser une commande → Receivable
              </div>
              <p className="text-xs opacity-60 mb-3">Crée une <code>Receivable</code> dans finance-api à partir d&apos;une commande LOLODRIVE.</p>
              <div className="flex gap-2">
                <input value={orderId} onChange={(e) => setOrderId(e.target.value)}
                  placeholder="order-lp-gerant-1" data-testid="fin-order-id-input"
                  className="flex-1 px-3 py-2 rounded-lg bg-white border text-sm font-mono"
                  style={{ borderColor: "rgba(212,175,55,0.30)" }} />
                <button type="button" onClick={pushOrder} disabled={pushBusy}
                  data-testid="fin-push-order-btn"
                  className="btn-gold h-9 px-3 rounded-lg inline-flex items-center gap-1 text-xs disabled:opacity-50">
                  {pushBusy ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />} Pousser
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="glass-panel rounded-2xl p-4 mb-4">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-xs uppercase tracking-wide opacity-60 mb-1.5">Statut</label>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                data-testid="fin-status-filter"
                className="px-3 py-2 rounded-lg bg-white border text-sm"
                style={{ borderColor: "rgba(212,175,55,0.30)" }}>
                {STATUS_FILTERS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wide opacity-60 mb-1.5">Source</label>
              <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}
                data-testid="fin-source-filter"
                className="px-3 py-2 rounded-lg bg-white border text-sm"
                style={{ borderColor: "rgba(212,175,55,0.30)" }}>
                <option value="">Toutes les sources</option>
                <option value="kdm_customer">kdm_customer</option>
                <option value="kdm_lolodrive_order">kdm_lolodrive_order</option>
                <option value="kdm_payment_request">kdm_payment_request</option>
                <option value="kdm_installment_plan">kdm_installment_plan</option>
                <option value="kdm_sepa_mandate">kdm_sepa_mandate</option>
              </select>
            </div>
          </div>
        </div>

        {/* Events table */}
        <div className="glass-panel rounded-2xl p-5" data-testid="fin-events-table">
          {loading && <div className="text-center py-8"><Loader2 className="animate-spin inline" size={20} /></div>}
          {!loading && events.length === 0 && (
            <div className="text-center py-10 opacity-60 text-sm">Aucun événement de synchronisation.</div>
          )}
          {!loading && events.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b" style={{ borderColor: "rgba(212,175,55,0.25)" }}>
                    <th className="text-left py-2 pr-3 font-medium opacity-70">Date</th>
                    <th className="text-left py-2 pr-3 font-medium opacity-70">Source</th>
                    <th className="text-left py-2 pr-3 font-medium opacity-70">ID métier</th>
                    <th className="text-left py-2 pr-3 font-medium opacity-70">Direction</th>
                    <th className="text-left py-2 pr-3 font-medium opacity-70">Statut</th>
                    <th className="text-left py-2 font-medium opacity-70">Détail</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev) => (
                    <tr key={ev.id}
                      className="border-b hover:bg-amber-50/40"
                      style={{ borderColor: "rgba(212,175,55,0.12)" }}
                      data-testid={`fin-event-row-${ev.id}`}>
                      <td className="py-2 pr-3 tabular-nums whitespace-nowrap">{fmtDateTime(ev.created_at)}</td>
                      <td className="py-2 pr-3 font-mono text-xs">{ev.source}</td>
                      <td className="py-2 pr-3 max-w-[220px] truncate font-mono text-xs" title={ev.source_id}>
                        {ev.source_id || "—"}
                      </td>
                      <td className="py-2 pr-3 text-xs">{ev.direction}</td>
                      <td className="py-2 pr-3"><StatusBadge status={ev.status} /></td>
                      <td className="py-2 max-w-[300px] truncate text-xs opacity-70"
                        title={ev.response?.error || ev.response?.id || ev.response?.reference || ""}>
                        {ev.response?.error || ev.response?.reference || (ev.response?.id ? `id: ${ev.response.id}` : "—")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function HealthCard({ health }) {
  const status = health.status || "UNKNOWN";
  const c = {
    OK:       { color: "#6FA82E", bg: "rgba(140,198,62,0.16)", border: "rgba(140,198,62,0.55)", icon: <Unlock size={14} />, label: "Opérationnel" },
    DEGRADED: { color: "#D97706", bg: "rgba(217,119,6,0.14)",  border: "rgba(217,119,6,0.45)",  icon: <AlertCircle size={14} />, label: "Dégradé (microservice finance-api injoignable)" },
    DISABLED: { color: "#94a3b8", bg: "rgba(148,163,184,0.16)", border: "rgba(148,163,184,0.45)", icon: <Lock size={14} />, label: "Désactivé (URL non configurée)" },
  }[status] || { color: "#E64432", bg: "rgba(230,68,50,0.14)", border: "rgba(230,68,50,0.45)", icon: <XCircle size={14} />, label: "Inconnu" };

  const ext = health.external_finance || {};
  return (
    <div className="glass-panel rounded-2xl p-5 mb-4" data-testid="fin-health-card">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
            style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.color }}>
            <Server size={20} />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide opacity-60">Statut du pont</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider"
                style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.color }}
                data-testid="fin-health-status">
                {c.icon} {status}
              </span>
              <span className="text-sm opacity-80">{c.label}</span>
            </div>
            {(health.message || health.error) && (
              <p className="text-xs opacity-60 mt-2 max-w-2xl">{health.message || health.error}</p>
            )}
            {ext.version && (
              <p className="text-xs opacity-60 mt-2">
                finance-api v{ext.version} · base {ext.database} · bootstrap {ext.bootstrap_done ? "✔" : "—"}
                {ext.config && (
                  <> · Stripe {ext.config.stripe_configured ? "✔" : "—"} · GoCardless {ext.config.gocardless_configured ? "✔" : "—"}</>
                )}
              </p>
            )}
          </div>
        </div>
        {health.config && (
          <div className="text-xs space-y-1 opacity-80">
            <div className="flex gap-2"><span className="opacity-60 w-32">URL</span><span className="font-mono">{health.config.url || "—"}</span></div>
            <div className="flex gap-2"><span className="opacity-60 w-32">Credentials</span><span>{health.config.credentials_configured ? "✔ configurés" : "— absents"}</span></div>
            <div className="flex gap-2"><span className="opacity-60 w-32">Timeout</span><span>{health.config.timeout_seconds}s</span></div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, accent, icon, testid }) {
  return (
    <div className="glass-panel rounded-2xl p-5" data-testid={testid}>
      <div className="text-xs uppercase tracking-wide opacity-60 mb-1 inline-flex items-center gap-1.5" style={{ color: accent }}>
        {icon}{label}
      </div>
      <div className="font-display text-3xl font-bold tabular-nums" style={{ color: accent }}>{value}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    SUCCESS:            { bg: "rgba(140,198,62,0.18)", color: "#6FA82E", label: "Succès" },
    SUCCESS_IDEMPOTENT: { bg: "rgba(31,77,135,0.14)",  color: "#1F4D87", label: "Idempotent" },
    ERROR:              { bg: "rgba(230,68,50,0.14)",  color: "#E64432", label: "Erreur" },
  };
  const c = map[status] || { bg: "rgba(148,163,184,0.16)", color: "#64748b", label: status };
  return (
    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium" style={{ background: c.bg, color: c.color }}>
      {c.label}
    </span>
  );
}
