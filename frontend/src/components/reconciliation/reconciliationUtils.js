export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const ACCOUNT_LABEL = {
  oscop: "O'SCOP OUTREMER",
  kdmarche: "KDMARCHE",
};
export const ACCOUNT_COLOR = {
  oscop: "#5B2E8C",      // Bleu logistique
  kdmarche: "#D4AF37",   // Or métallisé
};
export const KIND_LABEL = {
  PASS: "PASS Vie Chère (60 €)",
  RECHARGE: "Recharges UC",
  ORDER: "Commandes DRIVE",
};
export const STATUS_FILTERS = [
  { value: "all", label: "Tous les paiements" },
  { value: "paid", label: "Payés (non remboursés)" },
  { value: "refunded_full", label: "Remboursés intégralement" },
  { value: "refunded_partial", label: "Remboursés partiellement" },
];
export const PAGE_SIZE = 25;

export function formatEur(cents) {
  return new Intl.NumberFormat(i18n.language, { style: "currency", currency: "EUR" }).format((cents || 0) / 100);
}

export function isoToday() {
  return new Date().toISOString().slice(0, 10);
}

export function isoNDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

export function fmtDateTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(i18n.language, {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch (_e) {
    return iso;
  }
}
