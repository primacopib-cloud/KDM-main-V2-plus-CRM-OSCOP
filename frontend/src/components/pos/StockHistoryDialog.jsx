import { useEffect, useState } from 'react';
import { History, TrendingDown, TrendingUp, PackagePlus } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';

const TYPE_STYLE = {
  RESTOCK: { label: 'Réassort / ajustement', color: '#10b981', Icon: PackagePlus },
  SALE: { label: 'Vente comptoir', color: '#f59e0b', Icon: TrendingDown },
  INITIAL: { label: 'Stock initial fiche', color: '#D9B35A', Icon: TrendingUp },
  INVENTORY: { label: 'Inventaire', color: '#22d3ee', Icon: PackagePlus },
  DRIVE: { label: 'Retrait Drive', color: '#7c3aed', Icon: TrendingDown },
};

export const StockHistoryDialog = ({ product, onClose }) => {
  const [movements, setMovements] = useState(null);
  useEffect(() => {
    if (product) lolodriveAPI.posStockHistory(product.sku).then((d) => setMovements(d.movements || [])).catch(() => setMovements([]));
  }, [product]);
  if (!product) return null;
  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md" data-testid="stock-history-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <History className="w-4 h-4 text-[#D9B35A]" /> Historique stock — {product.name}
          </DialogTitle>
        </DialogHeader>
        <div className="max-h-80 overflow-y-auto space-y-1.5">
          {movements === null && <p className="text-xs text-white/40">Chargement…</p>}
          {movements?.length === 0 && <p className="text-xs text-white/40" data-testid="stock-history-empty">Aucun mouvement enregistré pour ce produit.</p>}
          {movements?.map((m, i) => {
            const st = TYPE_STYLE[m.type] || TYPE_STYLE.RESTOCK;
            return (
              <div key={i} className="flex items-center gap-2 text-xs p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]"
                data-testid={`stock-movement-${i}`}>
                <st.Icon className="w-3.5 h-3.5 shrink-0" style={{ color: st.color }} />
                <span className="flex-1 min-w-0">
                  <span className="font-semibold" style={{ color: st.color }}>{st.label}</span>
                  {m.ref && <span className="text-white/40"> · {m.ref}</span>}
                  <span className="block text-white/40 text-[10px]">
                    {new Date(m.created_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    {m.point_code ? ` · ${m.point_code}` : ''}
                  </span>
                </span>
                <span className="font-mono font-bold shrink-0" style={{ color: m.delta >= 0 ? '#10b981' : '#f59e0b' }}>
                  {m.delta >= 0 ? '+' : ''}{m.delta}
                </span>
                <span className="font-mono text-white/60 shrink-0 w-16 text-right">→ {m.stock_after}</span>
              </div>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
};
