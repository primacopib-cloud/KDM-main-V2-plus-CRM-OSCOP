import Seo from '../components/Seo';
import i18n from '@/i18n';
import React from 'react';
import { Link } from 'react-router-dom';
import NavBar from '../components/NavBar';
import {
  Check, Sparkles, ShieldCheck, Handshake, TrendingUp, Users,
  MapPin, Package, Wallet, LineChart, HeartHandshake,
} from 'lucide-react';

/**
 * Public pricing page — ESS subscription tiers for KDMARCHE × O'SCOP.
 * Structure mirrors the "Choisissez votre accès à la Centrale" reference:
 *   ESS ACCÈS PRO · ESS VOLUME PRO (recommended) · ESS IMPACT PRO
 */
const TIERS = [
  {
    id: 'ess-acces-pro',
    name: 'ESS ACCÈS PRO',
    tagline: i18n.t('pricing.demarrage_cooperatif'),
    price: 149,
    period: i18n.t('offers.ht_mois'),
    accent: '#5B2E8C',
    accentSoft: 'rgba(76,42,110,0.08)',
    accentBorder: 'rgba(76,42,110,0.22)',
    features: [
      { icon: Package, label: i18n.t('pricing.acces_a_la_centrale') },
      { icon: MapPin, label: i18n.t('pricing.1_zone_geographique_incluse') },
      { icon: TrendingUp, label: i18n.t('pricing.acces_aux_prix_structurels') },
      { icon: Wallet, label: i18n.t('pricing.wallet_credits_de_base') },
    ],
    cta: i18n.t('pricing.s_inscrire'),
    ctaLink: '/adhesion-vendeur?plan=ess-acces-pro',
    recommended: false,
  },
  {
    id: 'ess-volume-pro',
    name: 'ESS VOLUME PRO',
    tagline: i18n.t('pricing.le_choix_des_membres'),
    includes: i18n.t('pricing.inclut_volume'),
    price: 349,
    period: i18n.t('offers.ht_mois'),
    accent: '#D9B35A',
    accentSoft: 'rgba(217,179,90,0.10)',
    accentBorder: 'rgba(217,179,90,0.35)',
    features: [
      { icon: TrendingUp, label: i18n.t('pricing.acces_prioritaire_aux_volumes') },
      { icon: Package, label: i18n.t('pricing.acces_elargi_aux_gammes') },
      { icon: Wallet, label: i18n.t('pricing.wallet_credits_renforce') },
      { icon: HeartHandshake, label: i18n.t('pricing.acces_multi_categories') },
      { icon: Sparkles, label: i18n.t('pricing.reporting_d_usage') },
      { icon: MapPin, label: i18n.t('pricing.acces_promos_flash_de') },
    ],
    cta: i18n.t('offers.s_inscrire_maintenant'),
    ctaLink: '/adhesion-vendeur?plan=ess-volume-pro',
    recommended: true,
  },
  {
    id: 'ess-impact-pro',
    name: 'ESS IMPACT PRO',
    tagline: i18n.t('pricing.cooperative_en_projet'),
    includes: i18n.t('pricing.inclut_impact'),
    price: 749,
    period: i18n.t('offers.ht_mois'),
    accent: '#4a1776',
    accentSoft: 'rgba(74,23,118,0.08)',
    accentBorder: 'rgba(74,23,118,0.28)',
    features: [
      { icon: MapPin, label: i18n.t('pricing.acces_multi_zones') },
      { icon: Users, label: i18n.t('pricing.acces_projets_collectifs') },
      { icon: LineChart, label: i18n.t('pricing.reporting_ess_impact') },
      { icon: HeartHandshake, label: i18n.t('pricing.appui_structuration_cooperative') },
      { icon: ShieldCheck, label: i18n.t('pricing.accompagnement_compliance_ess') },
      { icon: Handshake, label: i18n.t('pricing.contact_dedie_referent_reseau') },
    ],
    cta: i18n.t('pricing.s_inscrire'),
    ctaLink: '/adhesion-vendeur?plan=ess-impact-pro',
    recommended: false,
  },
];

