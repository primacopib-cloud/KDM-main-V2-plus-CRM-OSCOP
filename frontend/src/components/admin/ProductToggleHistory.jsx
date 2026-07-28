import { useState } from 'react';
import { History, ChevronDown, ChevronUp, Ban, RotateCcw } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

// Historique des retraits / remises au catalogue (qui, quand, quel produit)
export const ProductToggleHistory = () => {
  const [open, setOpen] = useState(false);
  const [logs, setLogs] = useState(null);

  const toggle = () => {
    if (!open && logs === null) {
      lolodriveAPI.adminToggleHistory().then((d) => setLogs(d.logs || [])).catch(() => setLogs([]));
    }
    setOpen(!open);
  };

  return (
    <div className="mt-3 pt-3 border-t border-white/[0.06]">
      <button type="button" onClick={toggle} data-testid="toggle-history-btn"
        className="w-full flex items-center justify-between text-left text-xs font-semibold text-white/60 hover:text-white">
        <span className="flex items-center gap-1.5"><History className="w-3.5 h-3.5 text-[#D9B35A]" /> Historique retraits produits</span>
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>
      {open && (
        <div className="mt-2 max-h-48 overflow-y-auto space-y-1" data-testid="toggle-history-list">
          {logs === null && <p className="text-[11px] text-white/30">Chargement…</p>}
          {logs?.length === 0 && <p className="text-[11px] text-white/30">Aucun retrait ou remise au catalogue enregistré.</p>}
          {logs?.map((l, i) => (
            <p key={i} className="text-[11px] text-white/60 flex items-center gap-1.5" data-testid={`toggle-log-${l.sku}-${i}`}>
              {l.is_active
                ? <RotateCcw className="w-3 h-3 text-emerald-400 shrink-0" />
                : <Ban className="w-3 h-3 text-red-400 shrink-0" />}
              <span className="text-white/35 font-mono shrink-0">{new Date(l.at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
              <b className="truncate">{l.name || l.sku}</b>
              <span className={l.is_active ? 'text-emerald-300' : 'text-red-300'}>{l.is_active ? 'remis au catalogue' : 'retiré'}</span>
              <span className="text-white/35 truncate">par {l.by_name || l.by_email || '—'}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
};
