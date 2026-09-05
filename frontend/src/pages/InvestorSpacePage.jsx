import { Link } from 'react-router-dom';
import { TrendingUp, Ticket, Euro, Truck, ShieldAlert } from 'lucide-react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { BreadcrumbPill } from '../components/Breadcrumb';
import { SpaceHeaderActions } from '../components/SpaceHeaderActions';
import { InvestorLiveDashboard } from '../components/investor/InvestorLiveDashboard';
import { FinancingOpportunities } from '../components/investor/FinancingOpportunities';
import { MessagesNavLink } from '../components/MessagesNavLink';
import { InvestorDataroom } from '../components/investor/InvestorDataroom';
import { InvestorApplyForm } from '../components/investor/InvestorApplyForm';
import { InvestCreditsWidget } from '../components/investor/InvestCreditsWidget';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const CheckoutResultBanner = () => {
  const [result, setResult] = useState(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sid = params.get('invest_session_id');
    if (!sid) return;
    fetch(`${API_URL}/api/investor-plans/checkout-status/${sid}`)
      .then((r) => r.json())
      .then((d) => { if (d.status === 'ACTIVE') { setResult(d); toast.success('Adhésion investisseur validée !'); } })
      .catch(() => {});
  }, []);
  if (!result) return null;
  return (
    <div className="rounded-[18px] p-5 mb-5 bg-[#8CC63E]/10 border border-[#8CC63E]/40" data-testid="invest-welcome-banner">
      <p className="text-[#8CC63E] font-bold m-0 mb-1">✔ Votre espace investisseur {result.plan} est créé</p>
      <p className="text-white/80 text-sm m-0">Identifiant provisoire : <strong className="font-mono">{result.email}</strong></p>
      {result.temp_password && (
        <p className="text-white/80 text-sm m-0">Mot de passe provisoire : <strong className="font-mono text-[#E9CF8E]" data-testid="temp-password">{result.temp_password}</strong></p>
      )}
      <p className="text-amber-300 text-xs mt-2 mb-0">Connectez-vous dès maintenant — vous serez invité à modifier votre mot de passe à la première connexion.</p>
    </div>
  );
};

const blocks = [
  {
    icon: Euro,
    title: 'Abonnement O\u2019SCOP',
    text: "Abonnement mensuel de services coopératifs : montant, factures et statut, distincts de tout investissement.",
  },
  {
    icon: Ticket,
    title: "CREDI'SCOP-INVEST",
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
      <NavBar />
      <main className="max-w-[1000px] mx-auto px-5 pt-24 pb-14" data-testid="investor-space-page">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
          <BreadcrumbPill />
          <SpaceHeaderActions showFavorites={false} />
        </div>
        <div className="flex items-center gap-3 flex-wrap mb-3">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">Espace investisseurs</h1>
          <MessagesNavLink withLabel />
        </div>
        <p className="text-white/70 max-w-[70ch] mb-8">
          L'espace investisseur O'SCOP sépare strictement l'abonnement, le compteur CREDI'SCOP-INVEST, les
          investissements réels et le financement logistique LOGI'SCOP.
        </p>
        <InvestorLiveDashboard />
        <InvestorDataroom />
        <FinancingOpportunities />
        <CheckoutResultBanner />
        <InvestCreditsWidget />
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
            Les CREDI'SCOP-INVEST sont des unités internes de services. Ils ne constituent ni un solde financier,
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
