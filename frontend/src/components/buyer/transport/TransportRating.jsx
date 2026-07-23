import { useState } from 'react';
import { Star, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';

export const TransportRating = ({ ot, onChanged }) => {
  const [open, setOpen] = useState(false);
  const [stars, setStars] = useState(ot.rating?.stars || 0);
  const [comment, setComment] = useState(ot.rating?.comment || '');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/logiscop-transport/orders/${ot.id}/rating`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
        body: JSON.stringify({ stars, comment }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Notation impossible');
      toast.success(`Livraison ${ot.ref} notée ${stars}/5 — merci !`);
      setOpen(false);
      onChanged?.();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  if (!open) {
    return ot.rating ? (
      <button type="button" onClick={() => setOpen(true)} data-testid={`rating-view-${ot.ref.replace(/\//g, '-')}`}
        title={ot.rating.comment || 'Modifier ma note'}
        className="inline-flex items-center gap-0.5 text-[#E9CF8E] hover:text-white text-[10px] font-bold">
        <Star size={11} fill="currentColor" /> {ot.rating.stars}/5
      </button>
    ) : (
      <button type="button" onClick={() => setOpen(true)} data-testid={`rating-open-${ot.ref.replace(/\//g, '-')}`}
        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold bg-white/[0.06] text-white/60 hover:text-[#E9CF8E] border border-white/15">
        <Star size={11} /> Noter
      </button>
    );
  }

  return (
    <span className="inline-flex flex-col gap-1.5 p-2 rounded-lg bg-white/[0.05] border border-[#D9B35A]/30"
      data-testid={`rating-form-${ot.ref.replace(/\//g, '-')}`}>
      <span className="inline-flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" onClick={() => setStars(n)} data-testid={`rating-star-${n}`}
            className={n <= stars ? 'text-[#E9CF8E]' : 'text-white/25 hover:text-white/50'}>
            <Star size={15} fill={n <= stars ? 'currentColor' : 'none'} />
          </button>
        ))}
      </span>
      <textarea value={comment} onChange={(e) => setComment(e.target.value)} data-testid="rating-comment"
        placeholder="Commentaire (ponctualité, état de la marchandise…)"
        className="w-44 h-12 px-2 py-1 rounded bg-white/[0.06] border border-white/15 text-[10px] text-white placeholder:text-white/35" />
      <span className="inline-flex gap-1.5">
        <button type="button" onClick={submit} disabled={busy || stars < 1} data-testid="rating-submit"
          className="px-2 py-1 rounded-lg text-[10px] font-bold bg-[#D9B35A] text-[#1F0A33] disabled:opacity-50 inline-flex items-center gap-1">
          {busy ? <Loader2 size={10} className="animate-spin" /> : <Star size={10} />} Envoyer
        </button>
        <button type="button" onClick={() => setOpen(false)}
          className="px-2 py-1 rounded-lg text-[10px] text-white/50 border border-white/15">Annuler</button>
      </span>
    </span>
  );
};
