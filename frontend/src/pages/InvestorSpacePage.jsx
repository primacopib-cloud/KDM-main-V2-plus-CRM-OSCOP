import { Link } from 'react-router-dom';
import { TrendingUp, Ticket, Euro, Truck, ShieldAlert } from 'lucide-react';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { InvestorLiveDashboard } from '../components/investor/InvestorLiveDashboard';
import { FinancingOpportunities } from '../components/investor/FinancingOpportunities';
import { MessagesNavLink } from '../components/MessagesNavLink';
import { InvestorDataroom } from '../components/investor/InvestorDataroom';
import { InvestorApplyForm } from '../components/investor/InvestorApplyForm';

const blocks = [
  {
    icon: Euro,
    title: 'Abonnement O\u2019SCOP',
    text: "Abonnement mensuel de services coopératifs : montant, factures et statut, distincts de tout investissement.",
  },
  {
    icon: Ticket,
    title: "CREDI'SCOP-I",
    text: "Compteur d'unités de services internes : unités allouées, consommées et expirées. Aucune valeur en euros, non convertibles, non transférables, jamais un moyen de paiement des produits ou des fournisseurs.",
  },
  {
    icon: TrendingUp,
    title: 'Investissements réels',
    text: "Montants réellement investis en monnaie ayant cours légal : instruments juridiques, opérations financées, Bons d'Engagement signés et remboursements.",
  },
  {
    icon: Truck,
    title: "Financement logistique LOGI'SCOP",
    text: "Tranche logistique distincte de la tranche marchandises : montant approuvé, décaissements externes, affectations internes LOGI'SCOP et solde disponible.",
  },
];

export default function InvestorSpacePage() {
  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}>
      <Header />
      <main className="max-w-[1000px] mx-auto px-5 py-14" data-testid="investor-space-page">
        <div className="flex items-center gap-3 flex-wrap mb-3">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">Espace investisseurs</h1>
          <MessagesNavLink withLabel />
        </div>
        <p className="text-white/70 max-w-[70ch] mb-8">
          L'espace investisseur O'SCOP sépare strictement l'abonnement, le compteur CREDI'SCOP-I, les
          investissements réels et le financement logistique LOGI'SCOP.
        </p>
        <InvestorLiveDashboard />
        <InvestorDataroom />
        <FinancingOpportunities />
        <InvestorApplyForm />
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          {blocks.map((b) => (
            <div key={b.title} className="glass-panel-soft rounded-[22px] p-5">
              <b.icon className="w-6 h-6 text-[#D9B35A] mb-2" />
              <h2 className="text-lg font-bold mb-1.5">{b.title}</h2>
              <p className="text-white/65 text-sm">{b.text}</p>
            </div>
          ))}
        </div>
        <div className="rounded-[18px] p-4 border border-amber-400/30 bg-amber-500/10 flex gap-3" data-testid="crediscop-legal-notice">
          <ShieldAlert className="w-5 h-5 text-amber-300 shrink-0 mt-0.5" />
          <p className="text-amber-100/90 text-sm">
            Les CREDI'SCOP-I sont des unités internes de services. Ils ne constituent ni un solde financier,
            ni le montant investi, ni un moyen de paiement du fournisseur. Chaque investissement réel fait
            l'objet d'un Bon d'Engagement et d'un paiement distinct en monnaie ayant cours légal.
          </p>
        </div>
        <p className="text-white/50 text-sm mt-8">
          L'ouverture des comptes investisseurs est réalisée par l'équipe O'SCOP.{' '}
          <Link to="/contact" className="text-[#D9B35A] underline">Contactez-nous</Link> pour préparer votre dossier.
        </p>
      </main>
      <Footer />
    </div>
  );
}
