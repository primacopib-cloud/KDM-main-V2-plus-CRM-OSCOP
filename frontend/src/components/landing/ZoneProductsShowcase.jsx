import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, ArrowRight, Heart, Package } from 'lucide-react';
import i18n from '@/i18n';
import { tData } from '@/i18n/tData';
import { TerritoryMap } from './TerritoryMap';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Aperçu des produits phares par territoire sur la page d'accueil (visiteurs)
export const ZoneProductsShowcase = () => {
  const [zone, setZone] = useState('GUADELOUPE');
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/api/v2/catalog/products?zone_code=${zone}&sort=rating&limit=4`)
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
        <TerritoryMap zone={zone} onSelect={setZone} />

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
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="showcase-products">
            {products.map((p) => (
              <Link
                key={p.id}
                to={`/catalogue?produit=${p.id}`}
                data-testid={`showcase-product-${p.sku}`}
                className="group rounded-2xl overflow-hidden border border-white/[0.08] bg-white/[0.03] hover:border-[#D9B35A]/40 transition-all"
              >
                <div className="relative h-28 bg-white/[0.04] flex items-center justify-center overflow-hidden">
                  {p.image_url ? (
                    <img src={p.image_url} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
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
                </div>
              </Link>
            ))}
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/catalogue" data-testid="showcase-catalog-cta"
            className="btn-ghost h-10 px-5 rounded-lg inline-flex items-center gap-2 text-sm">
            {i18n.t('landing.voir_catalogue', 'Voir tout le catalogue')} <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/tarifs" data-testid="showcase-join-cta"
            className="inline-flex items-center gap-2 h-10 px-5 rounded-lg text-sm font-bold"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            {i18n.t('landing.adherer_a_la_centrale', 'Adhérer à la Centrale')}
          </Link>
        </div>
      </div>
    </section>
  );
};
