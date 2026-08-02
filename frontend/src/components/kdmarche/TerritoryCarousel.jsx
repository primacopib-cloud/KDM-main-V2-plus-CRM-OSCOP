import { useCallback, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight, MapPin, ArrowRight } from 'lucide-react';
import { TERRITORIES } from '../../data/territories';

const TOTAL = TERRITORIES.length;

// Carrousel des territoires de la coopérative — page /kdmarche (#territoires)
export const TerritoryCarousel = () => {
  const trackRef = useRef(null);
  const [index, setIndex] = useState(0);

  const scrollToIndex = useCallback((i) => {
    const track = trackRef.current;
    if (!track) return;
    const next = Math.max(0, Math.min(TOTAL - 1, i));
    const card = track.children[next];
    if (card) track.scrollTo({ left: Math.min(card.offsetLeft - track.offsetLeft, track.scrollWidth - track.clientWidth), behavior: 'smooth' });
    setIndex(next);
  }, []);

  const onScroll = () => {
    const track = trackRef.current;
    if (!track || track.children.length === 0) return;
    const maxScroll = track.scrollWidth - track.clientWidth;
    if (maxScroll > 0 && track.scrollLeft >= maxScroll - 4) { setIndex(TOTAL - 1); return; }
    const step = track.children[1] ? track.children[1].offsetLeft - track.children[0].offsetLeft : track.clientWidth;
    setIndex(Math.max(0, Math.min(TOTAL - 1, Math.round(track.scrollLeft / step))));
  };

  const onKeyDown = (e) => {
    if (e.key === 'ArrowLeft') { e.preventDefault(); scrollToIndex(index - 1); }
    if (e.key === 'ArrowRight') { e.preventDefault(); scrollToIndex(index + 1); }
  };

  return (
    <section id="territoires" data-territory-carousel className="max-w-[1160px] mx-auto px-5 mb-14 scroll-mt-24"
      aria-roledescription="carrousel" aria-label="Territoires de la coopérative" data-testid="kdm-territories-section">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-[#8CC63E] mb-2 flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5" aria-hidden="true" /> Territoires
          </p>
          <h2 className="font-display text-2xl sm:text-3xl m-0">Disponible sur votre territoire</h2>
          <p className="text-white/60 text-sm mt-2 m-0 max-w-[58ch]">
            Un aperçu des produits phares déjà référencés dans chaque zone de la coopérative.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-white/60 font-mono tabular-nums" aria-live="polite" data-testid="territory-counter">
            {index + 1} / {TOTAL}
          </span>
          <button type="button" onClick={() => scrollToIndex(index - 1)} disabled={index === 0}
            aria-label="Territoire précédent" data-testid="territory-prev"
            className="w-9 h-9 rounded-full border border-white/20 flex items-center justify-center text-white/80 hover:border-[#8CC63E] hover:text-[#8CC63E] transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:border-white/20 disabled:hover:text-white/80">
            <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          </button>
          <button type="button" onClick={() => scrollToIndex(index + 1)} disabled={index === TOTAL - 1}
            aria-label="Territoire suivant" data-testid="territory-next"
            className="w-9 h-9 rounded-full border border-white/20 flex items-center justify-center text-white/80 hover:border-[#8CC63E] hover:text-[#8CC63E] transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:border-white/20 disabled:hover:text-white/80">
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </div>
      <div ref={trackRef} onScroll={onScroll} onKeyDown={onKeyDown} tabIndex={0} role="group"
        aria-label={`Liste des ${TOTAL} territoires, utilisez les flèches du clavier pour naviguer`}
        data-testid="territory-track"
        className="flex gap-4 overflow-x-auto snap-x snap-mandatory pb-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#8CC63E]/60 rounded-xl [&::-webkit-scrollbar]:hidden"
        style={{ scrollbarWidth: 'none' }}>
        {TERRITORIES.map((t, i) => (
          <article key={t.id} aria-roledescription="diapositive" aria-label={`${i + 1} sur ${TOTAL} : ${t.name}`}
            data-testid={`territory-card-${t.id}`}
            className="glass-panel-soft rounded-[20px] p-6 snap-start shrink-0 w-[86%] sm:w-[47%] lg:w-[31.5%] flex flex-col">
            <div className="flex items-center gap-3 mb-1">
              <span className="text-2xl" aria-hidden="true">{t.flag}</span>
              <h3 className="font-display text-xl m-0" style={{ color: t.color }}>{t.name}</h3>
            </div>
            <p className="text-xs text-white/55 mb-4">{t.tagline}</p>
            <p className="text-[10px] uppercase tracking-wider text-white/40 mb-2">Produits phares</p>
            <ul className="space-y-2 mb-5">
              {t.products.map((p) => (
                <li key={p} className="text-sm text-white/75 flex gap-2">
                  <span aria-hidden="true" style={{ color: t.color }}>•</span>{p}
                </li>
              ))}
            </ul>
            <Link to={`/catalogue?zone=${t.zoneCode}`} data-testid={`territory-link-${t.id}`}
              className="mt-auto inline-flex items-center gap-1.5 text-sm font-semibold hover:underline"
              style={{ color: t.color }}
              aria-label={`Voir les offres de la zone ${t.name}`}>
              Voir les offres de la zone <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
};
