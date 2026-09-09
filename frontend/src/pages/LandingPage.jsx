import Seo from '../components/Seo';
import i18n from '@/i18n';
import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, CheckCircle2, ShieldCheck, Building2, ShoppingBasket } from 'lucide-react';
import { trackCta } from '../services/ctaTracking';
import PricingSection from '../components/PricingSection';
import PartnersSection from '../components/PartnersSection';
import LogisticsSection from '../components/LogisticsSection';
import ContactForm from '../components/ContactForm';
import NavBar from '../components/NavBar';
import { FlashPromoBanner } from '../components/FlashPromoBanner';
import Footer from '../components/Footer';
import WhyCommunityplaceSection from '../components/WhyCommunityplaceSection';
import { ZoneProductsShowcase } from '../components/landing/ZoneProductsShowcase';
import PartnerCarousel from '../components/PartnerCarousel';
import { TestimonialsSection } from '../components/TestimonialsSection';
import { ReferralChallengeBanner } from '../components/ReferralChallengeBanner';
import { CommunityStatsStrip } from '../components/CommunityStatsStrip';
import { PublicLolodriveMapSection } from '../components/landing/PublicLolodriveMapSection';
import { ReceptionProSection } from '../components/landing/ReceptionProSection';
import { TerritoryCarousel } from '../components/kdmarche/TerritoryCarousel';
import { ServicesBlock } from '../components/kdmarche/ServicesBlock';
import { VideoShowcase } from '../components/kdmarche/VideoShowcase';
import { AudienceBanner } from '../components/landing/AudienceBanner';
import { KdmPillarsSection } from '../components/landing/KdmPillarsSection';
import { CoopEssSection } from '../components/landing/CoopEssSection';
import { CommunityBoard } from '../components/landing/CommunityBoard';
import { CooperativeApiSection } from '../components/landing/CooperativeApiSection';
import { FloatingToc } from '../components/landing/FloatingToc';
import { Reveal } from '../components/landing/Reveal';
import { ParallaxOrbs } from '../components/landing/ParallaxOrbs';
import { ScrollProgressBar } from '../components/landing/ScrollProgressBar';
import { ActivityTicker } from '../components/landing/ActivityTicker';
import { BackToTop } from '../components/landing/BackToTop';
import { AudienceSwitcher } from '../components/landing/AudienceSwitcher';
import { ProHero } from '../components/landing/ProHero';
import { ProJourneysSection } from '../components/landing/ProJourneysSection';
import { ProCatalogFamilies } from '../components/landing/ProCatalogFamilies';
import { FinancingCompartments } from '../components/landing/FinancingCompartments';
import { LolodriveSection } from '../components/landing/LolodriveSection';
export { PublicLolodriveMapSection };
export { CooperativeApiSection };

