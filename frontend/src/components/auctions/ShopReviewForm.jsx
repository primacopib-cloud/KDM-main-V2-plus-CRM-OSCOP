import { useState } from 'react';
import { Star } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

// Avis boutique après enlèvement d'un lot détaillant
export const ShopReviewForm = ({ win }) => {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/auctions/${win.id}/shop-review`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ rating, comment }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erreur');
      toast.success(`✓ Merci ! ${win.retailer?.company_name} affiche désormais ★ ${data.rating_avg}`);
      setDone(true);
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  if (done) {
    return (
      <span className="block text-[9px] text-amber-300/80 mt-1" data-testid={`shop-reviewed-${win.id}`}>
        ★ Boutique notée — merci !
      </span>
    );
  }
  return (
    <div className="mt-1.5 rounded-lg border border-amber-400/25 bg-amber-500/[0.06] p-2" data-testid={`shop-review-form-${win.id}`}>
      <p className="text-[9px] font-bold text-amber-200">Notez la boutique {win.retailer?.company_name}</p>
      <div className="flex items-center gap-0.5 mt-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} onClick={() => setRating(n)} data-testid={`shop-review-star-${n}-${win.id}`}
            className="p-0.5">
            <Star className={`w-4 h-4 ${n <= rating ? 'text-amber-300 fill-amber-300' : 'text-white/25'}`} />
          </button>
        ))}
      </div>
      <input value={comment} onChange={(e) => setComment(e.target.value)} maxLength={500}
        placeholder="Un mot sur l'enlèvement ? (optionnel)" data-testid={`shop-review-comment-${win.id}`}
        className="w-full mt-1.5 h-7 px-2 rounded-md bg-white/[0.06] border border-white/15 text-[10px] text-white placeholder-white/30 outline-none focus:border-amber-400/50" />
      <button onClick={submit} disabled={busy || rating === 0} data-testid={`shop-review-submit-${win.id}`}
        className="mt-1.5 px-3 h-6 rounded-full text-[9px] font-bold bg-amber-400/20 text-amber-200 border border-amber-400/40 hover:bg-amber-400/30 disabled:opacity-40">
        {busy ? 'Envoi…' : "Envoyer l'avis"}
      </button>
    </div>
  );
};
