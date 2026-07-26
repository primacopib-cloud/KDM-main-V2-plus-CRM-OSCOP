import { Star } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

const Stars = ({ n }) => (
  <span className="inline-flex gap-0.5">
    {[1, 2, 3, 4, 5].map((i) => (
      <Star key={i} className={`w-3.5 h-3.5 ${i <= n ? 'fill-[#D9B35A] text-[#D9B35A]' : 'text-white/20'}`} />
    ))}
  </span>
);

export const RelayReviewsDialog = ({ open, onOpenChange, pointName, reviews }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="bg-[#1A092D] border-white/15 text-white max-w-lg max-h-[80vh] overflow-y-auto" data-testid="relay-reviews-dialog">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2 text-base">
          <Star className="w-4 h-4 fill-[#D9B35A] text-[#D9B35A]" /> Avis des titulaires — {pointName}
        </DialogTitle>
      </DialogHeader>
      <div className="space-y-3">
        {(reviews || []).length === 0 && <p className="text-sm text-white/40">Aucun avis pour le moment.</p>}
        {(reviews || []).map((r) => (
          <div key={r.id} className="p-3 rounded-xl bg-white/[0.04] border border-white/10" data-testid={`review-item-${r.id}`}>
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-bold text-white">{r.author}</p>
              <span className="text-[10px] text-white/35">{r.date}</span>
            </div>
            <Stars n={r.rating} />
            {r.comment && <p className="text-xs text-white/75 mt-1">{r.comment}</p>}
            {r.reply && (
              <div className="mt-2 p-2 rounded-lg bg-[#D9B35A]/[0.08] border border-[#D9B35A]/25">
                <p className="text-[10px] uppercase tracking-wider text-[#D9B35A] font-bold">Réponse du relais</p>
                <p className="text-xs text-white/80" data-testid={`review-reply-${r.id}`}>{r.reply}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </DialogContent>
  </Dialog>
);