const LandingPage = () => {
  return (
    <div className="min-h-screen vitrine relative" style={{ isolation: 'isolate', overflowX: 'clip' }}>
      <ParallaxOrbs />
      <ScrollProgressBar />
      <BackToTop />
      <Seo titleKey="seo.landing_title" descKey="seo.landing_desc" />
      <AudienceSwitcher />
      <NavBar />
      <FloatingToc />
      <div className="pt-24 -mb-16"><FlashPromoBanner placement="landing" /></div>

      {/* Hero professionnel */}
      <ProHero />

      {/* Quatre parcours professionnels */}
      <Reveal><ProJourneysSection /></Reveal>

      {/* Catalogue professionnel — quatre familles */}
      <Reveal variant="left"><ProCatalogFamilies /></Reveal>

      {/* Financement — quatre compartiments + CREDI'SCOP */}
      <Reveal><FinancingCompartments /></Reveal>

      {/* Ticker d'activité en direct */}
      <ActivityTicker />

      {/* Compteurs publics de la coopérative */}
      <Reveal variant="zoom"><CommunityStatsStrip /></Reveal>

      {/* Pourquoi Communityplace ? */}
      <Reveal><WhyCommunityplaceSection /></Reveal>
      <Reveal><CommunityBoard /></Reveal>

      {/* ============ PARTIE PROFESSIONNELS ============ */}
      <Reveal variant="left">
      <AudienceBanner
        id="pros" icon={Building2} color="#D9B35A" testId="audience-banner-pros"
        kicker="Espace professionnels"
        title="Pour les professionnels"
        subtitle="Vendeurs référencés, acheteurs pro, services mutualisés, tarifs ESS et logistique B2B multi-territoires."
      />
      </Reveal>

      {/* Piliers Vendeurs / Acheteurs pro */}
      <Reveal><KdmPillarsSection /></Reveal>

      {/* Les quatre services professionnels */}
      <Reveal delay={80}><ServicesBlock /></Reveal>

      {/* Règlement à Réception Pro — bloc commercial */}
      <Reveal><ReceptionProSection /></Reveal>

      {/* API Coopérative B2B2C — dispositif institutionnel */}
      <Reveal variant="zoom"><CooperativeApiSection /></Reveal>

      {/* Access Condition */}
      <Reveal>
      <section className="py-8 px-5">
        <div className="max-w-[1160px] mx-auto">
          <div
            className="rounded-[22px] p-6 text-center"
            style={{
              background: 'linear-gradient(180deg, rgba(217,179,90,0.12), rgba(255,255,255,0.02))',
              border: '1px solid rgba(217,179,90,0.25)'
            }}
          >
            <span className="ribbon mb-4 inline-block">{i18n.t('landing.regle_absolue')}</span>
            <h3 className="text-2xl font-bold mt-3 mb-3">
              {i18n.t('landing.conditions_d_acces_au')}
            </h3>
            <p className="text-white/75 mb-5 max-w-2xl mx-auto">
              {i18n.t('landing.acces_conditions_prefix')}<strong className="text-white">{i18n.t('landing.kdmarche_centrale_cooperative')}</strong>{i18n.t('landing.est_reserve_aux_membres')}<strong className="text-[#D4AF37]">{i18n.t('landing.adhesion_o_scop_active')}</strong>.
            </p>

            <div className="inline-flex flex-wrap gap-4 justify-center p-4 rounded-2xl bg-black/20">
              {(i18n.t('landing.exclusions_list', { returnObjects: true }) || []).map((item) => (
                <div key={`access-${item.slice(0, 32)}`} className="flex items-center gap-2 text-[#A9D96C] text-sm">
                  <div className="check-icon"></div>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
      </Reveal>

      {/* Pricing Section */}
      <Reveal><PricingSection /></Reveal>

      {/* Logistics Section */}
      <Reveal variant="right"><LogisticsSection /></Reveal>

      {/* Compliance Section */}
      <Reveal>
      <section className="py-8 px-5">
        <div className="max-w-[1160px] mx-auto">
          <div className="section-title mb-4">
            <div>
              <h3 className="text-[22px] font-bold tracking-tight m-0">{i18n.t('landing.conformite_juridique_administrative')}</h3>
              <p className="text-white/70 text-sm mt-1 m-0">{i18n.t('landing.le_partenariat_garantit_une')}</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-3.5">
            <div className="glass-panel-soft rounded-[18px] p-5">
              <h4 className="text-sm tracking-wider uppercase text-[#D4AF37] font-semibold mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                {i18n.t('landing.garanties')}
              </h4>
              <div className="space-y-2.5">
                {(i18n.t('landing.compliance_guaranteed', { returnObjects: true }) || []).map((point) => (
                  <div key={`guaranteed-${point.slice(0, 32)}`} className="flex items-center gap-2.5 text-white/80 text-sm">
                    <div className="check-icon"></div>
                    <span>{point}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-panel-soft rounded-[18px] p-5">
              <h4 className="text-sm tracking-wider uppercase text-[#D9B35A] font-semibold mb-4 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                {i18n.t('landing.exclusions')}
              </h4>
              <div className="space-y-2.5">
                {(i18n.t('landing.compliance_excluded', { returnObjects: true }) || []).map((point) => (
                  <div key={`excluded-${point.slice(0, 32)}`} className="flex items-center gap-2.5 text-white/80 text-sm">
                    <div className="cross-icon"></div>
                    <span>{point}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
      </Reveal>

      {/* Partners Section */}
      <Reveal>
      <PartnersSection />
      <PartnerCarousel />
      </Reveal>

      {/* ============ PONT PARTICULIERS (détails sur /particuliers) ============ */}
      <Reveal><LolodriveSection /></Reveal>

      {/* Section territoriale professionnelle */}
      <Reveal variant="zoom">
      <div className="py-8">
        <TerritoryCarousel />
      </div>
      </Reveal>

      {/* Témoignages membres */}
      <Reveal variant="left"><TestimonialsSection /></Reveal>

      {/* Défi parrainage */}
      <Reveal variant="zoom"><ReferralChallengeBanner /></Reveal>

      {/* Galerie spots vidéo IA */}
      <Reveal><VideoShowcase /></Reveal>

      {/* Catalogue + cadre coopératif ESS */}
      <Reveal><CoopEssSection /></Reveal>

      {/* Contact Section */}
      <Reveal variant="zoom">
      <section id="contact" className="py-8 px-5 scroll-mt-24">
        <div className="max-w-[800px] mx-auto">
          <div className="text-center mb-6">
            <span className="badge-status mb-4 inline-flex">
              <span className="dot"></span>
              {i18n.t('landing.formulaire_de_contact')}
            </span>
            <h3 className="text-[28px] font-bold tracking-tight mt-3 mb-2">{i18n.t('landing.demande_de_devis')}</h3>
            <p className="text-white/70 text-sm">{i18n.t('landing.contactez_nous_pour_rejoindre')}</p>
          </div>

          <ContactForm />
        </div>
      </section>
      </Reveal>

      <Footer />
    </div>
  );
};

export default LandingPage;
