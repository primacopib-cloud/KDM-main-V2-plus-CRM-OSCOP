import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { FileText, ChevronDown, ChevronUp, Loader2, FolderArchive } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const PAY = { CARD: '💳 CB', UC: "🪙 UC", MIXED: '🪙+💳 Mixte', CASH: '💵 Espèces' };
const today = () => new Date().toISOString().slice(0, 10);

// Historique des ventes (jour courant ou date passée) avec téléchargement du ticket PDF
export const SalesTicketsList = ({ sales: todaySales }) => {
  const [open, setOpen] = useState(false);
  const [pdfId, setPdfId] = useState(null);
  const [date, setDate] = useState(today());
  const [sales, setSales] = useState(todaySales || []);
  const [loading, setLoading] = useState(false);
  const [zipping, setZipping] = useState(false);

  const downloadZip = async () => {
    const month = date.slice(0, 7);
    setZipping(true);
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/pos/counter-journal/tickets.zip?month=${month}`,
        { credentials: 'include' });
      if (!r.ok) { toast.error((await r.json()).detail || 'Archive indisponible'); return; }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tickets-${month}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Tickets du mois ${month} archivés en ZIP ✓`);
    } catch { toast.error('Erreur de connexion'); } finally { setZipping(false); }
  };

  useEffect(() => {
    if (date === today()) { setSales(todaySales || []); return; }
    setLoading(true);
    lolodriveAPI.posCounterJournal(date)
      .then((d) => setSales(d.sales || []))
      .catch(() => setSales([]))
      .finally(() => setLoading(false));
  }, [date, todaySales]);

  if ((!todaySales || todaySales.length === 0) && date === today() && !open) {
    return (
      <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-2.5" data-testid="sales-tickets-list">
        <button type="button" onClick={() => setOpen(true)} data-testid="sales-tickets-toggle"
          className="w-full flex items-center justify-between gap-2 text-xs">
          <span className="font-bold text-white/60 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-[#D9B35A]" /> Tickets PDF — historique des ventes
          </span>
          <ChevronDown className="w-4 h-4 text-white/40" />
        </button>
      </div>
    );
  }

  const downloadPdf = async (s) => {
    setPdfId(s.id);
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/pos/counter-sale/${s.id}/ticket.pdf`,
        { credentials: 'include' });
      if (!r.ok) { toast.error('Ticket PDF indisponible'); return; }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ticket-${s.order_number}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Ticket ${s.order_number} archivé en PDF ✓`);
    } catch { toast.error('Erreur de connexion'); } finally { setPdfId(null); }
  };

  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-2.5" data-testid="sales-tickets-list">
      <button type="button" onClick={() => setOpen(!open)} data-testid="sales-tickets-toggle"
        className="w-full flex items-center justify-between gap-2 text-xs">
        <span className="font-bold text-white/60 flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-[#D9B35A]" /> Tickets PDF — {date === today() ? 'ventes du jour' : `ventes du ${new Date(date).toLocaleDateString('fr-FR')}`} ({sales.length})
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
      </button>
      {open && (
        <div className="mt-2 space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-white/45">Journée :</span>
            <input type="date" value={date} max={today()} onChange={(e) => e.target.value && setDate(e.target.value)}
              data-testid="sales-date-input"
              className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-xs text-white" />
            {loading && <Loader2 className="w-3.5 h-3.5 animate-spin text-white/40" />}
            {!loading && sales.length === 0 && <span className="text-white/40" data-testid="sales-empty">Aucune vente ce jour-là.</span>}
            <button type="button" onClick={downloadZip} disabled={zipping} data-testid="tickets-zip-btn"
              title="Télécharger tous les tickets PDF du mois en une archive ZIP"
              className="ml-auto flex items-center gap-1 px-2 py-1 rounded-lg font-bold text-cyan-300 bg-cyan-500/10 border border-cyan-500/30 hover:bg-cyan-500/20 disabled:opacity-50">
              {zipping ? <Loader2 className="w-3 h-3 animate-spin" /> : <FolderArchive className="w-3 h-3" />} ZIP du mois
            </button>
          </div>
          <div className="space-y-1 max-h-56 overflow-y-auto pr-1">
          {sales.map((s) => (
            <div key={s.id || s.order_number} data-testid={`sale-row-${s.order_number}`}
              className="flex items-center gap-2 text-xs rounded-lg bg-white/[0.03] border border-white/[0.05] px-2.5 py-1.5">
              <span className="font-mono text-white/45 shrink-0">{new Date(s.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>
              <span className="font-mono truncate">{s.order_number}</span>
              <span className="text-white/45 truncate hidden sm:block">{s.customer_name || ''}</span>
              <span className="ml-auto shrink-0 text-white/55">{PAY[s.payment_method] || PAY.CASH}</span>
              <span className="font-mono font-bold shrink-0">{(s.total_cents / 100).toFixed(2)} € <span className="text-[#D9B35A] font-normal">· {+(s.total_cents / 10).toFixed(1)} UC</span></span>
              <button type="button" onClick={() => downloadPdf(s)} disabled={pdfId === s.id}
                data-testid={`ticket-pdf-${s.order_number}`} title="Télécharger le ticket PDF"
                className="shrink-0 flex items-center gap-1 px-2 py-1 rounded-lg font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/35 hover:bg-[#D9B35A]/25 disabled:opacity-50">
                {pdfId === s.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />} PDF
              </button>
            </div>
          ))}
          </div>
        </div>
      )}
    </div>
  );
};
