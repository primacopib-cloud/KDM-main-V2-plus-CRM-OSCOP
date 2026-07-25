import { useState, useEffect, useCallback } from 'react';
import { Star, Trash2, Loader2, Send } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import i18n from '@/i18n';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const Stars = ({ value, size = 14, onPick = null }) => (
  <span className="inline-flex items-center gap-0.5">
    {[1, 2, 3, 4, 5].map((n) => (
      <Star
        key={n}
        size={size}
        onClick={onPick ? () => onPick(n) : undefined}
        data-testid={onPick ? `review-star-${n}` : undefined}
        className={`${n <= Math.round(value || 0) ? 'text-[#D9B35A] fill-[#D9B35A]' : 'text-white/25'} ${onPick ? 'cursor-pointer hover:scale-110 transition-transform' : ''}`}
      />
    ))}
  </span>
);

export const ProductReviewsModal = ({ product, onClose }) => {
  const [data, setData] = useState(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/api/v2/catalog/products/${product.id}/reviews`, { credentials: 'include' });
      if (r.ok) setData(await r.json());
    } catch { /* noop */ }
  }, [product.id]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (!rating) return toast.error(i18n.t('catalog.avis_note_requise', 'Sélectionnez une note (1 à 5 étoiles)'));
    setSending(true);
    try {
      const r = await fetch(`${API_URL}/api/v2/catalog/products/${product.id}/reviews`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating, comment }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(i18n.t('catalog.avis_publie', 'Votre avis a été publié'));
      setRating(0); setComment('');
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSending(false);
    }
  };

  const remove = async (reviewId) => {
    try {
      const r = await fetch(`${API_URL}/api/v2/catalog/reviews/${reviewId}`, { method: 'DELETE', credentials: 'include' });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(i18n.t('catalog.avis_supprime', 'Avis supprimé'));
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" data-testid="product-reviews-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Star className="w-5 h-5 text-[#D9B35A]" /> {product.name}
          </DialogTitle>
          <DialogDescription>
            {data?.count
              ? <span className="inline-flex items-center gap-2"><Stars value={data.avg} /> {data.avg}/5 · {data.count} {i18n.t('catalog.avis', 'avis')}</span>
              : i18n.t('catalog.aucun_avis', 'Aucun avis pour le moment — soyez le premier !')}
          </DialogDescription>
        </DialogHeader>

        {/* Formulaire */}
        {data?.can_review ? (
          <div className="space-y-3 p-3 rounded-lg border border-gray-200" data-testid="review-form">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium">{i18n.t('catalog.votre_note', 'Votre note')} :</span>
              <Stars value={rating} size={22} onPick={setRating} />
            </div>
            <Textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={i18n.t('catalog.avis_placeholder', 'Partagez votre expérience avec ce produit (optionnel)…')}
              rows={2}
              maxLength={1000}
              data-testid="review-comment-input"
            />
            <Button onClick={submit} disabled={sending} size="sm"
              className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black" data-testid="review-submit-btn">
              {sending ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Send className="w-4 h-4 mr-1" />}
              {i18n.t('catalog.publier_avis', 'Publier mon avis')}
            </Button>
          </div>
        ) : data && (
          <p className="text-sm text-white/60" data-testid="review-login-notice">
            {i18n.t('catalog.avis_connexion', 'Connectez-vous avec votre compte adhérent pour donner votre avis.')}
          </p>
        )}

        {/* Liste */}
        <div className="space-y-3" data-testid="reviews-list">
          {(data?.reviews || []).map((r) => (
            <div key={r.id} className="p-3 rounded-lg border border-gray-200" data-testid={`review-${r.id}`}>
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Stars value={r.rating} />
                  <span className="text-sm font-semibold">{r.user_name}</span>
                  <span className="text-xs opacity-60">{new Date(r.created_at).toLocaleDateString(i18n.language)}</span>
                </div>
                {(r.mine || data?.is_admin) && (
                  <button type="button" onClick={() => remove(r.id)} title={i18n.t('catalog.supprimer', 'Supprimer')}
                    className="text-red-400 hover:text-red-500" data-testid={`review-delete-${r.id}`}>
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
              {r.comment && <p className="text-sm mt-1 opacity-80">{r.comment}</p>}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
};