const PricingPage = () => {
  const [visibleSlugs, setVisibleSlugs] = React.useState(null);

  React.useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/public/plans`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d && Array.isArray(d.plans)) setVisibleSlugs(d.plans.map((p) => p.slug)); })
      .catch(() => {});
  }, []);

  const tiers = visibleSlugs === null ? TIERS : TIERS.filter((t) => visibleSlugs.includes(t.id));

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }} data-testid="pricing-page">
      <Seo titleKey="seo.pricing_title" descKey="seo.pricing_desc" />
      <NavBar />

      {/* Hero */}
      <section className="pt-28 pb-10 px-4">
        <div className="max-w-6xl mx-auto text-center">
          <span
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs uppercase tracking-[0.15em] font-semibold mb-5"
            style={{
              background: 'rgba(217,179,90,0.12)',
              border: '1px solid rgba(217,179,90,0.35)',
              color: '#D9B35A',
            }}
            data-testid="pricing-badge"
          >
            <Sparkles className="w-3 h-3" />
            {i18n.t('offers.abonnements_o_scop')}
          </span>
          <h1
            className="text-4xl sm:text-5xl lg:text-6xl font-serif font-semibold text-white leading-[1.05] mb-4"
            style={{ fontFamily: '"Playfair Display", serif' }}
            data-testid="pricing-title"
          >
            {i18n.t('landing.acces_pro')} <span className="text-[#D9B35A]">{i18n.t('pricing.mutualise')}</span>
          </h1>
          <p className="text-white/70 text-base sm:text-lg max-w-2xl mx-auto">
            {i18n.t('pricing.choisissez_votre_acces_a')}
          </p>
        </div>
      </section>

      {/* Tiers grid */}
      <section className="pb-16 px-4">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6 lg:gap-7">
          {tiers.map((tier) => (
            <PricingCard key={tier.id} tier={tier} />
          ))}
          {tiers.length === 0 && (
            <div className="col-span-full text-center text-white/60 py-10" data-testid="pricing-no-plans">
              Les offres seront bientôt disponibles. Contactez-nous pour en savoir plus.
            </div>
          )}
        </div>
      </section>

      {/* Trust strip */}
      <section className="pb-16 px-4">
        <div className="max-w-5xl mx-auto grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[
            { icon: ShieldCheck, title: i18n.t('landing.securise'), desc: i18n.t('pricing.rgpd_ssl_wallet_certifie') },
            { icon: Handshake, title: i18n.t('pricing.mutualise'), desc: i18n.t('landing.conditions_issues_du_collectif') },
            { icon: HeartHandshake, title: i18n.t('landing.cooperatif'), desc: i18n.t('landing.modele_ethique_et_solidaire') },
            { icon: TrendingUp, title: i18n.t('landing.performant'), desc: i18n.t('pricing.solutions_et_services_selectionnes') },
          ].map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="on-dark p-5 rounded-2xl border border-[#D9B35A]/25 flex items-start gap-3"
                style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03))', backdropFilter: 'blur(12px)' }}
              >
                <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-[#D9B35A]/15 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-[#D9B35A]" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{f.title}</p>
                  <p className="text-xs text-white/55 mt-0.5">{f.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* FAQ short */}
      <section className="pb-24 px-4">
        <div
          className="on-dark max-w-3xl mx-auto p-8 rounded-2xl border border-[#D9B35A]/25"
          style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03))', backdropFilter: 'blur(12px)' }}
        >
          <h3 className="text-xl font-serif font-semibold text-white mb-4" style={{ fontFamily: '"Playfair Display", serif' }}>
            {i18n.t('pricing.questions_frequentes')}
          </h3>
          <div className="space-y-4 text-sm">
            <div>
              <p className="font-semibold text-[#E9CF8E]">{i18n.t('pricing.puis_je_changer_de')}</p>
              <p className="text-white/70 mt-1">
                {i18n.t('pricing.oui_changement_de_formule')}
              </p>
            </div>
            <div>
              <p className="font-semibold text-[#E9CF8E]">{i18n.t('pricing.qui_peut_adherer')}</p>
              <p className="text-white/70 mt-1">
                {i18n.t('pricing.qui_peut_adherer_answer')}
              </p>
            </div>
            <div>
              <p className="font-semibold text-[#E9CF8E]">{i18n.t('pricing.comment_se_calculent_les')}</p>
              <p className="text-white/70 mt-1">
                {i18n.t('pricing.comment_answer')}
              </p>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/adhesion"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}
              data-testid="cta-adhesion"
            >
              {i18n.t('landing.adherer_a_la_centrale')}
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

const PricingCard = ({ tier }) => {
  const isRecommended = tier.recommended;
  return (
    <div
      className={`on-dark relative rounded-3xl p-6 lg:p-7 transition-transform hover:-translate-y-1 ${
        isRecommended ? 'shadow-2xl ring-2 ring-[#D9B35A]' : 'shadow-lg'
      }`}
      style={{
        background: 'linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))',
        border: '1px solid rgba(217,179,90,0.28)',
        backdropFilter: 'blur(12px)',
      }}
      data-testid={`pricing-card-${tier.id}`}
    >
      {isRecommended && (
        <span
          className="absolute -top-3 right-6 px-3 py-1 rounded-full text-[10px] uppercase tracking-[0.15em] font-bold shadow-md"
          style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}
          data-testid="pricing-recommended-badge"
        >
          {i18n.t('offers.recommande')}
        </span>
      )}
      <div>
        <p className="text-[11px] uppercase tracking-[0.18em] font-bold mb-1 text-[#D9B35A]">
          {tier.name}
        </p>
        <p className="text-xs text-white/55 mb-2">{tier.tagline}</p>
        {tier.includes && (
          <p className="text-[11px] font-bold text-[#E9CF8E] mb-3" data-testid={`pricing-includes-${tier.id}`}>
            ↑ {tier.includes}
          </p>
        )}

        <div
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] uppercase tracking-wider font-semibold mb-3"
          style={{ background: 'rgba(217,179,90,0.14)', color: '#E9CF8E' }}
        >
          {i18n.t('lists.mensuel')}
        </div>

        <div className="flex items-baseline gap-1 mb-6">
          <span className="text-5xl font-bold text-white">{tier.price}</span>
          <span className="text-2xl font-bold text-white/70">€</span>
          <span className="text-xs text-white/50 ml-2">{tier.period}</span>
        </div>

        <ul className="space-y-3 mb-8">
          {tier.features.map((f) => {
            const Icon = f.icon;
            return (
              <li key={f.label} className="flex items-start gap-2.5 text-sm text-white/85">
                <div
                  className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5"
                  style={{ background: 'rgba(217,179,90,0.16)' }}
                >
                  <Check className="w-3 h-3 text-[#D9B35A]" />
                </div>
                <span className="leading-snug">{f.label}</span>
                <Icon className="w-3.5 h-3.5 text-white/25 ml-auto mt-1 flex-shrink-0" />
              </li>
            );
          })}
        </ul>

        <Link
          to={tier.ctaLink}
          data-testid={`pricing-cta-${tier.id}`}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold transition-all hover:brightness-110"
          style={
            isRecommended
              ? { background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }
              : { background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(217,179,90,0.4)', color: '#E9CF8E' }
          }
        >
          {tier.cta} <span aria-hidden>→</span>
        </Link>
      </div>
    </div>
  );
};

export default PricingPage;
