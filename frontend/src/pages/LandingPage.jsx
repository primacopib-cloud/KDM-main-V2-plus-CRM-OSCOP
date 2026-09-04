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
import { CooperativeApiSection } from '../components/landing/CooperativeApiSection';
import { FloatingToc } from '../components/landing/FloatingToc';
import { Reveal } from '../components/landing/Reveal';
import { ParallaxOrbs } from '../components/landing/ParallaxOrbs';
import { ScrollProgressBar } from '../components/landing/ScrollProgressBar';
import { ActivityTicker } from '../components/landing/ActivityTicker';
import { BackToTop } from '../components/landing/BackToTop';
export { PublicLolodriveMapSection };
export { CooperativeApiSection };

const LandingPage = () => {
  return (
    <div className="min-h-screen vitrine relative" style={{ isolation: 'isolate', overflowX: 'clip' }}>
      <ParallaxOrbs />
      <ScrollProgressBar />
      <BackToTop />
      <Seo titleKey="seo.landing_title" descKey="seo.landing_desc" />
      <NavBar />
      <FloatingToc />
      <div className="pt-20 -mb-16"><FlashPromoBanner placement="landing" /></div>

      {/* Hero Section */}
      <section className="pt-20 pb-8 px-5">
        <div className="max-w-[1160px] mx-auto">
          <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-6 items-stretch">
            {/* Main Hero Card */}
            <div className="glass-panel card-glow rounded-[26px] p-7">
              {/* Kicker */}
              <div className="flex items-center gap-2.5 flex-wrap mb-3.5">
                <div className="badge-status">
                  <span className="dot pulse-glow"></span>
                  {i18n.t('landing.partenariat_actif')}
                </div>
                <span className="pill">
                  <span className="font-bold text-white/90">ESS</span>
                  <span className="text-white/65">{i18n.t('landing.economie_sociale_et_solidaire')}</span>
                </span>
              </div>

              <h2 className="text-[36px] leading-[1.08] font-bold tracking-tight my-2.5" data-testid="hero-title">
                La centrale coopérative <span className="text-[#D9B35A]">d'achat, de référencement et de distribution</span>
              </h2>

              <p className="text-white/75 text-base max-w-[60ch] m-0">
                {i18n.t('landing.official_statement')}
              </p>

              {/* Actions */}
              <div className="flex gap-3 flex-wrap mt-5">
                <Link to="/catalogue">
                  <button
                    className="force-white inline-flex items-center justify-center gap-2.5 rounded-[14px] px-4 py-3 text-sm font-semibold text-white shadow-lg"
                    style={{ background: 'linear-gradient(135deg, #5B2E8C 0%, #2A1045 100%)' }}
                    data-testid="hero-cta-offres"
                    onClick={() => trackCta('hero_offres')}
                  >
                    Découvrir les offres
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </Link>
                <Link to="/tarifs">
                  <button
                    className="btn-ghost inline-flex items-center justify-center gap-2 rounded-[14px] px-4 py-3 text-sm font-semibold"
                    data-testid="hero-cta-acces-pro"
                    onClick={() => trackCta('hero_acces_pro')}
                  >
                    Accès acheteurs professionnels
                  </button>
                </Link>
                <Link to="/espace-investisseur" className="btn-ghost inline-flex items-center justify-center gap-2 rounded-[14px] px-4 py-3 text-sm font-semibold" data-testid="hero-cta-investisseurs">
                  Espace investisseurs
                </Link>
              </div>

              {/* Mini Stats */}
              <div className="grid grid-cols-3 gap-3 mt-5">
                <div className="mini-card">
                  <div className="text-xs text-white/65 uppercase tracking-wider">{i18n.t('landing.prix')}</div>
                  <div className="text-sm mt-1.5 text-white/90 font-bold">{i18n.t('landing.jusqu_a_50')}</div>
                </div>
                <div className="mini-card">
                  <div className="text-xs text-white/65 uppercase tracking-wider">{i18n.t('landing.modele')}</div>
                  <div className="text-sm mt-1.5 text-white/90 font-bold">B2B EXW</div>
                </div>
                <div className="mini-card">
                  <div className="text-xs text-white/65 uppercase tracking-wider">{i18n.t('landing.commission')}</div>
                  <div className="text-sm mt-1.5 text-white/90 font-bold">{i18n.t('landing.0_produit')}</div>
                </div>
              </div>
            </div>

            {/* Side Card */}
            <div className="glass-panel-soft rounded-[26px] p-5 flex flex-col gap-3.5 hero-enter-delayed" style={{ boxShadow: '0 16px 50px rgba(0,0,0,0.35)' }}>
              <h3 className="text-sm tracking-wider uppercase text-white/75 font-semibold m-0">{i18n.t('landing.avantages_cles')}</h3>

              {/* Callout */}
              <div className="callout-gold">
                <strong className="text-white/90">{i18n.t('landing.prix_structurels_b2b')}</strong>
                <p className="text-sm text-white/70 mt-1 mb-0">
                  {i18n.t('landing.il_ne_s_agit')}
                </p>
              </div>

              {/* List */}
              <ul className="grid gap-2.5 m-0 p-0 list-none">
                {(i18n.t('landing.advantages', { returnObjects: true }) || []).map((advantage) => (
                  <li
                    key={`advantage-${advantage.slice(0, 32)}`}
                    className="flex gap-2.5 items-start p-2.5 px-3 rounded-2xl bg-white/[0.03] border border-white/[0.08]"
                  >
                    <div className="check-icon mt-0.5"></div>
                    <div>
                      <b className="block text-white/90 text-sm">{advantage}</b>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Ticker d'activité en direct */}
      <ActivityTicker />

      {/* Compteurs publics de la coopérative */}
      <Reveal variant="zoom"><CommunityStatsStrip /></Reveal>

      {/* Pourquoi Communityplace ? */}
      <Reveal><WhyCommunityplaceSection /></Reveal>

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

      {/* ============ PARTIE PARTICULIERS / CONSOMMATEURS ============ */}
      <Reveal variant="right">
      <AudienceBanner
        id="particuliers" icon={ShoppingBasket} color="#8CC63E" testId="audience-banner-particuliers"
        kicker="Espace particuliers"
        title="Pour les particuliers & consommateurs"
        subtitle="Produits phares de votre territoire, points relais LOLODRIVE, PASS Vie Chère, parrainage et spots vidéo."
      />
      </Reveal>

      {/* Produits phares par territoire */}
      <Reveal><ZoneProductsShowcase /></Reveal>

      {/* Carrousel territorial — visiteurs grand public */}
      <Reveal variant="zoom">
      <div className="py-8">
        <TerritoryCarousel />
      </div>
      </Reveal>

      {/* Réseau LOLODRIVE — carte publique */}
      <Reveal><PublicLolodriveMapSection /></Reveal>

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
