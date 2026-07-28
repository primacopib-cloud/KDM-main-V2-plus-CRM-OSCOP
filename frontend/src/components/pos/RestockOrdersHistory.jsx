import { useState } from 'react';
import { toast } from 'sonner';
import { PackageCheck, ChevronDown, ChevronUp, Loader2, PackagePlus, FileText } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const fmtDate = (iso) => new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' });
const daysSince = (iso) => Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);

// Historique des bons de commande fournisseur + pointage de réception (gérant)
export const RestockOrdersHistory = () => {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [qtys, setQtys] = useState({});
  const [busy, setBusy] = useState(false);

  const load = () => lolodriveAPI.posRestockOrders().then(setData).catch(() => setData({ orders: [] }));
  const toggle = () => { if (!open && data === null) load(); setOpen(!open); };

  const expand = (o) => {
    setExpanded(expanded === o.id ? null : o.id);
    setQtys(Object.fromEntries(o.lines.map((l) => [l.sku, String(l.qty)])));
  };

  const receive = async (o) => {
    const items = o.lines.map((l) => ({ sku: l.sku, qty: parseInt(qtys[l.sku], 10) || 0 }));
    if (!items.some((it) => it.qty > 0)) return toast.error('Aucune quantité reçue');
    setBusy(true);
    try {
      const r = await lolodriveAPI.posReceiveRestockOrder(o.id, items);
      toast.success(`Réception ${r.order_number} pointée — ${r.received.length} stock(s) mis à jour ✓`);
      if (r.shortages?.length) {
        toast.warning(`Écart de livraison : ${r.shortages.reduce((a, s) => a + s.missing, 0)} manquant(s) — ${r.suppliers_notified?.length ? `fournisseur prévenu par email (${r.suppliers_notified.join(', ')})` : 'pas d\u2019email fournisseur, pensez à le signaler'}`);
      }
      setExpanded(null);
      load();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  const downloadPdf = async (o) => {
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/pos/restock-orders/${o.id}/pdf`,
        { credentials: 'include' });
      if (!r.ok) { toast.error('PDF indisponible'); return; }
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement('a');
      a.href = url; a.download = `bon-${o.order_number}.pdf`; a.click();
      URL.revokeObjectURL(url);
      toast.success('Bon de commande PDF téléchargé ✓');
    } catch { toast.error('Erreur de connexion'); }
  };

  const badge = (o) => {
    if (o.received_at) return <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-bold text-[10px]" data-testid={`ro-status-${o.order_number}`}>✅ reçu le {fmtDate(o.received_at)}</span>;
    const d = daysSince(o.created_at);
    if (d >= 5) return <span className="px-1.5 py-0.5 rounded bg-red-500/15 text-red-300 font-bold text-[10px]" data-testid={`ro-status-${o.order_number}`}>⚠️ en attente {d} j</span>;
    return <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 font-bold text-[10px]" data-testid={`ro-status-${o.order_number}`}>⏳ en attente</span>;
  };

  return (
    <div className="mt-3 rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-2.5" data-testid="restock-orders-history">
      <button type="button" onClick={toggle} data-testid="restock-orders-toggle"
        className="w-full flex items-center justify-between text-left text-xs font-semibold text-white/60 hover:text-white">
        <span className="flex items-center gap-1.5"><PackagePlus className="w-3.5 h-3.5 text-emerald-400" /> Bons de commande fournisseur{data ? ` (${data.orders.length})` : ''}</span>
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>
      {open && (
        <div className="mt-2 space-y-1.5 max-h-72 overflow-y-auto">
          {data === null && <p className="text-[11px] text-white/30">Chargement…</p>}
          {data?.orders.length === 0 && <p className="text-[11px] text-white/30">Aucun bon de commande envoyé.</p>}
          {data?.orders.map((o) => (
            <div key={o.id} className="rounded-lg bg-white/[0.03] border border-white/[0.06]" data-testid={`ro-row-${o.order_number}`}>
              <button type="button" onClick={() => expand(o)}
                className="w-full flex flex-wrap items-center gap-x-2.5 gap-y-1 px-2.5 py-2 text-xs text-left">
                <span className="text-white/35 font-mono">{fmtDate(o.created_at)}</span>
                <b className="font-mono">{o.order_number}</b>
                <span className="text-white/50">{o.lines.length} article(s) · {[...new Set(o.lines.map((l) => l.supplier || 'sans fournisseur'))].join(', ')}</span>
                {o.total_cents > 0 && <span className="text-emerald-300/80 font-mono">{(o.total_cents / 100).toFixed(2)} €</span>}
                <span className="ml-auto">{badge(o)}</span>
              </button>
              {expanded === o.id && (
                <div className="px-2.5 pb-2.5 space-y-1" data-testid={`ro-detail-${o.order_number}`}>
                  <button type="button" onClick={() => downloadPdf(o)} data-testid={`ro-pdf-btn-${o.order_number}`}
                    className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold text-[#22d3ee] bg-[#22d3ee]/10 border border-[#22d3ee]/35 hover:bg-[#22d3ee]/20">
                    <FileText className="w-3 h-3" /> Bon de commande PDF
                  </button>
                  {o.lines.map((l) => (
                    <div key={l.sku} className="flex items-center gap-3 text-xs p-1.5 rounded bg-white/[0.03]">
                      <span className="flex-1 truncate">{l.name}</span>
                      <span className="text-white/35 font-mono shrink-0">commandé : {l.qty}</span>
                      {!o.received_at && (
                        <input type="number" min="0" value={qtys[l.sku] ?? ''} data-testid={`ro-qty-${l.sku}`}
                          onChange={(e) => setQtys((q) => ({ ...q, [l.sku]: e.target.value }))}
                          className="w-16 px-2 py-0.5 rounded bg-white/10 border border-emerald-500/40 text-white text-xs font-mono shrink-0" />
                      )}
                      {o.received_at && <span className="text-emerald-300 font-mono shrink-0">reçu : {(o.received_items || []).find((r) => r.sku === l.sku)?.qty ?? 0}</span>}
                    </div>
                  ))}
                  {!o.received_at && (
                    <button type="button" onClick={() => receive(o)} disabled={busy} data-testid={`ro-receive-btn-${o.order_number}`}
                      className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-black bg-emerald-500 hover:bg-emerald-600 disabled:opacity-60">
                      {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <><PackageCheck className="w-3.5 h-3.5" /> Pointer la réception (+ mise à jour des stocks)</>}
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
