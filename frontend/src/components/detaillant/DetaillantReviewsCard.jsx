import { useEffect, useState } from 'react';
import { MessageSquareReply, Star } from 'lucide-react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../services/api.detaillant';

// Avis reçus par le POP'S + réponse publique
export const DetaillantReviewsCard = () => {
  const [reviews, setReviews] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [busy, setBusy] = useState('');
  const load = () => detaillantAPI.detaillantReviews().then((d) => setReviews(d.reviews || [])).catch(() => setReviews([]));
  useEffect(() => { load(); }, []);
  if (!reviews || reviews.length === 0) return null;

  const reply = async (id) => {
    setBusy(id);
    try {
      await detaillantAPI.reviewReply(id, drafts[id] || '');
      toast.success('✓ Réponse publiée — visible sur la vitrine');
      load();
    } catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="dt-reviews-card">
      <h3 className="text-sm font-bold text-[#E9CF8E] mb-3 flex items-center gap-2">
        <Star className="w-4 h-4" /> Avis reçus ({reviews.length})
      </h3>
      <div className="space-y-3">
        {reviews.map((r) => (
          <div key={r.id} className="rounded-xl bg-white/[0.03] border border-white/[0.08] p-3" data-testid={`dt-review-${r.id}`}>
            <div className="flex items-center gap-2">
              <span className="text-amber-300 text-xs font-bold">{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span>
              <span className="text-[10px] text-white/40">{r.auction_reference} · {new Date(r.created_at).toLocaleDateString('fr-FR')}</span>
            </div>
            {r.comment && <p className="text-[11px] text-white/65 mt-1 italic">« {r.comment} »</p>}
            {r.reply ? (
              <p className="text-[11px] text-emerald-300/85 mt-2 flex items-start gap-1.5" data-testid={`dt-review-reply-${r.id}`}>
                <MessageSquareReply className="w-3.5 h-3.5 shrink-0 mt-px" /> Votre réponse : {r.reply}
              </p>
            ) : (
              <div className="flex gap-2 mt-2">
                <input value={drafts[r.id] || ''} onChange={(e) => setDrafts((d) => ({ ...d, [r.id]: e.target.value }))}
                  placeholder="Répondre publiquement à cet avis…" maxLength={500}
                  data-testid={`dt-review-reply-input-${r.id}`}
                  className="flex-1 h-8 px-2.5 rounded-lg bg-white/[0.05] border border-white/15 text-[11px] text-white placeholder-white/30 outline-none focus:border-emerald-400/50" />
                <button onClick={() => reply(r.id)} disabled={busy === r.id || !(drafts[r.id] || '').trim()}
                  data-testid={`dt-review-reply-btn-${r.id}`}
                  className="px-3 h-8 rounded-lg text-[10px] font-bold text-emerald-300 border border-emerald-400/40 bg-emerald-500/10 hover:bg-emerald-500/20 disabled:opacity-40">
                  Publier
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
