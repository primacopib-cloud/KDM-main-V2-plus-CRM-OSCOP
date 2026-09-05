import Seo from '../components/Seo';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { AudienceSwitcher } from '../components/landing/AudienceSwitcher';
import { TerritoryCarousel } from '../components/kdmarche/TerritoryCarousel';

export default function TerritoiresPage() {
  return (
    <div className="min-h-screen vitrine relative" style={{ isolation: 'isolate', overflowX: 'clip' }} data-testid="territoires-page">
      <Seo titleKey="seo.landing_title" descKey="seo.landing_desc" />
      <AudienceSwitcher />
      <NavBar />
      <div className="pt-28 pb-10">
        <TerritoryCarousel />
      </div>
      <Footer />
    </div>
  );
}
