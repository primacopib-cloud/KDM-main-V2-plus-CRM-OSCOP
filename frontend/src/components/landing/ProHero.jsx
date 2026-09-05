import { Link } from 'react-router-dom';
import { ArrowRight, FileSearch, TrendingUp, Info } from 'lucide-react';
import { trackCta } from '../../services/ctaTracking';

const FLOW_STEPS = [
  'Commande client confirmée',
  "Fournisseur facture O'SCOP",
  'Financeur paie le fournisseur',
  "LOGI'SCOP pilote le transport",
  "O'SCOP revend et facture le client",
  'Les encaissements remboursent les sommes dues — le solde constitue la marge O\'SCOP',
];

export const ProHero = () => (
  <section className="pt-20 pb-8 px-5" data-testid="pro-hero">
    <div className="max-w-[1160px] mx-auto">
      <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-6 items-stretch">
        <div className="glass-panel card-glow rounded-[26px] p-7">
          <div className="badge-status mb-3.5">
            <span className="dot pulse-glow"></span>
            CENTRALE PROFESSIONNELLE MULTI-TERRITOIRES
          </div>
          <h1 className="text-[34px] sm:text-[38px] leading-[1.08] font-bold tracking-tight my-2.5" data-testid="hero-title">
            Vos achats, votre financement et votre logistique, <span className="text-[#D9B35A]">dans un seul parcours.</span>
          </h1>
          <p className="text-white/75 text-base max-w-[62ch] m-0">
            O'SCOP peut acheter les marchandises auprès du fournisseur, les revendre et facturer le client
            professionnel. Selon l'offre, un partenaire référencé peut également demeurer le vendeur direct.
            Le circuit, le prix, la logistique et le bénéficiaire du paiement sont définis avant l'engagement.
          </p>
          <div className="flex gap-3 flex-wrap mt-5">
            <Link to="/espace-acheteur" onClick={() => trackCta('hero_besoin_achat')}>
              <button className="force-white inline-flex items-center gap-2.5 rounded-[14px] px-4 py-3 text-sm font-semibold text-white shadow-lg"
                style={{ background: 'linear-gradient(135deg, #5B2E8C 0%, #2A1045 100%)' }}
                data-testid="hero-cta-besoin-achat">
                <FileSearch className="w-4 h-4" /> Déposer un besoin d'achat
              </button>
            </Link>
            <Link to="/catalogue" onClick={() => trackCta('hero_catalogue_pro')}
              className="btn-ghost inline-flex items-center gap-2 rounded-[14px] px-4 py-3 text-sm font-semibold"
              data-testid="hero-cta-catalogue-pro">
              Explorer le catalogue Pro <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/espace-investisseur" onClick={() => trackCta('hero_financer')}
              className="btn-ghost inline-flex items-center gap-2 rounded-[14px] px-4 py-3 text-sm font-semibold"
              data-testid="hero-cta-financer">
              <TrendingUp className="w-4 h-4" /> Financer une opération
            </Link>
          </div>
        </div>

        <div className="glass-panel-soft rounded-[26px] p-5 flex flex-col gap-3 hero-enter-delayed"
          style={{ boxShadow: '0 16px 50px rgba(0,0,0,0.35)' }} data-testid="hero-flow-example">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-[#D9B35A]" />
            <h3 className="text-sm tracking-wider uppercase text-white/75 font-semibold m-0">Exemple illustratif d'une opération</h3>
          </div>
          <ol className="grid gap-2 m-0 p-0 list-none">
            {FLOW_STEPS.map((step, i) => (
              <li key={step} className="flex gap-2.5 items-start p-2.5 px-3 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
                <span className="on-gold shrink-0 w-5 h-5 rounded-full bg-[#D9B35A] text-[11px] font-bold flex items-center justify-center mt-0.5">{i + 1}</span>
                <span className="text-white/85 text-sm">{step}</span>
              </li>
            ))}
          </ol>
          <p className="text-[11px] text-white/55 italic m-0">
            Schéma illustratif du circuit type. Aucun montant présenté ne constitue une ligne disponible réelle.
          </p>
        </div>
      </div>
    </div>
  </section>
);
