import { useEffect, useState } from 'react';
import { Star, Quote } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const Stars = ({ n }) => (
  <span className="inline-flex gap-0.5">
    {[1, 2, 3, 4, 5].map((i) => (
      <Star key={i} className={`w-3.5 h-3.5 ${i <= n ? 'fill-[#D9B35A] text-[#D9B35A]' : 'text-white/20'}`} />
    ))}
  </span>
);

export const VitrineReviews = () => {
  const [reviews, setReviews] = useState([]);

  useEffect(() => {
    lolodriveAPI.relayReviewsLatest(6)
      .then((d) => setReviews((d.reviews || []).filter((r) => r.comment)))
      .catch(() => {});
  }, []);

  if (!reviews.length) return null;
  return (
    <section className="mt-12" data-testid="vitrine-reviews">
      <p className="text-[11px] uppercase tracking-[0.2em] text-[#D9B35A] font-bold mb-1">Ils utilisent déjà le PASS</p>
      <h2 className="text-base md:text-lg font-bold text-white mb-4">Les derniers avis des titulaires dans les relais LOLODRIVE</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {reviews.map((r) => (
          <div key={r.id} className="rounded-2xl p-4 border border-[#D9B35A]/25 bg-white/[0.03]"
            data-testid={`vitrine-review-${r.id}`}>
            <Quote className="w-4 h-4 text-[#D9B35A]/60 mb-1" />
            <p className="text-sm text-white/85 leading-relaxed">« {r.comment} »</p>
            <div className="mt-3 flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-xs font-bold text-white truncate">{r.author}</p>
                <p className="text-[10px] text-white/40 truncate">{r.point_name}{r.city ? ` · ${r.city}` : ''}</p>
              </div>
              <Stars n={r.rating} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
