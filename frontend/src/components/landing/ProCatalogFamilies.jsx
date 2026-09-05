import { Link } from 'react-router-dom';
import { UtensilsCrossed, HardHat, Sprout, Store, ArrowRight } from 'lucide-react';

const FAMILIES = [
  { icon: UtensilsCrossed, label: 'Alimentaire & épicerie', color: '#D9B35A' },
  { icon: HardHat, label: 'BTP & équipements', color: '#5AA7D9' },
  { icon: Sprout, label: 'Agriculture & végétal', color: '#8CC63E' },
  { icon: Store, label: 'Commerce général, hygiène & bazar', color: '#B37BE8' },
];

export const ProCatalogFamilies = () => (
  <section className="py-8 px-5" data-testid="pro-catalog-families">
    <div className="max-w-[1160px] mx-auto">
      <div className="section-title mb-5 flex items-end justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-[24px] font-bold tracking-tight m-0">Catalogue professionnel</h2>
          <p className="text-white/70 text-sm mt-1 m-0">
            Chaque fiche affiche le vendeur juridique, l'émetteur de la facture, le territoire, la disponibilité,
            la logistique, l'éligibilité au financement et le prix HT.
          </p>
        </div>
        <Link to="/catalogue" className="btn-ghost inline-flex items-center gap-2 rounded-[12px] px-4 py-2 text-sm font-semibold" data-testid="catalog-families-cta">
          Ouvrir le catalogue Pro <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {FAMILIES.map((f) => (
          <Link key={f.label} to="/catalogue"
            className="glass-panel-soft rounded-[18px] p-5 flex items-center gap-3 hover:border-[#D9B35A]/40 transition-colors border border-transparent"
            data-testid={`family-${f.label.slice(0, 4).toLowerCase()}`}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${f.color}22`, border: `1px solid ${f.color}55` }}>
              <f.icon className="w-5 h-5" style={{ color: f.color }} />
            </div>
            <span className="text-white/90 text-sm font-semibold">{f.label}</span>
          </Link>
        ))}
      </div>
    </div>
  </section>
);
