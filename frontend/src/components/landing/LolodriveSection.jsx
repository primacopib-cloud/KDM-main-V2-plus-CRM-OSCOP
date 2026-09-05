import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ShoppingBasket, MapPin, ArrowRight } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const LolodriveSection = () => {
  const [relayCount, setRelayCount] = useState(null);
  const [territories, setTerritories] = useState([]);
  useEffect(() => {
    lolodriveAPI.listLoloPoints({}).then((p) => setRelayCount((p.points || []).length)).catch(() => {});
    lolodriveAPI.listTerritories().then((t) => setTerritories(t.territories || t || [])).catch(() => {});
  }, []);
  return (
    <section className="py-8 px-5" data-testid="lolodrive-section">
      <div className="max-w-[1160px] mx-auto">
        <div className="rounded-[22px] p-7"
          style={{ background: 'linear-gradient(135deg, rgba(140,198,62,0.14), rgba(255,255,255,0.02))', border: '1px solid rgba(140,198,62,0.35)' }}>
          <div className="badge-status mb-3" style={{ borderColor: 'rgba(140,198,62,0.5)' }}>
            <span className="dot" style={{ background: '#8CC63E' }}></span>
            PARCOURS PARTICULIERS MAINTENU
          </div>
          <h2 className="text-[26px] font-bold tracking-tight mt-1 mb-2.5">
            Pour les particuliers, <span className="text-[#8CC63E]">LOLODRIVE</span> reste l'accès dédié.
          </h2>
          <p className="text-white/75 text-base max-w-[70ch] m-0">
            Les particuliers conservent un univers séparé pour consulter les produits de leur territoire,
            choisir un relais coopératif, retirer leurs commandes ou bénéficier d'une livraison locale.
          </p>
          <div className="flex gap-3 flex-wrap mt-5 items-center">
            <Link to="/particuliers" data-testid="lolo-cta-espace">
              <button className="inline-flex items-center gap-2 rounded-[14px] px-4 py-3 text-sm font-bold text-[#1F2A12]"
                style={{ background: '#8CC63E' }}>
                <ShoppingBasket className="w-4 h-4" /> Accéder à l'espace particuliers
              </button>
            </Link>
            <Link to="/points-relais" data-testid="lolo-cta-relais"
              className="btn-ghost inline-flex items-center gap-2 rounded-[14px] px-4 py-3 text-sm font-semibold">
              <MapPin className="w-4 h-4" /> Trouver un relais LOLODRIVE <ArrowRight className="w-3.5 h-3.5" />
            </Link>
            {relayCount != null && (
              <span className="text-white/70 text-sm" data-testid="lolo-relay-count">
                <strong className="text-[#8CC63E]">{relayCount}</strong> relais actif{relayCount > 1 ? 's' : ''}
                {territories.length > 0 && <> · {territories.length} territoires</>}
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
