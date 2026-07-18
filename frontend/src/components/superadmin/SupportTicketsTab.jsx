import { useState, useEffect, useCallback } from 'react';
import { LifeBuoy, Send, Loader2, ChevronDown, ChevronUp, CheckCircle2, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { apiCall } from '../../services/http';

const STATUS_STYLES = {
  OPEN: { label: 'Ouvert', cls: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  ANSWERED: { label: 'Répondu', cls: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  CLOSED: { label: 'Fermé', cls: 'bg-white/10 text-white/50 border-white/20' },
};

const CATEGORY_LABELS = {
  GENERAL: 'Général', COMPTE: 'Compte', COMMANDE: 'Commande',
  PAIEMENT: 'Paiement', CREDISCOP: "CREDI'SCOP", TECHNIQUE: 'Technique',
};

const TicketCard = ({ ticket, onReply, onClose }) => {
  const [open, setOpen] = useState(false);
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const st = STATUS_STYLES[ticket.status] || STATUS_STYLES.OPEN;

  const handleReply = async () => {
    setSending(true);
    try {
      await onReply(ticket.id, reply);
      setReply('');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="glass-panel-soft rounded-[16px] overflow-hidden" data-testid={`support-ticket-${ticket.ticket_number}`}>
      <button onClick={() => setOpen(!open)} className="w-full p-4 flex items-center gap-3 text-left hover:bg-white/[0.03] transition-colors" data-testid={`support-ticket-toggle-${ticket.ticket_number}`}>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${st.cls}`}>{st.label}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white/90 truncate">{ticket.subject}</p>
          <p className="text-xs text-white/50 truncate">
            {ticket.ticket_number} · {ticket.name} &lt;{ticket.email}&gt; · {CATEGORY_LABELS[ticket.category] || ticket.category} · {new Date(ticket.created_at).toLocaleString('fr-FR')}
          </p>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-white/50" /> : <ChevronDown className="w-4 h-4 text-white/50" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3">
          <div className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-white/80 whitespace-pre-wrap">{ticket.message}</div>

          {(ticket.replies || []).map((r, i) => (
            r.from_client ? (
              <div key={`${ticket.id}-r${i}`} className="p-3 rounded-xl bg-blue-500/[0.07] border border-blue-500/20">
                <p className="text-xs text-blue-400 font-semibold mb-1">↩ {ticket.name} (client) — {new Date(r.at).toLocaleString('fr-FR')}</p>
                <p className="text-sm text-white/80 whitespace-pre-wrap">{r.message}</p>
              </div>
            ) : (
              <div key={`${ticket.id}-r${i}`} className="p-3 rounded-xl bg-[#D9B35A]/[0.07] border border-[#D9B35A]/20">
                <p className="text-xs text-[#D9B35A] font-semibold mb-1">↩ {r.admin_name} — {new Date(r.at).toLocaleString('fr-FR')}</p>
                <p className="text-sm text-white/80 whitespace-pre-wrap">{r.message}</p>
              </div>
            )
          ))}

          {ticket.status !== 'CLOSED' && (
            <div className="space-y-2">
              <textarea rows={3} value={reply} onChange={(e) => setReply(e.target.value)}
                placeholder="Votre réponse (envoyée par email au demandeur)…"
                className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-sm focus:outline-none focus:border-[#D9B35A]/60 resize-y"
                data-testid={`support-reply-input-${ticket.ticket_number}`} />
              <div className="flex gap-2">
                <button onClick={handleReply} disabled={sending || reply.trim().length < 2}
                  className="btn-gold inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold disabled:opacity-50"
                  data-testid={`support-reply-btn-${ticket.ticket_number}`}>
                  {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  Répondre par email
                </button>
                <button onClick={() => onClose(ticket.id)}
                  className="btn-ghost inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium"
                  data-testid={`support-close-btn-${ticket.ticket_number}`}>
                  <XCircle className="w-3.5 h-3.5" /> Fermer le ticket
                </button>
              </div>
            </div>
          )}
          {ticket.status === 'CLOSED' && (
            <p className="text-xs text-white/40 flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5" /> Ticket fermé</p>
          )}
        </div>
      )}
    </div>
  );
};

export const SupportTicketsTab = () => {
  const [tickets, setTickets] = useState([]);
  const [counts, setCounts] = useState({});
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (f = filter) => {
    setLoading(true);
    try {
      const data = await apiCall(`/support/admin/tickets${f ? `?status_filter=${f}` : ''}`);
      setTickets(data.tickets);
      setCounts(data.counts);
    } catch (e) {
      toast.error(e.message || 'Erreur de chargement des tickets');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const handleReply = async (ticketId, message) => {
    try {
      await apiCall(`/support/admin/tickets/${ticketId}/reply`, { method: 'POST', body: JSON.stringify({ message }) });
      toast.success('Réponse envoyée par email au demandeur');
      load();
    } catch (e) {
      toast.error(e.message || "Erreur lors de l'envoi");
      throw e;
    }
  };

  const handleClose = async (ticketId) => {
    try {
      await apiCall(`/support/admin/tickets/${ticketId}/status`, { method: 'PATCH', body: JSON.stringify({ status: 'CLOSED' }) });
      toast.success('Ticket fermé');
      load();
    } catch (e) {
      toast.error(e.message || 'Erreur');
    }
  };

  const FILTERS = [
    { value: '', label: `Tous (${(counts.OPEN || 0) + (counts.ANSWERED || 0) + (counts.CLOSED || 0)})` },
    { value: 'OPEN', label: `Ouverts (${counts.OPEN || 0})` },
    { value: 'ANSWERED', label: `Répondus (${counts.ANSWERED || 0})` },
    { value: 'CLOSED', label: `Fermés (${counts.CLOSED || 0})` },
  ];

  return (
    <div className="space-y-4" data-testid="support-tickets-tab">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <LifeBuoy className="w-5 h-5 text-[#D9B35A]" /> Tickets support
        </h2>
        <div className="flex gap-2">
          {FILTERS.map((f) => (
            <button key={f.value || 'all'} onClick={() => setFilter(f.value)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-colors ${
                filter === f.value ? 'bg-[#D9B35A]/20 text-[#D9B35A] border-[#D9B35A]/30' : 'bg-white/[0.04] text-white/60 border-white/[0.08] hover:text-white'
              }`}
              data-testid={`support-filter-${f.value || 'all'}`}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>
      ) : tickets.length === 0 ? (
        <div className="glass-panel-soft rounded-[16px] p-10 text-center text-white/50 text-sm" data-testid="support-empty-state">
          Aucun ticket {filter ? `avec le statut « ${STATUS_STYLES[filter]?.label} »` : ''} pour le moment.
        </div>
      ) : (
        <div className="space-y-3">
          {tickets.map((t) => <TicketCard key={t.id} ticket={t} onReply={handleReply} onClose={handleClose} />)}
        </div>
      )}
    </div>
  );
};
