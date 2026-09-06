import Seo from '../components/Seo';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { ShoppingBasket } from 'lucide-react';
import { AudienceSwitcher } from '../components/landing/AudienceSwitcher';
import { AudienceBanner } from '../components/landing/AudienceBanner';
import { ZoneProductsShowcase } from '../components/landing/ZoneProductsShowcase';
import { TerritoryCarousel } from '../components/kdmarche/TerritoryCarousel';
import { PublicLolodriveMapSection } from '../components/landing/PublicLolodriveMapSection';
import { VideoShowcase } from '../components/kdmarche/VideoShowcase';
import { ReferralChallengeBanner } from '../components/ReferralChallengeBanner';
import { Reveal } from '../components/landing/Reveal';
import { LolodriveSpotButton } from '../components/lolodrive/LolodriveSpot';

export default function ParticuliersPage() {
  return (
    <div className="min-h-screen vitrine relative" style={{ isolation: 'isolate', overflowX: 'clip' }} data-testid="particuliers-page">
      <Seo titleKey="seo.landing_title" descKey="seo.landing_desc" />
      <AudienceSwitcher />
      <div className="pt-8"><NavBar /></div>
      <div className="pt-24" />
      <AudienceBanner
        id="particuliers" icon={ShoppingBasket} color="#8CC63E" testId="audience-banner-particuliers"
        kicker="Espace particuliers"
        title="Pour les particuliers & consommateurs"
        subtitle="Produits phares de votre territoire, points relais LOLODRIVE, PASS Vie Chère, parrainage et spots vidéo."
      />
      <div className="flex justify-center -mt-2 mb-2"><LolodriveSpotButton /></div>
      <Reveal><ZoneProductsShowcase audience="lolodrive" /></Reveal>
      <Reveal variant="zoom"><div className="py-8"><TerritoryCarousel /></div></Reveal>
      <Reveal><PublicLolodriveMapSection /></Reveal>
      <Reveal variant="zoom"><ReferralChallengeBanner /></Reveal>
      <Reveal><VideoShowcase /></Reveal>
      <Footer />
    </div>
  );
}
