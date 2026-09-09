import { Link } from 'react-router-dom';
import Seo from '../components/Seo';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { Code2, Package, RefreshCw, ShieldCheck, Layers, ArrowRight, CheckCircle2 } from 'lucide-react';
import { Reveal } from '../components/landing/Reveal';

const FEATURES = [
  { icon: Package, title: 'Catalogue en temps réel', desc: 'Interrogez le catalogue coopératif multi-zones : produits, prix HT négociés, disponibilité et logistique par pays.' },
  { icon: RefreshCw, title: 'Commandes automatisées', desc: 'Créez et suivez vos commandes mutualisées directement depuis votre ERP, votre caisse ou votre site e-commerce.' },
  { icon: Layers, title: 'Stocks & zones', desc: 'Synchronisez les stocks, les zones tarifaires et les points relais LOLODRIVE avec vos propres outils.' },
  { icon: ShieldCheck, title: 'Accès sécurisé', desc: 'Clés API dédiées par organisation, quotas maîtrisés et traçabilité complète de chaque appel.' },
];

// Page d'explication de l'API coopérative + invitation à la souscription annuelle
export default function ApiCooperativePage() {
  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #2a0c4a 0%, #1F0A33 100%)' }}>
      <Seo title="API coopérative — Centrale O'SCOP" description="Connectez vos outils à la centrale d'achats : catalogue, commandes, stocks et logistique via l'API coopérative." />
      <NavBar />
      <main className="max-w-[1000px] mx-auto px-5 pt-28 pb-16" data-testid="api-cooperative-page">
        <Reveal>
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold bg-[#D9B35A]/15 border border-[#D9B35A]/40 text-[#E9CF8E]">
            <Code2 className="w-3.5 h-3.5" /> API COOPÉRATIVE
          </span>
          <h1 className="font-display text-4xl sm:text-5xl mt-4 mb-3">Connectez vos outils à la centrale</h1>
          <p className="text-white/70 text-base max-w-2xl">
            L'API coopérative O'SCOP permet aux adhérents professionnels de brancher leur ERP, leur caisse ou leur
            boutique en ligne directement sur la centrale d'achats : catalogue, prix négociés, commandes mutualisées,
            stocks et logistique LOGI'SCOP — sans ressaisie manuelle.
          </p>
        </Reveal>

        <Reveal delay={80}>
          <div className="grid sm:grid-cols-2 gap-4 mt-10">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="glass-panel-soft rounded-[20px] p-6" data-testid={`api-feature-${title.split(' ')[0].toLowerCase()}`}>
                <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-3 bg-[#D9B35A]/12 border border-[#D9B35A]/30">
                  <Icon className="w-5 h-5 text-[#D9B35A]" />
                </div>
                <h3 className="font-display text-lg mb-1.5 text-white/95">{title}</h3>
                <p className="text-sm text-white/65 m-0">{desc}</p>
              </div>
            ))}
          </div>
        </Reveal>

        <Reveal delay={110}>
          <div className="mt-10 rounded-[20px] border border-white/10 overflow-hidden" data-testid="api-code-example">
            <div className="px-5 py-3 bg-white/[0.04] border-b border-white/10 flex items-center gap-2">
              <Code2 className="w-4 h-4 text-[#8CC63E]" />
              <span className="text-xs font-bold uppercase tracking-wide text-white/60">Exemple — récupérer le catalogue d'une zone</span>
            </div>
            <pre className="m-0 p-5 text-[13px] leading-relaxed overflow-x-auto bg-[#150724] text-[#B6E27A]">
{`curl -X GET "https://centrale.objectifscopoutremer.com/api/v2/catalog/products?zone_code=GUADELOUPE" \\
  -H "Authorization: Bearer VOTRE_CLE_API"

# Réponse (extrait)
[
  {
    "sku": "RIZ-5KG",
    "name": "Riz parfumé 5 kg",
    "price_ht_cents": 780,
    "zone_code": "GUADELOUPE",
    "in_stock": true
  }
]`}
            </pre>
          </div>
        </Reveal>

        <Reveal delay={140}>
          <div className="mt-10 rounded-[24px] p-7 border border-[#D9B35A]/30 text-center"
            style={{ background: 'radial-gradient(120% 160% at 50% -20%, rgba(217,179,90,0.14), rgba(20,8,38,0.5))' }}
            data-testid="api-subscription-cta">
            <h2 className="font-display text-2xl mb-2 text-[#E9CF8E]">Accès inclus dans la souscription annuelle</h2>
            <p className="text-white/70 text-sm max-w-xl mx-auto mb-4">
              L'API est réservée aux adhérents de la centrale. La souscription annuelle inclut la clé API de votre
              organisation, l'accès multi-zones, l'assistance technique et les mises à jour du catalogue.
            </p>
            <ul className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-white/75 mb-6 list-none p-0">
              {['Clé API par organisation', 'Support technique coopératif', 'Catalogue & prix en continu'].map((li) => (
                <li key={li} className="inline-flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-[#8CC63E]" /> {li}</li>
              ))}
            </ul>
            <div className="flex flex-wrap justify-center gap-3">
              <Link to="/tarifs" data-testid="api-cta-souscription"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-[#2a0c4a]"
                style={{ background: 'linear-gradient(135deg, #F5A623 0%, #D9B35A 100%)' }}>
                Souscrire l'abonnement annuel <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to="/adhesion-vendeur" data-testid="api-cta-adhesion"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white border border-white/25 hover:bg-white/5">
                Adhérer à la centrale
              </Link>
            </div>
          </div>
        </Reveal>
      </main>
      <Footer />
    </div>
  );
}
