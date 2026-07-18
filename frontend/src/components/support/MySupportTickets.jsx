import { useState, useEffect } from 'react';
import { History, ChevronDown, ChevronUp, Loader2, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { apiCall } from '../../services/http';

const STATUS = {
  OPEN: { label: 'Ouvert', cls: 'bg-amber-500/20 text-amber-500 border-amber-500/30' },
  ANSWERED: { label: 'Répondu', cls: 'bg-blue-500/20 text-blue-500 border-blue-500/30' },
  CLOSED: { label: 'Fermé', cls: 'bg-white/10 text-white/50 border-white/20' },
};

const TicketRow = ({ ticket, onReopened }) => {
  const [open, setOpen] = useState(false);
  const [reopenMsg, setReopenMsg] = useState('');
  const [reopening, setReopening] = useState(false);
  const st = STATUS[ticket.status] || STATUS.OPEN;

  const handleReopen = async () => {
    setReopening(true);
    try {
      await apiCall(`/support/my-tickets/${ticket.id}/reopen`, {
        method: 'POST',
        body: JSON.stringify({ message: reopenMsg.trim() || null }),
      });
      toast.success('Ticket relancé — notre équipe a été prévenue');
      setReopenMsg('');
      onReopened();
    } catch (e) {
      toast.error(e.message || 'Erreur lors de la relance');
    } finally {
      setReopening(false);
    }
  };

  return (
    <div className="rounded-[14px] border border-white/[0.08] bg-white/[0.03] overflow-hidden" data-testid={`my-ticket-${ticket.ticket_number}`}>
      <button onClick={() => setOpen(!open)} className="w-full p-3.5 flex items-center gap-3 text-left hover:bg-white/[0.03] transition-colors" data-testid={`my-ticket-toggle-${ticket.ticket_number}`}>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${st.cls}`}>{st.label}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{ticket.subject}</p>
          <p className="text-xs text-white/50">{ticket.ticket_number} · {new Date(ticket.created_at).toLocaleString('fr-FR')}</p>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-white/50" /> : <ChevronDown className="w-4 h-4 text-white/50" />}
      </button>
      {open && (
        <div className="px-3.5 pb-3.5 space-y-2">
          <div className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-white/75 whitespace-pre-wrap">{ticket.message}</div>
          {(ticket.replies || []).length === 0 ? (
            <p className="text-xs text-white/40 italic">En attente de réponse de notre équipe…</p>
          ) : (
            ticket.replies.map((r, i) => (
              r.from_client ? (
                <div key={`${ticket.id}-r${i}`} className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.1]">
                  <p className="text-xs text-white/60 font-semibold mb-1">↩ Vous — {new Date(r.at).toLocaleString('fr-FR')}</p>
                  <p className="text-sm text-white/80 whitespace-pre-wrap">{r.message}</p>
                </div>
              ) : (
                <div key={`${ticket.id}-r${i}`} className="p-3 rounded-xl bg-[#D9B35A]/[0.08] border border-[#D9B35A]/25">
                  <p className="text-xs text-[#D9B35A] font-semibold mb-1">↩ Support — {new Date(r.at).toLocaleString('fr-FR')}</p>
                  <p className="text-sm text-white/80 whitespace-pre-wrap">{r.message}</p>
                </div>
              )
            ))
          )}
          {ticket.status === 'CLOSED' && (
            <div className="space-y-2 pt-1">
              <textarea rows={2} value={reopenMsg} onChange={(e) => setReopenMsg(e.target.value)}
                placeholder="Précisez pourquoi vous relancez (optionnel)…"
                className="w-full px-3 py-2 rounded-xl bg-white/[0.04] border border-white/10 text-sm focus:outline-none focus:border-[#D9B35A]/60 resize-y"
                data-testid={`reopen-input-${ticket.ticket_number}`} />
              <button onClick={handleReopen} disabled={reopening}
                className="btn-ghost inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium disabled:opacity-50"
                data-testid={`reopen-btn-${ticket.ticket_number}`}>
                {reopening ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                Relancer le ticket
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const MySupportTickets = ({ refreshKey = 0 }) => {
  const [tickets, setTickets] = useState(null);
  const [localRefresh, setLocalRefresh] = useState(0);

  useEffect(() => {
    apiCall('/support/my-tickets').then((d) => {
      setTickets(d.tickets);
      if (d.tickets.some((t) => t.user_unread)) {
        apiCall('/support/my-tickets/mark-read', { method: 'POST' }).catch(() => {});
      }
    }).catch(() => setTickets([]));
  }, [refreshKey, localRefresh]);

  if (tickets === null) {
    return <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A]" /></div>;
  }
  if (tickets.length === 0) return null;

  return (
    <div className="mt-10" data-testid="my-support-tickets">
      <h2 className="text-base md:text-lg font-semibold mb-4 flex items-center gap-2">
        <History className="w-5 h-5 text-[#D9B35A]" /> Mes demandes ({tickets.length})
      </h2>
      <div className="space-y-2.5">
        {tickets.map((t) => <TicketRow key={t.id} ticket={t} onReopened={() => setLocalRefresh((n) => n + 1)} />)}
      </div>
    </div>
  );
};
