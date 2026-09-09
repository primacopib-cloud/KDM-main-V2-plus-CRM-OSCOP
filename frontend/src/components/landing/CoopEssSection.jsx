import { Link } from 'react-router-dom';
import { Users, HeartHandshake, ArrowRight } from 'lucide-react';

export const CoopEssSection = () => (
  <>
    <section className="max-w-[820px] mx-auto px-5 text-center mb-14" data-testid="kdm-catalog-cta">
      <h2 className="font-display text-2xl mb-3">Explorez le catalogue LOLODRIVE</h2>
      <p className="text-white/60 text-sm mb-5 max-w-[56ch] mx-auto">
        Découvrez les lots ×3 à prix mini disponibles dans le LOLODRIVE de votre pays et de votre zone.
        Choisissez votre point LOLODRIVE, souscrivez au PASS et débloquez les prix membres.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <Link to="/catalogue-lolodrive" className="btn-gold h-11 px-6 rounded-lg inline-flex items-center gap-2 text-sm font-semibold" data-testid="kdm-cta-catalog-full">
          Accéder au catalogue <ArrowRight size={15} />
        </Link>
        <Link to="/pass" className="h-11 px-6 rounded-lg inline-flex items-center gap-2 text-sm font-semibold text-white border border-white/25 hover:bg-white/5" data-testid="kdm-cta-choose-pass">
          Choisir mon LOLODRIVE & souscrire au PASS
        </Link>
      </div>
    </section>

    <section className="max-w-[820px] mx-auto px-5 text-center mb-12" data-testid="kdm-coop-section">
      <HeartHandshake className="w-8 h-8 mx-auto mb-3 text-[#D9B35A]" />
      <h2 className="font-display text-2xl mb-3">Un cadre coopératif ESS</h2>
      <p className="text-white/70 text-sm">
        1 personne = 1 voix. Gouvernance partagée, marges plafonnées et bénéfices réinvestis
        au service du pouvoir d&apos;achat des territoires. En agrégeant les besoins des professionnels,
        KDMARCHÉ transforme le volume collectif en levier de négociation pour tous ses membres.
      </p>
      <div className="flex justify-center gap-3 mt-6">
        <Link to="/tarifs" className="btn-gold h-11 px-6 rounded-lg inline-flex items-center gap-2 text-sm font-semibold" data-testid="kdm-cta-pricing">
          <Users size={15} /> Devenir membre
        </Link>
      </div>
    </section>
  </>
);
