import {
  Loader2, Download, RefreshCw, ExternalLink, ArrowLeft, AlertTriangle, Lock, Unlock,
  RotateCcw, ChevronLeft, ChevronRight,
} from "lucide-react";
import { ACCOUNT_LABEL, ACCOUNT_COLOR, KIND_LABEL, formatEur } from "./reconciliationUtils";

export function ModeBadge({ mode }) {
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

export function TotalCard({ title, amount, count, accent, testid, negative }) {
  return (
    <div className="glass-panel rounded-2xl p-5" data-testid={testid}>
      <div className="text-xs uppercase tracking-wide opacity-60 mb-1">{title}</div>
      <div className="font-display text-3xl font-bold tabular-nums" style={{ color: accent }}>
        {negative && amount > 0 ? "− " : ""}{formatEur(amount)}
      </div>
      {count !== null && count !== undefined && (
        <div className="text-xs opacity-60 mt-1">{count} transaction{count > 1 ? "s" : ""}</div>
      )}
    </div>
  );
}

export function AccountTotalCard({ account, data, link, testid }) {
  const refundFull = data?.refund_full_cents || 0;
  const refundPartial = data?.refund_partial_cents || 0;
  const refundTotal = refundFull + refundPartial;
  const refundFullCount = data?.refund_full_count || 0;
  const refundPartialCount = data?.refund_partial_count || 0;
  const net = data?.net_cents ?? ((data?.amount_cents || 0) - refundTotal);
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
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="text-xs uppercase tracking-wide opacity-60 mb-1">{ACCOUNT_LABEL[account]}</div>
          <div className="font-display text-3xl font-bold tabular-nums" style={{ color: ACCOUNT_COLOR[account] }}>
            {formatEur(data?.amount_cents)}
          </div>
          <div className="text-xs opacity-60 mt-1">{data?.count || 0} transaction{(data?.count || 0) > 1 ? "s" : ""} encaissées</div>
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

      {/* Refund + net section */}
      <div className="grid grid-cols-3 gap-2 pt-3 border-t" style={{ borderColor: "rgba(212,175,55,0.18)" }}>
        <RefundStat
          label="Remboursé total"
          amount={refundTotal}
          count={refundFullCount + refundPartialCount}
          color="#E64432"
          icon={<RotateCcw size={11} />}
          testid={`reco-${account}-refund-total`}
        />
        <RefundStat
          label="Partiels"
          amount={refundPartial}
          count={refundPartialCount}
          color="#D97706"
          testid={`reco-${account}-refund-partial`}
        />
        <div data-testid={`reco-${account}-net`}>
          <div className="text-[10px] uppercase tracking-wider opacity-60">Net</div>
          <div className="font-semibold tabular-nums" style={{ color: ACCOUNT_COLOR[account] }}>
            {formatEur(net)}
          </div>
        </div>
      </div>
    </div>
  );
}

export function RefundStat({ label, amount, count, color, icon, testid }) {
  return (
    <div data-testid={testid}>
      <div className="text-[10px] uppercase tracking-wider opacity-60 inline-flex items-center gap-1">
        {icon}{label}
      </div>
      <div className="font-semibold tabular-nums" style={{ color }}>
        {amount > 0 ? `− ${formatEur(amount)}` : formatEur(0)}
      </div>
      {count > 0 && (
        <div className="text-[10px] opacity-50">{count} op.</div>
      )}
    </div>
  );
}

export function RefundBadge({ status }) {
  if (!status) {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium"
        style={{ background: "rgba(140,198,62,0.18)", color: "#6FA82E" }}>
        Encaissé
      </span>
    );
  }
  if (status === "full") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium"
        style={{ background: "rgba(230,68,50,0.14)", color: "#E64432" }}>
        Remboursé
      </span>
    );
  }
  if (status === "partial") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium"
        style={{ background: "rgba(217,119,6,0.14)", color: "#D97706" }}>
        Partiel
      </span>
    );
  }
  return null;
}

export function ByKindCard({ account, byKind, testid }) {
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
