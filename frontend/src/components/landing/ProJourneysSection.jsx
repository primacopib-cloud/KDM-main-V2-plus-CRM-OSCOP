import { Link } from 'react-router-dom';
import { ShoppingCart, Factory, TrendingUp, Ship, ArrowRight } from 'lucide-react';

const JOURNEYS = [
  {
    icon: ShoppingCart, color: '#D9B35A', title: 'Acheteurs professionnels',
    desc: "Déposez vos besoins d'achat, comparez les offres des deux circuits et commandez au tarif professionnel HT.",
    to: '/espace-acheteur', cta: 'Acheter', testid: 'journey-acheter',
  },
  {
    icon: Factory, color: '#8CC63E', title: 'Fournisseurs référencés',
    desc: "Rejoignez le référencement coopératif : vendez en direct ou via l'achat-revente O'SCOP selon l'offre.",
    to: '/adhesion-vendeur', cta: 'Devenir fournisseur', testid: 'journey-fournisseurs',
  },
  {
    icon: TrendingUp, color: '#B37BE8', title: 'Investisseurs & financeurs',
    desc: "Financez des opérations réelles d'achat-revente en euros, tranche marchandises ou tranche logistique.",
    to: '/espace-investisseur', cta: 'Financer', testid: 'journey-financer',
  },
  {
    icon: Ship, color: '#5AA7D9', title: "LOGI'SCOP",
    desc: "Enlèvement, groupage, fret maritime ou aérien, douane, stockage et dernier kilomètre multi-territoires.",
    to: '/calculateur-fret', cta: 'Organiser la logistique', testid: 'journey-logiscop',
  },
];

export const ProJourneysSection = () => (
  <section className="py-8 px-5" data-testid="pro-journeys">
    <div className="max-w-[1160px] mx-auto">
      <div className="section-title mb-5">
        <div>
          <h2 className="text-[24px] font-bold tracking-tight m-0">Quatre parcours professionnels</h2>
          <p className="text-white/70 text-sm mt-1 m-0">Acheter, vendre, financer et organiser la logistique — dans un cadre coopératif unique.</p>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {JOURNEYS.map((j) => (
          <Link key={j.testid} to={j.to} data-testid={j.testid}
            className="glass-panel-soft rounded-[18px] p-5 flex flex-col gap-3 group hover:border-[#D9B35A]/40 transition-colors border border-transparent">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${j.color}22`, border: `1px solid ${j.color}55` }}>
              <j.icon className="w-5 h-5" style={{ color: j.color }} />
            </div>
            <h3 className="text-base font-bold text-white m-0">{j.title}</h3>
            <p className="text-white/70 text-[13px] m-0 flex-1">{j.desc}</p>
            <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold" style={{ color: j.color }}>
              {j.cta} <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </Link>
        ))}
      </div>
    </div>
  </section>
);
