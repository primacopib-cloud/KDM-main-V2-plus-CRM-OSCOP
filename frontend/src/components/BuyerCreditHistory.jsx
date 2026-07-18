import { useState, useEffect } from 'react';
import { History, ChevronDown, ChevronUp } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmtDate = (iso) => { try { return new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (_e) { return iso; } };

/** Historique des crédits de l'acheteur pro (dashboard). */
export const BuyerCreditHistory = () => {
  const [transactions, setTransactions] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetch(`${API}/team/my-credits`, { credentials: 'include' })
      .then((r) => r.ok && r.json())
      .then((d) => d && setTransactions(d.transactions || []))
      .catch(() => {});
  }, []);

  return (
    <div className="glass-panel-soft rounded-[18px] p-5 mb-6" data-testid="buyer-credit-history">
      <button type="button" onClick={() => setOpen(!open)} className="w-full flex items-center justify-between" data-testid="buyer-credit-history-toggle">
        <span className="flex items-center gap-2 text-sm font-semibold">
          <History className="w-4 h-4 text-[#D4AF37]" /> Historique de mes crédits
          <span className="text-xs font-normal text-white/50">({transactions.length})</span>
        </span>
        {open ? <ChevronUp className="w-4 h-4 opacity-50" /> : <ChevronDown className="w-4 h-4 opacity-50" />}
      </button>
      {open && (
        <div className="divide-y divide-white/5 mt-3" data-testid="buyer-credit-history-list">
          {transactions.map((t) => (
            <div key={t.id} className="flex items-center justify-between gap-2 py-2 text-sm">
              <div className="min-w-0">
                <p className="truncate text-xs">{t.detail || t.action}</p>
                <p className="text-[10px] text-white/40">{fmtDate(t.at)}</p>
              </div>
              <span className={`font-bold text-sm shrink-0 ${t.cost > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                {t.cost > 0 ? `−${t.cost}` : `+${-t.cost}`}
              </span>
            </div>
          ))}
          {transactions.length === 0 && (
            <p className="text-xs text-white/40 py-3">Aucune transaction de crédits pour le moment.</p>
          )}
        </div>
      )}
    </div>
  );
};
