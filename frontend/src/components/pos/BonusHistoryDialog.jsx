import { useState } from 'react';
import { toast } from 'sonner';
import { Trophy, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';

const weekLabel = (w) => {
  try { return `Semaine du ${new Date(w).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })}`; }
  catch { return w; }
};

export const BonusHistoryDialog = () => {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const openDialog = async () => {
    setOpen(true);
    setLoading(true);
    try {
      setData(await lolodriveAPI.managerBonusHistory());
    } catch (e) { toast.error(e.message); } finally { setLoading(false); }
  };

  return (
    <>
      <button type="button" onClick={openDialog} data-testid="bonus-history-btn"
        className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/40 hover:bg-[#D9B35A]/25">
        <Trophy className="w-3 h-3" /> Historique des primes
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md" data-testid="bonus-history-dialog">
          <DialogHeader><DialogTitle>🏆 Historique des primes UC</DialogTitle></DialogHeader>
          {loading && <div className="py-8 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto text-[#D9B35A]" /></div>}
          {!loading && data && (
            <>
              <div className="rounded-xl border border-[#D9B35A]/30 bg-[#D9B35A]/[0.06] px-3 py-2 text-xs flex justify-between" data-testid="bonus-history-total">
                <span>{data.count} prime{data.count > 1 ? 's' : ''} offerte{data.count > 1 ? 's' : ''}</span>
                <b className="text-[#D9B35A]">{data.total_uc} UC au total</b>
              </div>
              {data.rewards.length === 0 && (
                <p className="text-xs text-white/40 py-4 text-center">Aucune prime offerte pour l'instant.</p>
              )}
              <div className="max-h-72 overflow-y-auto space-y-1.5">
                {data.rewards.map((r) => (
                  <div key={`${r.point_id}-${r.week}`} data-testid={`bonus-row-${r.week}`}
                    className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                    <span>
                      <b>{r.operator_name}</b>
                      <span className="block text-white/40 text-[10px]">
                        {weekLabel(r.week)} · versée le {new Date(r.created_at).toLocaleDateString('fr-FR')}
                      </span>
                    </span>
                    <b className="text-[#D9B35A] font-mono shrink-0 ml-2">+{r.amount_uc} UC</b>
                  </div>
                ))}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};
