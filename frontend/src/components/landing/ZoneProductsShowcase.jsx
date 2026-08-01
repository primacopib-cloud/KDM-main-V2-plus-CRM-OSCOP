import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, ArrowRight, Heart, Package, ChevronLeft, ChevronRight } from 'lucide-react';
import i18n from '@/i18n';
import { tData } from '@/i18n/tData';
import { TerritoryMap } from './TerritoryMap';
import { trackCta } from '../../services/ctaTracking';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Aperçu des produits phares par territoire sur la page d'accueil (visiteurs)
export const ZoneProductsShowcase = () => {
  const [zone, setZone] = useState('');
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const trackRef = useRef(null);
  const offsetRef = useRef(0);
  const pausedRef = useRef(false);

  // Défilement automatique continu (boucle infinie), pause au survol ou pendant une navigation manuelle
  useEffect(() => {
    let raf;
    const step = () => {
      const el = trackRef.current;
      if (el && !pausedRef.current) {
        const half = el.scrollWidth / 2;
        if (half > 0) {
          offsetRef.current = (offsetRef.current + 0.6) % half;
          el.style.transform = `translateX(-${offsetRef.current}px)`;
        }
      }
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [products]);

  // Flèches : saut d'une carte (210 px + 16 px de gap) avec transition douce
  const shift = (dir) => {
    const el = trackRef.current;
    if (!el) return;
    const half = el.scrollWidth / 2;
    pausedRef.current = true;
    offsetRef.current = (((offsetRef.current + dir * 226) % half) + half) % half;
    el.style.transition = 'transform 0.35s ease';
    el.style.transform = `translateX(-${offsetRef.current}px)`;
    setTimeout(() => {
      if (trackRef.current) trackRef.current.style.transition = '';
      pausedRef.current = false;
    }, 400);
  };

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/api/v2/catalog/products?sort=rating&limit=12${zone ? `&zone_code=${zone}` : ''}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setProducts(Array.isArray(d) ? d : []))
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [zone]);

  return (
    <section className="py-10 px-5" data-testid="zone-showcase-section">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-2 mb-1">
          <MapPin className="w-5 h-5" style={{ color: '#D9B35A' }} />
          <h2 className="text-lg md:text-lg font-bold" style={{ color: '#F7F2E9' }}>
            {i18n.t('landing.zone_showcase_title', 'Disponible sur votre territoire')}
          </h2>
        </div>
        <p className="text-sm mb-5" style={{ color: 'rgba(247,242,233,0.6)' }}>
          {i18n.t('landing.zone_showcase_sub', 'Un aperçu des produits phares déjà référencés dans chaque zone de la coopérative.')}
        </p>

        {/* Carte interactive des Outre-mer */}
        <TerritoryMap zone={zone} onSelect={setZone} showAll />

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-44 rounded-2xl animate-pulse bg-white/[0.05]" />
            ))}
          </div>
        ) : products.length === 0 ? (
          <p className="text-sm py-8 text-center" style={{ color: 'rgba(247,242,233,0.5)' }} data-testid="showcase-empty">
            {i18n.t('landing.zone_showcase_empty', 'Les premiers produits de cette zone arrivent bientôt — devenez pionnier de votre territoire !')}
          </p>
        ) : (
          <div className="relative" data-testid="showcase-products"
            onMouseEnter={() => { pausedRef.current = true; }}
            onMouseLeave={() => { pausedRef.current = false; }}>
            <div className="overflow-hidden"
              style={{ maskImage: 'linear-gradient(90deg, transparent, black 6%, black 94%, transparent)', WebkitMaskImage: 'linear-gradient(90deg, transparent, black 6%, black 94%, transparent)' }}>
              <div ref={trackRef} className="flex gap-4" style={{ width: 'max-content', willChange: 'transform' }}>
              {[...products, ...products].map((p, i) => (
                <Link
                  key={`${p.id}-${i}`}
                  to={`/catalogue?produit=${p.id}`}
                  data-testid={i < products.length ? `showcase-product-${p.sku}` : undefined}
                  className="group w-[210px] shrink-0 rounded-2xl overflow-hidden border border-white/[0.08] bg-white/[0.03] hover:border-[#D9B35A]/40 transition-colors"
                >
                  <div className="relative h-28 bg-white/[0.04] flex items-center justify-center overflow-hidden">
                    {p.image_url ? (
                      <img src={p.image_url} alt={p.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                    ) : (
                      <Package className="w-8 h-8 text-white/20" />
                    )}
                    {p.rating_avg >= 4.5 && (
                      <span className="absolute top-2 left-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold text-white"
                        style={{ background: 'linear-gradient(90deg, #C0392B, #E74C3C)' }}>
                        <Heart size={9} fill="currentColor" /> {i18n.t('catalog.coup_de_coeur_court', 'Coup de cœur')}
                      </span>
                    )}
                  </div>
                  <div className="p-3">
                    <p className="text-sm font-semibold truncate" style={{ color: '#F7F2E9' }}>{tData(p.name) || p.name}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'rgba(247,242,233,0.45)' }}>{p.sku}</p>
                    {(p.price_ht_cents ?? p.teaser_price_ht_cents) != null && (
                      <p className="text-sm font-bold mt-1" style={{ color: '#D9B35A' }}
                        data-testid={i < products.length ? `showcase-price-${p.sku}` : undefined}>
                        {p.price_ht_cents == null && <span className="text-[10px] font-normal" style={{ color: 'rgba(247,242,233,0.5)' }}>{i18n.t('landing.a_partir_de', 'à partir de')} </span>}
                        {(((p.price_ht_cents ?? p.teaser_price_ht_cents)) / 100).toFixed(2)} € <span className="text-[10px] font-normal" style={{ color: 'rgba(247,242,233,0.5)' }}>HT</span>
                      </p>
                    )}
                  </div>
                </Link>
              ))}
            </div>
            </div>
            <button type="button" onClick={() => shift(-1)} data-testid="showcase-prev-btn"
              aria-label="Produits précédents"
              className="absolute left-1 top-1/2 -translate-y-1/2 z-10 w-9 h-9 rounded-full flex items-center justify-center bg-black/55 backdrop-blur-sm border border-[#D9B35A]/45 text-[#D9B35A] hover:bg-[#D9B35A] hover:text-black transition-colors shadow-lg">
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button type="button" onClick={() => shift(1)} data-testid="showcase-next-btn"
              aria-label="Produits suivants"
              className="absolute right-1 top-1/2 -translate-y-1/2 z-10 w-9 h-9 rounded-full flex items-center justify-center bg-black/55 backdrop-blur-sm border border-[#D9B35A]/45 text-[#D9B35A] hover:bg-[#D9B35A] hover:text-black transition-colors shadow-lg">
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/catalogue" data-testid="showcase-catalog-cta" onClick={() => trackCta('voir_catalogue')}
            className="btn-ghost h-10 px-5 rounded-lg inline-flex items-center gap-2 text-sm">
            {i18n.t('landing.voir_catalogue', 'Voir tout le catalogue')} <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/tarifs" data-testid="showcase-join-cta" onClick={() => trackCta('adherer_centrale')}
            className="inline-flex items-center gap-2 h-10 px-5 rounded-lg text-sm font-bold"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            {i18n.t('landing.adherer_a_la_centrale', 'Adhérer à la Centrale')}
          </Link>
        </div>
      </div>
    </section>
  );
};
