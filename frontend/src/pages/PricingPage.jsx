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
    tagline: 'Démarrage coopératif',
    price: 149,
    period: 'HT / mois',
    accent: '#0B4D87',
    accentSoft: 'rgba(11,77,135,0.08)',
    accentBorder: 'rgba(11,77,135,0.22)',
    features: [
      { icon: Package, label: 'Accès à la centrale d\'achats KDMARCHE B2B' },
      { icon: MapPin, label: '1 zone géographique incluse' },
      { icon: TrendingUp, label: 'Accès aux prix structurels mutualisés' },
      { icon: Wallet, label: 'Wallet crédits de base' },
    ],
    cta: 'S\'inscrire',
    ctaLink: '/adhesion?plan=ess-acces-pro',
    recommended: false,
  },
  {
    id: 'ess-volume-pro',
    name: 'ESS VOLUME PRO',
    tagline: 'Le choix des membres actifs',
    price: 349,
    period: 'HT / mois',
    accent: '#D9B35A',
    accentSoft: 'rgba(217,179,90,0.10)',
    accentBorder: 'rgba(217,179,90,0.35)',
    features: [
      { icon: TrendingUp, label: 'Accès prioritaire aux volumes' },
      { icon: Package, label: 'Accès élargi aux gammes KDMARCHE' },
      { icon: Wallet, label: 'Wallet crédits renforcé' },
      { icon: HeartHandshake, label: 'Accès multi-catégories' },
      { icon: Sparkles, label: 'Reporting d\'usage' },
      { icon: MapPin, label: 'Accès promos flash de la zone' },
    ],
    cta: 'S\'inscrire maintenant',
    ctaLink: '/adhesion?plan=ess-volume-pro',
    recommended: true,
  },
  {
    id: 'ess-impact-pro',
    name: 'ESS IMPACT PRO',
    tagline: 'Coopérative en projet',
    price: 749,
    period: 'HT / mois',
    accent: '#4a1776',
    accentSoft: 'rgba(74,23,118,0.08)',
    accentBorder: 'rgba(74,23,118,0.28)',
    features: [
      { icon: MapPin, label: 'Accès multi-zones' },
      { icon: Users, label: 'Accès projets collectifs' },
      { icon: LineChart, label: 'Reporting ESS / impact' },
      { icon: HeartHandshake, label: 'Appui structuration coopérative' },
      { icon: ShieldCheck, label: 'Accompagnement compliance ESS' },
      { icon: Handshake, label: 'Contact dédié référent réseau' },
    ],
    cta: 'S\'inscrire',
    ctaLink: '/adhesion?plan=ess-impact-pro',
    recommended: false,
  },
];

