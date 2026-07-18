/**
 * Page admin minimaliste — Pont GED ESS externe.
 *
 * Affiche :
 *   • Statut du pont (OK / DEGRADED / DISABLED) avec diagnostic config
 *   • Compteurs agrégés (total / succès / erreurs)
 *   • Journal des sync-events (filtre statut + source)
 *   • Bouton "Re-pousser" sur chaque événement en ERROR
 *
 * Volontairement compacte : aucun refactor lourd, design aligné sur la charte
 * premium light (glass-panel, or métallisé, bleu logistique).
 */
import { getSessionToken } from '../services/http';
import i18n from '@/i18n';
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft, RefreshCw, Loader2, AlertTriangle, CheckCircle2,
  XCircle, RotateCcw, Server, Lock, Unlock, AlertCircle,
} from "lucide-react";
import NavBar from "../components/NavBar";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_FILTERS = [
  { value: "", label: "Tous les statuts" },
  { value: "SUCCESS", label: "Succès" },
  { value: "ERROR", label: "Erreurs" },
];

function fmtDateTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(i18n.language, {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch (_e) {
    return iso;
  }
}

export default function GedBridgeAdminPage() {
  const navigate = useNavigate();
  const [health, setHealth] = useState(null);
  const [events, setEvents] = useState([]);
  const [counts, setCounts] = useState({ total: 0, success: 0, error: 0 });
  const [statusFilter, setStatusFilter] = useState("ERROR");
  const [sourceFilter, setSourceFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryingId, setRetryingId] = useState(null);

  const authHeader = () => {
    const token = getSessionToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const fetchHealth = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/ged-bridge/health`, { headers: authHeader() });
      if (resp.status === 403) {
        setError("Accès réservé aux administrateurs.");
        return;
      }
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setHealth(await resp.json());
    } catch (e) {
      setError(e.message || "Erreur santé");
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (statusFilter) params.set("status", statusFilter);
      if (sourceFilter) params.set("source", sourceFilter);
      const resp = await fetch(`${API}/ged-bridge/sync-events?${params}`, { headers: authHeader() });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const j = await resp.json();
      setEvents(j.events || []);
      setCounts(j.counts || { total: 0, success: 0, error: 0 });
    } catch (e) {
      toast.error(e.message || "Erreur sync-events");
    }
  }, [statusFilter, sourceFilter]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    await Promise.all([fetchHealth(), fetchEvents()]);
    setLoading(false);
  }, [fetchHealth, fetchEvents]);

  useEffect(() => { refresh(); }, [refresh]);

  const handleRetry = async (eventId) => {
    setRetryingId(eventId);
    try {
      const resp = await fetch(`${API}/ged-bridge/sync-events/${eventId}/retry`, {
        method: "POST",
        headers: authHeader(),
      });
      const j = await resp.json().catch(() => ({}));
      if (resp.ok) {
        toast.success("Re-push réussi");
      } else {
        toast.error(j.detail || `Re-push échoué (HTTP ${resp.status})`);
      }
      // Re-fetch events to show the new RETRY entry
      await fetchEvents();
    } catch (e) {
      toast.error(e.message || "Erreur retry");
    } finally {
      setRetryingId(null);
    }
  };

  const sources = useMemo(() => {
    const set = new Set(events.map((e) => e.source).filter(Boolean));
    return Array.from(set).sort();
  }, [events]);

  return (
    <div className="min-h-screen" data-testid="ged-bridge-admin-page">
      <NavBar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <button
              type="button"
              onClick={() => navigate("/admin")}
              data-testid="ged-back-btn"
              className="inline-flex items-center gap-2 text-sm mb-3 opacity-70 hover:opacity-100 transition-opacity"
            >
              <ArrowLeft size={14} /> Admin
            </button>
            <h1 className="font-display text-3xl sm:text-4xl" style={{ color: "#F7F2E9" }}>
              Pont GED ESS
            </h1>
            <p className="text-sm opacity-70 mt-2">
              Synchronisation vers le microservice GED ESS externe (PostgreSQL + S3/R2 + audit probant)
            </p>
          </div>
          <button
            type="button"
            onClick={refresh}
            data-testid="ged-refresh-btn"
            className="btn-ghost h-10 px-4 rounded-lg inline-flex items-center gap-2"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Actualiser
          </button>
        </div>

        {error && (
          <div className="glass-panel rounded-2xl p-6 text-center mb-6" data-testid="ged-error">
            <AlertTriangle className="mx-auto mb-3 text-orange-500" size={28} />
            <p className="font-medium">{error}</p>
          </div>
        )}

        {/* Health card */}
        {health && <HealthCard health={health} />}

        {/* Counts */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <StatCard label="Total tentatives" value={counts.total} accent="var(--kdm-or-metallise)" testid="ged-count-total" />
          <StatCard label="Succès" value={counts.success} accent="#6FA82E" icon={<CheckCircle2 size={18} />} testid="ged-count-success" />
          <StatCard label="Erreurs" value={counts.error} accent="#E64432" icon={<XCircle size={18} />} testid="ged-count-error" />
        </div>

        {/* Filters */}
        <div className="glass-panel rounded-2xl p-4 mb-4">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-xs uppercase tracking-wide opacity-60 mb-1.5">Statut</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                data-testid="ged-status-filter"
                className="px-3 py-2 rounded-lg bg-white border text-sm"
                style={{ borderColor: "rgba(212,175,55,0.30)" }}
              >
                {STATUS_FILTERS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wide opacity-60 mb-1.5">Source</label>
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                data-testid="ged-source-filter"
                className="px-3 py-2 rounded-lg bg-white border text-sm"
                style={{ borderColor: "rgba(212,175,55,0.30)" }}
              >
                <option value="">Toutes les sources</option>
                {sources.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Events table */}
        <div className="glass-panel rounded-2xl p-5" data-testid="ged-events-table">
          {loading && (
            <div className="text-center py-8">
              <Loader2 className="animate-spin inline" size={20} style={{ color: "var(--kdm-or-metallise)" }} />
            </div>
          )}
          {!loading && events.length === 0 && (
            <div className="text-center py-10 opacity-60 text-sm">
              Aucun événement de synchronisation.
            </div>
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
                    <th className="text-left py-2 pr-3 font-medium opacity-70">Détail</th>
                    <th className="text-right py-2 font-medium opacity-70">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev) => (
                    <tr
                      key={ev.id}
                      className="border-b transition-colors hover:bg-amber-50/40"
                      style={{ borderColor: "rgba(212,175,55,0.12)" }}
                      data-testid={`ged-event-row-${ev.id}`}
                    >
                      <td className="py-2 pr-3 tabular-nums whitespace-nowrap">{fmtDateTime(ev.created_at)}</td>
                      <td className="py-2 pr-3"><span className="font-mono text-xs">{ev.source}</span></td>
                      <td className="py-2 pr-3 max-w-[220px] truncate font-mono text-xs" title={ev.source_id}>{ev.source_id || "—"}</td>
                      <td className="py-2 pr-3 text-xs">{ev.direction}</td>
                      <td className="py-2 pr-3"><StatusBadge status={ev.status} /></td>
                      <td className="py-2 pr-3 max-w-[300px] truncate text-xs opacity-70" title={ev.response?.error || ev.response?.id || ""}>
                        {ev.response?.error || (ev.response?.id ? `GED id: ${ev.response.id}` : "—")}
                      </td>
                      <td className="py-2 text-right">
                        {ev.status === "ERROR" && (
                          <button
                            type="button"
                            onClick={() => handleRetry(ev.id)}
                            disabled={retryingId === ev.id}
                            data-testid={`ged-retry-${ev.id}`}
                            className="btn-ghost h-8 px-3 rounded-lg inline-flex items-center gap-1 text-xs disabled:opacity-50"
                          >
                            {retryingId === ev.id
                              ? <Loader2 size={12} className="animate-spin" />
                              : <RotateCcw size={12} />}
                            Re-pousser
                          </button>
                        )}
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
  const config = {
    OK:       { color: "#6FA82E", bg: "rgba(140,198,62,0.16)", border: "rgba(140,198,62,0.55)", icon: <Unlock size={14} />, label: "Opérationnel" },
    DEGRADED: { color: "#D97706", bg: "rgba(217,119,6,0.14)",  border: "rgba(217,119,6,0.45)",  icon: <AlertCircle size={14} />, label: "Dégradé (microservice GED injoignable)" },
    DISABLED: { color: "#94a3b8", bg: "rgba(148,163,184,0.16)", border: "rgba(148,163,184,0.45)", icon: <Lock size={14} />, label: "Désactivé (URL non configurée)" },
  }[status] || { color: "#E64432", bg: "rgba(230,68,50,0.14)", border: "rgba(230,68,50,0.45)", icon: <XCircle size={14} />, label: "Inconnu" };

  return (
    <div className="glass-panel rounded-2xl p-5 mb-4" data-testid="ged-health-card">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center"
            style={{ background: config.bg, border: `1px solid ${config.border}`, color: config.color }}
          >
            <Server size={20} />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide opacity-60">Statut du pont</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider"
                style={{ background: config.bg, border: `1px solid ${config.border}`, color: config.color }}
                data-testid="ged-health-status"
              >
                {config.icon} {status}
              </span>
              <span className="text-sm opacity-80">{config.label}</span>
            </div>
            {(health.message || health.error) && (
              <p className="text-xs opacity-60 mt-2 max-w-2xl">
                {health.message || health.error}
              </p>
            )}
          </div>
        </div>
        {health.config && (
          <div className="text-xs space-y-1 opacity-80">
            <div className="flex gap-2"><span className="opacity-60 w-32">URL</span><span className="font-mono">{health.config.url_configured ? (health.config.url || "✔") : "—"}</span></div>
            <div className="flex gap-2"><span className="opacity-60 w-32">Bearer token</span><span>{health.config.token_configured ? "✔ configuré" : "— absent"}</span></div>
            <div className="flex gap-2"><span className="opacity-60 w-32">HMAC secret</span><span>{health.config.webhook_secret_configured ? "✔ configuré" : "— absent"}</span></div>
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
    SUCCESS: { bg: "rgba(140,198,62,0.18)", color: "#6FA82E", label: "Succès" },
    ERROR:   { bg: "rgba(230,68,50,0.14)",  color: "#E64432", label: "Erreur" },
  };
  const c = map[status] || { bg: "rgba(148,163,184,0.16)", color: "#64748b", label: status };
  return (
    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium" style={{ background: c.bg, color: c.color }}>
      {c.label}
    </span>
  );
}
