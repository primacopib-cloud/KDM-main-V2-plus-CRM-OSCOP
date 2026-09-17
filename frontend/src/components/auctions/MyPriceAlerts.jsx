import { Target, X } from 'lucide-react';

// Panneau « Mes alertes prix » : liste des alertes prix cible actives du membre, retrait en un clic
export const MyPriceAlerts = ({ alerts, onRemove }) => {
  if (!alerts || alerts.length === 0) return null;
  return (
    <div className="mb-5 rounded-2xl border border-amber-400/25 bg-amber-500/[0.06] p-3" data-testid="my-price-alerts">
      <div className="text-[11px] font-bold uppercase tracking-wide text-amber-300 mb-2 inline-flex items-center gap-1.5">
        <Target className="w-3.5 h-3.5" /> Mes alertes prix ({alerts.length})
      </div>
      <div className="space-y-1.5">
        {alerts.map((al) => (
          <div key={al.auction_id} className="flex items-center gap-2 text-[11px] text-white/80"
            data-testid={`price-alert-row-${al.reference || al.auction_id}`}>
            <span className="truncate flex-1" title={al.title}>{al.title || al.reference || 'Lot'}</span>
            <span className="text-white/50 shrink-0">
              actuel {al.current_price_eur != null ? `${Number(al.current_price_eur).toFixed(2)} €` : '—'}
            </span>
            <span className="shrink-0 font-bold text-amber-300">cible {Number(al.target_eur).toFixed(2)} €</span>
            <button type="button" onClick={() => onRemove(al.auction_id)}
              data-testid={`price-alert-remove-${al.reference || al.auction_id}`}
              title="Retirer cette alerte"
              className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-white/45 border border-white/20 hover:text-red-300 hover:border-red-400/50 transition-colors">
              <X className="w-2.5 h-2.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
