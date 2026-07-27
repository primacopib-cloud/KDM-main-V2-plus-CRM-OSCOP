import { useEffect, useState } from 'react';
import { Receipt } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';

export const UcDebitsDialog = ({ onClose }) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    lolodriveAPI.posUcDebits().then(setData).catch(() => setData({ debits: [], total_debited_uc: 0, balance_uc: 0 }));
  }, []);
  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md" data-testid="uc-debits-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <Receipt className="w-4 h-4 text-[#c4b5fd]" /> Débits UC produits relais
          </DialogTitle>
        </DialogHeader>
        {data && (
          <>
            <div className="flex items-center justify-between text-xs rounded-lg bg-[#7c3aed]/[0.08] border border-[#7c3aed]/30 px-3 py-2">
              <span>Total débité : <b className="text-[#c4b5fd]" data-testid="uc-debits-total">{data.total_debited_uc} UC</b></span>
              <span>Solde : <b className={data.balance_uc < 0 ? 'text-red-300' : 'text-emerald-300'}>{data.balance_uc} UC</b></span>
            </div>
            <div className="max-h-72 overflow-y-auto space-y-1.5">
              {data.debits.length === 0 && <p className="text-xs text-white/40">Aucun débit UC pour le moment.</p>}
              {data.debits.map((d, i) => (
                <div key={i} className="flex items-center gap-2 text-xs p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]"
                  data-testid={`uc-debit-${i}`}>
                  <span className="flex-1 min-w-0">
                    <span className="font-semibold">{d.order_number || 'Vente comptoir'}</span>
                    <span className="block text-white/40 text-[10px]">
                      {new Date(d.created_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </span>
                  <span className="font-mono font-bold text-amber-300 shrink-0">−{d.amount_uc} UC</span>
                </div>
              ))}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
