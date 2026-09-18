import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, BellRing, Clock, Share2, Star, Store, Users } from 'lucide-react';
import { toast } from 'sonner';
import { Flag } from '../components/Flag';
import { AuctionCard } from '../components/auctions/AuctionCard';
import { apiCall, getSessionToken } from '../services/http';

// Mini page publique d'un POP'S : lots en cours, avis, bouton suivre
export default function PopsShopPage() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [follows, setFollows] = useState(null);
  const isLogged = Boolean(getSessionToken());

  useEffect(() => {
    apiCall(`/detaillant/shops/public/${userId}`).then(setData).catch(() => setError(true));
    if (isLogged) apiCall('/auctions/shops/follows').then((d) => setFollows(d.follows || [])).catch(() => {});
  }, [userId, isLogged]);

  const toggleFollow = async () => {
    try {
      const r = await apiCall(`/auctions/shops/${userId}/follow`, { method: 'POST' });
      setFollows((f) => (r.following ? [...(f || []), userId] : (f || []).filter((x) => x !== userId)));
      setData((d) => ({ ...d, followers: d.followers + (r.following ? 1 : -1) }));
      toast.success(r.following ? "✓ POP'S suivi — cloche + email à chaque nouveau lot" : 'Suivi retiré');
    } catch (e) { toast.error(e.message); }
  };

  if (error) return <div className="min-h-screen bg-[#1F0A33] text-white flex items-center justify-center text-sm text-white/60" data-testid="pops-shop-notfound">Boutique POP'S introuvable</div>;
  if (!data) return <div className="min-h-screen bg-[#1F0A33]" />;
  const { shop, lots, reviews, sold, followers } = data;
  const following = follows?.includes(userId);

  return (
    <div className="min-h-screen bg-[#1F0A33] text-white" data-testid="pops-shop-page">
      <div className="max-w-4xl mx-auto px-5 py-10">
        <button type="button" onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/detaillant'))}
          className="inline-flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80" data-testid="pops-shop-back">
          <ArrowLeft className="w-3.5 h-3.5" /> Retour
        </button>
        <div className="mt-4 rounded-2xl border border-emerald-400/25 bg-emerald-500/[0.05] p-5">
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black bg-gradient-to-r from-emerald-500 to-emerald-700 text-white tracking-wide">POP'S</span>
            {shop.gold && (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-black bg-gradient-to-r from-[#FFD700] to-[#D9B35A] text-[#1F0A33]"
                data-testid="pops-shop-gold-badge">🏆 POP'S d'Or — n°1 du palmarès</span>
            )}
            <h1 className="text-2xl sm:text-3xl font-black flex items-center gap-2" data-testid="pops-shop-name">
              <Flag code={shop.country_code} className="w-6 h-auto rounded-[3px] inline-block" /> {shop.company_name}
            </h1>
            {shop.rating_avg && (
              <span className="text-sm font-bold text-amber-300" data-testid="pops-shop-rating">★ {Number(shop.rating_avg).toFixed(1)} ({shop.rating_count})</span>
            )}
          </div>
          <p className="text-xs text-white/50 mt-1">{shop.locality} — Partenaire d'Offres de Produits Solidaires, vendeur éphémère en salle COOP'ACT</p>
          <div className="flex flex-wrap items-center gap-3 mt-3">
            <span className="inline-flex items-center gap-1.5 text-xs text-white/60" data-testid="pops-shop-followers">
              <Users className="w-3.5 h-3.5" /> <b className="text-white/90">{followers}</b> membre{followers > 1 ? 's' : ''} suivent ce POP'S
            </span>
            {isLogged ? (
              <button onClick={toggleFollow} data-testid="pops-shop-follow-btn"
                className={`inline-flex items-center gap-1.5 px-4 h-8 rounded-full text-xs font-bold border transition-colors ${
                  following ? 'text-emerald-300 border-emerald-400/50 bg-emerald-500/15'
                    : 'text-white/70 border-white/25 hover:border-emerald-400/50 hover:text-emerald-300'}`}>
                <BellRing className="w-3.5 h-3.5" /> {following ? 'Suivi ✓' : 'Suivre ce POP\'S'}
              </button>
            ) : (
              <Link to="/connexion" data-testid="pops-shop-login-to-follow"
                className="inline-flex items-center gap-1.5 px-4 h-8 rounded-full text-xs font-bold text-white/70 border border-white/25 hover:border-emerald-400/50 hover:text-emerald-300">
                <BellRing className="w-3.5 h-3.5" /> Se connecter pour suivre
              </Link>
            )}
            <a href={`https://wa.me/?text=${encodeURIComponent(`Découvrez la boutique POP'S ${shop.company_name} en salle COOP'ACT — des lots à prix descendant ! ${window.location.origin}/api/detaillant/shops/share/${userId}`)}`}
              target="_blank" rel="noopener noreferrer" data-testid="pops-shop-share-btn"
              title="Partager cette boutique sur WhatsApp"
              className="inline-flex items-center gap-1.5 px-4 h-8 rounded-full text-xs font-bold text-white bg-[#25D366] hover:brightness-110 transition-all">
              <Share2 className="w-3.5 h-3.5" /> Partager
            </a>
          </div>
          {(shop.pickup_slots || []).length > 0 && (
            <p className="text-[11px] text-white/45 mt-2 inline-flex items-center gap-1.5">
              <Clock className="w-3 h-3" /> Enlèvements : {shop.pickup_slots.join(' · ')}
            </p>
          )}
        </div>

        <h2 className="text-base md:text-lg font-bold text-[#E9CF8E] mt-8 flex items-center gap-2">
          <Store className="w-4 h-4" /> Lots en salle COOP'ACT ({lots.length})
        </h2>
        {lots.length === 0 ? (
          <p className="text-xs text-white/40 mt-3" data-testid="pops-shop-no-lots">Aucun lot en cours — suivez ce POP'S pour être alerté du prochain dépôt.</p>
        ) : (
          <div className="grid gap-3 mt-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }} data-testid="pops-shop-lots">
            {lots.map((a) => <AuctionCard key={a.id} auction={a} canBid={false} />)}
          </div>
        )}

        {(sold || []).length > 0 && (
          <>
            <h2 className="text-base md:text-lg font-bold text-[#E9CF8E] mt-10 flex items-center gap-2">
              🏆 Derniers lots vendus ({sold.length})
            </h2>
            <div className="space-y-2 mt-4" data-testid="pops-shop-sold">
              {sold.map((s) => (
                <div key={s.reference} className="flex items-center justify-between gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2"
                  data-testid={`pops-sold-${s.reference}`}>
                  <div className="min-w-0">
                    <p className="text-xs font-bold truncate">{s.title}</p>
                    <p className="text-[10px] text-white/40">{s.won_at ? new Date(s.won_at).toLocaleDateString('fr-FR') : ''} · {s.reference}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs font-bold text-[#E9CF8E]">{s.price_eur != null ? `${Number(s.price_eur).toFixed(2)} €` : '—'}</p>
                    {s.picked_up && <p className="text-[9px] text-emerald-300">✓ retiré</p>}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        <h2 className="text-base md:text-lg font-bold text-[#E9CF8E] mt-10 flex items-center gap-2">
          <Star className="w-4 h-4" /> Avis des Coop'acteurs ({reviews.length})
        </h2>
        {reviews.length === 0 ? (
          <p className="text-xs text-white/40 mt-3">Pas encore d'avis — les gagnants notent la boutique après l'enlèvement.</p>
        ) : (
          <div className="space-y-3 mt-4" data-testid="pops-shop-reviews">
            {reviews.map((r) => (
              <div key={r.created_at} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <div className="flex items-center gap-2">
                  <span className="text-amber-300 text-xs font-bold">{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span>
                  <span className="text-[10px] text-white/35">{new Date(r.created_at).toLocaleDateString('fr-FR')}</span>
                </div>
                {r.comment && <p className="text-xs text-white/65 mt-1 italic">« {r.comment} »</p>}
                {r.reply && (
                  <p className="text-xs text-emerald-300/85 mt-1.5">↳ Réponse de la boutique : {r.reply}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
