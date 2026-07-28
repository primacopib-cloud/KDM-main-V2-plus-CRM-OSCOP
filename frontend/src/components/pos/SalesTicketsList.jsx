import { useState } from 'react';
import { toast } from 'sonner';
import { FileText, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';

const PAY = { CARD: '💳 CB', UC: "🪙 UC", MIXED: '🪙+💳 Mixte', CASH: '💵 Espèces' };

// Historique des ventes du jour avec téléchargement du ticket PDF (archivage comptable)
export const SalesTicketsList = ({ sales }) => {
  const [open, setOpen] = useState(false);
  const [pdfId, setPdfId] = useState(null);
  if (!sales || sales.length === 0) return null;

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
          <FileText className="w-3.5 h-3.5 text-[#D9B35A]" /> Ventes du jour — tickets PDF ({sales.length})
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
      </button>
      {open && (
        <div className="mt-2 space-y-1 max-h-56 overflow-y-auto pr-1">
          {sales.map((s) => (
            <div key={s.id || s.order_number} data-testid={`sale-row-${s.order_number}`}
              className="flex items-center gap-2 text-xs rounded-lg bg-white/[0.03] border border-white/[0.05] px-2.5 py-1.5">
              <span className="font-mono text-white/45 shrink-0">{new Date(s.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>
              <span className="font-mono truncate">{s.order_number}</span>
              <span className="text-white/45 truncate hidden sm:block">{s.customer_name || ''}</span>
              <span className="ml-auto shrink-0 text-white/55">{PAY[s.payment_method] || PAY.CASH}</span>
              <span className="font-mono font-bold shrink-0">{(s.total_cents / 100).toFixed(2)} €</span>
              <button type="button" onClick={() => downloadPdf(s)} disabled={pdfId === s.id}
                data-testid={`ticket-pdf-${s.order_number}`} title="Télécharger le ticket PDF"
                className="shrink-0 flex items-center gap-1 px-2 py-1 rounded-lg font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/35 hover:bg-[#D9B35A]/25 disabled:opacity-50">
                {pdfId === s.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />} PDF
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