const PricingPage = () => {
  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }} data-testid="pricing-page">
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
            Abonnements O&apos;SCOP
          </span>
          <h1
            className="text-4xl sm:text-5xl lg:text-6xl font-serif font-semibold text-[#0B1F3B] leading-[1.05] mb-4"
            style={{ fontFamily: '"Playfair Display", serif' }}
            data-testid="pricing-title"
          >
            Choisissez votre accès <span className="text-[#D9B35A]">à la Centrale</span>
          </h1>
          <p className="text-slate-600 text-base sm:text-lg max-w-2xl mx-auto">
            Accédez aux prix structurels B2B mutualisés via KDMARCHE, dans un cadre coopératif B2B2C dédié aux membres
            professionnels.
          </p>
        </div>
      </section>

      {/* Tiers grid */}
      <section className="pb-16 px-4">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6 lg:gap-7">
          {TIERS.map((tier) => (
            <PricingCard key={tier.id} tier={tier} />
          ))}
        </div>
      </section>

      {/* Trust strip */}
      <section className="pb-16 px-4">
        <div className="max-w-5xl mx-auto grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[
            { icon: ShieldCheck, title: 'Sécurisé', desc: 'RGPD · SSL · Wallet certifié' },
            { icon: Handshake, title: 'Mutualisé', desc: 'Conditions issues du collectif' },
            { icon: HeartHandshake, title: 'Coopératif', desc: 'Modèle éthique et solidaire' },
            { icon: TrendingUp, title: 'Performant', desc: 'Solutions et services sélectionnés' },
          ].map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="p-5 rounded-2xl bg-white/70 border border-[#D9B35A]/25 backdrop-blur-sm flex items-start gap-3"
              >
                <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-[#4a1776]/10 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-[#4a1776]" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-[#0B1F3B]">{f.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{f.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* FAQ short */}
      <section className="pb-24 px-4">
        <div className="max-w-3xl mx-auto p-8 rounded-2xl bg-white/80 border border-[#D9B35A]/25 backdrop-blur-sm">
          <h3 className="text-xl font-serif font-semibold text-[#0B1F3B] mb-4" style={{ fontFamily: '"Playfair Display", serif' }}>
            Questions fréquentes
          </h3>
          <div className="space-y-4 text-sm">
            <div>
              <p className="font-semibold text-[#0B1F3B]">Puis-je changer de formule à tout moment ?</p>
              <p className="text-slate-600 mt-1">
                Oui, changement de formule possible chaque mois. L&apos;écart tarifaire est calculé au prorata et
                imputé au wallet crédits.
              </p>
            </div>
            <div>
              <p className="font-semibold text-[#0B1F3B]">Qui peut adhérer ?</p>
              <p className="text-slate-600 mt-1">
                Toute structure professionnelle (SIRET obligatoire) : coopératives, associations ESS, PME, artisans,
                restaurateurs, épiceries, collectivités.
              </p>
            </div>
            <div>
              <p className="font-semibold text-[#0B1F3B]">Comment se calculent les prix mutualisés ?</p>
              <p className="text-slate-600 mt-1">
                Les prix résultent de la force collective des membres : volumes agrégés, contributions et services
                mutualisés du réseau. Il ne s&apos;agit ni de remises, ni de promotions, mais de <strong>conditions
                économiques structurelles</strong>.
              </p>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/adhesion"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white"
              style={{ background: 'linear-gradient(135deg, #0B4D87 0%, #083866 100%)' }}
              data-testid="cta-adhesion"
            >
              Adhérer à la Centrale
            </Link>
            <Link
              to="/#contact"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-[#4a1776] border border-[#4a1776]/25 hover:bg-[#4a1776]/5"
              data-testid="cta-contact"
            >
              Parler à un conseiller
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
      className={`relative rounded-3xl p-6 lg:p-7 bg-white/90 backdrop-blur-sm transition-transform hover:-translate-y-1 ${
        isRecommended ? 'shadow-2xl ring-2 ring-[#D9B35A]' : 'shadow-lg'
      }`}
      style={{ border: `1px solid ${tier.accentBorder}` }}
      data-testid={`pricing-card-${tier.id}`}
    >
      {isRecommended && (
        <span
          className="absolute -top-3 right-6 px-3 py-1 rounded-full text-[10px] uppercase tracking-[0.15em] font-bold text-white shadow-md"
          style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)' }}
          data-testid="pricing-recommended-badge"
        >
          Recommandé
        </span>
      )}
      <div>
        <p
          className="text-[11px] uppercase tracking-[0.18em] font-bold mb-1"
          style={{ color: tier.accent }}
        >
          {tier.name}
        </p>
        <p className="text-xs text-slate-500 mb-5">{tier.tagline}</p>

        <div
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] uppercase tracking-wider font-semibold mb-3"
          style={{ background: tier.accentSoft, color: tier.accent }}
        >
          Mensuel
        </div>

        <div className="flex items-baseline gap-1 mb-6">
          <span className="text-5xl font-bold text-[#0B1F3B]">{tier.price}</span>
          <span className="text-2xl font-bold text-[#0B1F3B]/70">€</span>
          <span className="text-xs text-slate-500 ml-2">{tier.period}</span>
        </div>

        <ul className="space-y-3 mb-8">
          {tier.features.map((f) => {
            const Icon = f.icon;
            return (
              <li key={f.label} className="flex items-start gap-2.5 text-sm text-slate-700">
                <div
                  className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5"
                  style={{ background: tier.accentSoft }}
                >
                  <Check className="w-3 h-3" style={{ color: tier.accent }} />
                </div>
                <span className="leading-snug">{f.label}</span>
                <Icon className="w-3.5 h-3.5 text-slate-300 ml-auto mt-1 flex-shrink-0" />
              </li>
            );
          })}
        </ul>

        <Link
          to={tier.ctaLink}
          data-testid={`pricing-cta-${tier.id}`}
          className={`w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition-all ${
            isRecommended
              ? 'text-white shadow-lg hover:shadow-xl'
              : 'text-[#0B1F3B] hover:opacity-90'
          }`}
          style={
            isRecommended
              ? { background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)' }
              : { background: tier.accentSoft, border: `1px solid ${tier.accentBorder}` }
          }
        >
          {tier.cta} <span aria-hidden>→</span>
        </Link>
      </div>
    </div>
  );
};

export default PricingPage;
