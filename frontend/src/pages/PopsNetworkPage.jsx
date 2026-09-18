import Seo from '../components/Seo';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { AudienceSwitcher } from '../components/landing/AudienceSwitcher';
import { PublicLolodriveMapSection } from '../components/landing/PublicLolodriveMapSection';

export default function PopsNetworkPage() {
  return (
    <div className="min-h-screen vitrine relative" style={{ isolation: 'isolate', overflowX: 'clip' }} data-testid="pops-network-page">
      <Seo titleKey="seo.landing_title" descKey="seo.landing_desc" />
      <AudienceSwitcher />
      <div className="pt-8"><NavBar /></div>
      <div className="pt-24" />
      <PublicLolodriveMapSection showRelays={false} />
      <Footer />
    </div>
  );
}
