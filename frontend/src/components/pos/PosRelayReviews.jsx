import { useEffect, useState } from 'react';
import { Star, Loader2, Reply, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';

const Stars = ({ n }) => (
  <span className="inline-flex gap-0.5">
    {[1, 2, 3, 4, 5].map((i) => (
      <Star key={i} className={`w-3.5 h-3.5 ${i <= n ? 'fill-[#D9B35A] text-[#D9B35A]' : 'text-white/20'}`} />
    ))}
  </span>
);

const ReviewRow = ({ review, onReplied }) => {
  const [reply, setReply] = useState('');
  const [busy, setBusy] = useState(false);
  const send = async () => {
    if (!reply.trim()) { toast.error('Écrivez votre réponse'); return; }
    setBusy(true);
    try {
      await lolodriveAPI.replyRelayReview(review.id, reply);
      toast.success('Réponse publiée ✓');
      onReplied();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return (
    <div className="p-3 rounded-xl bg-white/[0.04] border border-white/10" data-testid={`pos-review-${review.id}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-bold text-white">{review.author}</p>
        <span className="text-[10px] text-white/35">{review.date}</span>
      </div>
      <Stars n={review.rating} />
      {review.comment && <p className="text-xs text-white/75 mt-1">{review.comment}</p>}
      {review.reply ? (
        <div className="mt-2 p-2 rounded-lg bg-[#D9B35A]/[0.08] border border-[#D9B35A]/25">
          <p className="text-[10px] uppercase tracking-wider text-[#D9B35A] font-bold">Votre réponse publique</p>
          <p className="text-xs text-white/80">{review.reply}</p>
        </div>
      ) : (
        <div className="mt-2 flex gap-2">
          <input value={reply} onChange={(e) => setReply(e.target.value)} maxLength={500}
            placeholder="Répondre publiquement à ce client…" data-testid={`pos-review-reply-input-${review.id}`}
            className="flex-1 h-8 px-2.5 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15" />
          <button type="button" onClick={send} disabled={busy} data-testid={`pos-review-reply-send-${review.id}`}
            className="inline-flex items-center gap-1 px-3 h-8 rounded-lg text-[11px] font-bold text-black disabled:opacity-50"
            style={{ background: '#D9B35A' }}>
            {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Reply className="w-3 h-3" />} Publier
          </button>
        </div>
      )}
    </div>
  );
};

export const PosRelayReviews = () => {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);

  const load = () => {
    lolodriveAPI.managerMyReviews().then(setData).catch(() => {});
  };
  useEffect(load, []);

  if (!data) return null;
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} data-testid="pos-reviews-btn"
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-white/80 hover:border-[#D9B35A]/50 transition-colors">
        <MessageSquare className="w-3 h-3 text-[#D9B35A]" />
        Avis clients ({data.count}){data.avg ? ` · ★ ${data.avg}` : ''}
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-[#1A092D] border-white/15 text-white max-w-lg max-h-[80vh] overflow-y-auto" data-testid="pos-reviews-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Star className="w-4 h-4 fill-[#D9B35A] text-[#D9B35A]" />
              Avis reçus — {data.point?.name}{data.avg ? ` · ★ ${data.avg} (${data.count})` : ''}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            {data.reviews.length === 0 && <p className="text-sm text-white/40">Aucun avis reçu pour le moment.</p>}
            {data.reviews.map((r) => <ReviewRow key={r.id} review={r} onReplied={load} />)}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};
