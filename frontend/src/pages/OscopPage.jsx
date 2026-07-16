import i18n from '@/i18n';
import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Users, HeartHandshake, Sprout, Vote, Leaf, Award, BarChart3 } from 'lucide-react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

/**
 * O'SCOP — Objectif SCOP Outre-mer (gouvernance coopérative ESS).
 * Charte : Vert lime #8CC63E (vie, ESS) + Or métallisé #D4AF37 (premium coopératif).
 */
export default function OscopPage() {
  return (
    <div className="min-h-screen text-white">
      <NavBar />

      {/* Hero — Vert lime × Or métallisé */}
      <section
        className="px-5 pt-20 pb-14"
        style={{ background: 'linear-gradient(135deg, rgba(140,198,62,0.18) 0%, rgba(212,175,55,0.15) 100%)' }}
        data-testid="oscop-hero"
      >
        <div className="max-w-[1160px] mx-auto grid md:grid-cols-2 gap-10 items-center">
          <div>
            <span
              className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wider"
              style={{ background: 'rgba(140,198,62,0.15)', color: '#8CC63E', border: '1px solid rgba(140,198,62,0.45)' }}
            >
              <HeartHandshake className="w-3 h-3" /> {i18n.t('oscop.badge')}
            </span>
            <h1
              className="font-display text-5xl md:text-6xl font-bold leading-[1.05] mt-4 mb-3 tracking-tight italic"
            >
              <span style={{ color: '#8CC63E' }}>O</span>'<span style={{ color: '#D4AF37' }}>SCOP</span>
            </h1>
            <p className="text-base text-white/80 max-w-[55ch] mb-2">
              <strong>{i18n.t('oscop.objectif_scop_outre_mer')}</strong> — {i18n.t('oscop.hero_desc')}
            </p>
            <p className="text-sm text-white/60 max-w-[55ch] mb-6 italic">
              {i18n.t('oscop.hero_quote')}
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/inscription">
                <button
                  className="inline-flex items-center gap-2 rounded-[14px] px-5 py-3 text-sm font-semibold transition-all hover:translate-y-[-1px]"
                  style={{ background: 'linear-gradient(135deg, #8CC63E, #D4AF37)', color: '#0a1f08', boxShadow: '0 10px 30px rgba(140,198,62,0.35)' }}
                  data-testid="oscop-cta-coop"
                >
                  {i18n.t('oscop.rejoindre')} <ArrowRight className="w-4 h-4" />
                </button>
              </Link>
              <Link to="/reporting-impact" className="inline-flex items-center gap-2 rounded-[14px] px-5 py-3 text-sm font-medium border border-white/15 hover:bg-white/[0.05] transition-all">
                {i18n.t('oscop.reporting_impact_ess')}
              </Link>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Pillar icon={Vote} label={i18n.t('oscop.gouvernance')} value="1=1" sub={i18n.t('oscop.sub_gouvernance')} />
            <Pillar icon={Sprout} label={i18n.t('oscop.cooperateurs')} value="2 410+" sub={i18n.t('oscop.sub_cooperateurs')} />
            <Pillar icon={Award} label={i18n.t('oscop.marges_plafonnees')} value="6%" sub={i18n.t('oscop.sub_marges')} />
            <Pillar icon={Leaf} label={i18n.t('oscop.impact_ess')} value="320 k€" sub={i18n.t('oscop.sub_impact')} />
          </div>
        </div>
      </section>

      {/* Piliers */}
      <section className="px-5 py-12">
        <div className="max-w-[1160px] mx-auto">
          <h2 className="text-3xl font-display font-bold text-center mb-10">
            {i18n.t('oscop.trois_piliers')} <span className="text-vert-lime">{i18n.t('oscop.cooperatifs')}</span>
          </h2>
          <div className="grid md:grid-cols-3 gap-5">
            <Card
              icon={HeartHandshake}
              title={i18n.t('oscop.mutualisation')}
              desc={i18n.t('oscop.achats_groupes_negociation_collective')}
            />
            <Card
              icon={Users}
              title={i18n.t('oscop.gouvernance_partagee')}
              desc={i18n.t('oscop.chaque_cooperateur_dispose_d')}
            />
            <Card
              icon={Leaf}
              title={i18n.t('oscop.impact_territorial')}
              desc={i18n.t('oscop.producteurs_locaux_prioritaires_relais')}
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-5 pb-12">
        <div className="max-w-[800px] mx-auto rounded-[20px] p-8 text-center border" style={{ background: 'linear-gradient(135deg, rgba(140,198,62,0.10), rgba(212,175,55,0.10))', borderColor: 'rgba(212,175,55,0.3)' }}>
          <BarChart3 className="w-10 h-10 mx-auto mb-3 text-or-metallise" />
          <h3 className="font-display text-2xl font-bold mb-2">{i18n.t('oscop.voir_l_impact_ess')}</h3>
          <p className="text-sm text-white/70 mb-5">{i18n.t('oscop.tableaux_de_bord_ouverts')}</p>
          <Link to="/reporting-impact">
            <button className="btn-gold inline-flex items-center gap-2 rounded-[14px] px-5 py-3 text-sm font-semibold">
              {i18n.t('oscop.consulter_reporting')} <ArrowRight className="w-4 h-4" />
            </button>
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}

const Pillar = ({ icon: Icon, label, value, sub }) => (
  <div className="rounded-[16px] p-4 border border-white/10 backdrop-blur-sm" style={{ background: 'rgba(140,198,62,0.06)' }}>
    <Icon className="w-5 h-5 mb-2 text-vert-lime" />
    <div className="font-display text-2xl font-bold">{value}</div>
    <div className="text-[11px] uppercase tracking-wider text-vert-lime mt-1">{label}</div>
    <div className="text-[10px] text-white/50 mt-1">{sub}</div>
  </div>
);

const Card = ({ icon: Icon, title, desc }) => (
  <div className="rounded-[18px] p-5 border border-white/10 hover:border-vert-lime/40 transition-all" style={{ background: 'rgba(255,255,255,0.03)' }}>
    <div className="rounded-full p-2.5 inline-flex mb-3" style={{ background: 'rgba(140,198,62,0.15)' }}>
      <Icon className="w-5 h-5 text-vert-lime" />
    </div>
    <h3 className="text-lg font-display font-bold mb-2">{title}</h3>
    <p className="text-sm text-white/70 leading-relaxed">{desc}</p>
  </div>
);
