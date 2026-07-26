import { useEffect, useState } from 'react';
import { Star, Loader2, Send } from 'lucide-react';
import { toast } from 'sonner';
import { lolodriveAPI } from '../../services/api';

export const RelayReviewPrompt = () => {
  const [pending, setPending] = useState([]);
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    lolodriveAPI.relayReviewsPending()
      .then((d) => setPending(d.pending || []))
      .catch(() => {});
  }, []);

  if (!pending.length) return null;
  const cur = pending[0];

  const submit = async () => {
    if (!rating) { toast.error('Choisissez une note de 1 à 5 étoiles'); return; }
    setBusy(true);
    try {
      await lolodriveAPI.submitRelayReview({ order_id: cur.order_id, rating, comment });
      toast.success('Merci pour votre avis, il renforce la confiance du réseau ⭐');
      setPending(pending.slice(1));
      setRating(0); setHover(0); setComment('');
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="mb-6 rounded-2xl border border-[#D9B35A]/35 p-4"
      style={{ background: 'linear-gradient(90deg, rgba(217,179,90,0.12), rgba(255,255,255,0.02))' }}
      data-testid="relay-review-prompt">
      <p className="text-sm font-bold text-white">
        Comment s'est passé votre retrait chez <span className="text-[#E9CF8E]">{cur.point_name}</span> ?
      </p>
      <p className="text-[11px] text-white/45 mb-3">Commande {cur.order_number} — votre avis aide les autres titulaires du PASS.</p>
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1" data-testid="relay-review-stars">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" onClick={() => setRating(n)}
              onMouseEnter={() => setHover(n)} onMouseLeave={() => setHover(0)}
              data-testid={`relay-review-star-${n}`}
              className="transition-transform hover:scale-125">
              <Star className={`w-6 h-6 ${(hover || rating) >= n ? 'fill-[#D9B35A] text-[#D9B35A]' : 'text-white/25'}`} />
            </button>
          ))}
        </div>
        <input value={comment} onChange={(e) => setComment(e.target.value)} maxLength={500}
          placeholder="Un commentaire ? (facultatif)" data-testid="relay-review-comment"
          className="flex-1 min-w-[200px] h-9 px-3 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15" />
        <button type="button" onClick={submit} disabled={busy} data-testid="relay-review-submit"
          className="inline-flex items-center gap-1.5 px-4 h-9 rounded-full text-xs font-bold text-black disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #c9a34a)' }}>
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />} Envoyer mon avis
        </button>
      </div>
    </div>
  );
};
