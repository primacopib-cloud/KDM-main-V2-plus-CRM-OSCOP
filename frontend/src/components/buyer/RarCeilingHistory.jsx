import { useState } from 'react';
import { History, ChevronDown, ChevronUp, Loader2, FileDown } from 'lucide-react';
import { toast } from 'sonner';
import { rarAPI } from '../../services/api.rar';

const fmt = (c) => `${(Math.abs(c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;
const fmtDate = (d) => (d ? new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—');

const TYPE_STYLE = {
  GRANT: 'text-[#D9B35A]',
  RESERVE: 'text-amber-300',
  CREDIT: 'text-sky-300',
  RESTORE: 'text-emerald-300',
};

// Historique des mouvements de plafond RàR (acheteur)
export const RarCeilingHistory = () => {
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState(null);
  const [loading, setLoading] = useState(false);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && events === null) {
      setLoading(true);
      try {
        const d = await rarAPI.ceilingHistory();
        setEvents(d.events || []);
      } catch { setEvents([]); } finally { setLoading(false); }
    }
  };

  return (
    <div className="mt-3">
      <button type="button" onClick={toggle} data-testid="rar-history-toggle"
        className="text-[10px] text-white/45 hover:text-white/70 flex items-center gap-1">
        <History className="w-3 h-3" /> Historique du plafond
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {open && (
        <div className="mt-2 flex items-center gap-1.5" data-testid="rar-statement-bar">
          <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} data-testid="rar-statement-month"
            className="px-2 py-1 rounded bg-black/30 border border-white/15 text-[10px] text-white" />
          <button type="button" data-testid="rar-statement-pdf-btn"
            onClick={() => rarAPI.downloadCeilingStatement(month).then(() => toast.success('Relevé téléchargé')).catch((e) => toast.error(e.message))}
            className="px-2 py-1 rounded text-[10px] font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/30 hover:bg-[#D9B35A]/20 flex items-center gap-1">
            <FileDown className="w-3 h-3" /> Relevé mensuel PDF
          </button>
        </div>
      )}
      {open && (
        <div className="mt-2 space-y-1 max-h-52 overflow-y-auto pr-1" data-testid="rar-history-list">
          {loading && <Loader2 className="w-4 h-4 animate-spin text-white/40" />}
          {events && events.length === 0 && !loading && (
            <p className="text-[10px] text-white/35">Aucun mouvement de plafond pour le moment.</p>
          )}
          {(events || []).map((e, i) => (
            <div key={i} className="flex items-center justify-between gap-2 p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.07] text-[10px]"
              data-testid={`rar-history-event-${i}`}>
              <span className="text-white/60 truncate">
                <span className="text-white/35 mr-1.5">{fmtDate(e.date)}</span>
                {e.label}
                {e.order_number && <span className="text-white/35 ml-1">· {e.order_number}</span>}
              </span>
              <span className={`font-mono font-bold shrink-0 ${TYPE_STYLE[e.type] || 'text-white/70'}`}>
                {e.amount_cents < 0 ? '−' : '+'}{fmt(e.amount_cents)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
