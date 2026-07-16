import Seo from '../components/Seo';
import i18n from '@/i18n';
import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Truck, Package, MapPin, Clock, ShieldCheck, BarChart3, Globe2 } from 'lucide-react';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

/**
 * LOGI'SCOP — Logistique coopérative de proximité.
 * Charte : Bleu logistique #5B2E8C (fiabilité) + Orange énergie #FF7A00 (dynamique).
 */
export default function LogiscopPage() {
  return (
    <div className="min-h-screen text-white">
      <Seo titleKey="seo.logiscop_title" descKey="seo.logiscop_desc" />
      <NavBar />

      {/* Hero — Bleu logistique × Orange énergie */}
      <section
        className="px-5 pt-20 pb-14"
        style={{ background: 'linear-gradient(135deg, rgba(76,42,110,0.25) 0%, rgba(255,122,0,0.15) 100%)' }}
        data-testid="logiscop-hero"
      >
        <div className="max-w-[1160px] mx-auto grid md:grid-cols-2 gap-10 items-center">
          <div>
            <span
              className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wider"
              style={{ background: 'rgba(255,122,0,0.15)', color: '#FF7A00', border: '1px solid rgba(255,122,0,0.4)' }}
            >
              <Truck className="w-3 h-3" /> {i18n.t('logiscop.badge')}
            </span>
            <h1
              className="font-display text-5xl md:text-6xl font-bold leading-[1.05] mt-4 mb-3 tracking-tight"
              style={{ color: '#fff' }}
            >
              <span style={{ color: '#5B2E8C' }}>LOGI</span>'<span style={{ color: '#FF7A00' }}>SCOP</span>
            </h1>
            <p className="text-base text-white/80 max-w-[55ch] mb-6">
              {i18n.t('logiscop.hero_desc')}
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/inscription">
                <button
                  className="inline-flex items-center gap-2 rounded-[14px] px-5 py-3 text-sm font-semibold transition-all hover:translate-y-[-1px]"
                  style={{ background: 'linear-gradient(135deg, #5B2E8C, #FF7A00)', color: '#fff', boxShadow: '0 10px 30px rgba(76,42,110,0.4)' }}
                  data-testid="logiscop-cta-partner"
                >
                  {i18n.t('logiscop.devenir_partenaire')} <ArrowRight className="w-4 h-4" />
                </button>
              </Link>
              <Link to="/" className="inline-flex items-center gap-2 rounded-[14px] px-5 py-3 text-sm font-medium border border-white/15 hover:bg-white/[0.05] transition-all">
                {i18n.t('logiscop.retour_ecosysteme')}
              </Link>
            </div>
          </div>
          <div className="relative">
            <div className="grid grid-cols-2 gap-4">
              <Stat icon={Package} label={i18n.t('logiscop.volumes_2026')} value="280 t" tone="bleu" />
              <Stat icon={Clock} label={i18n.t('logiscop.delai_moyen')} value="48 h" tone="orange" />
              <Stat icon={MapPin} label={i18n.t('logiscop.dom_couverts')} value="4" tone="bleu" />
              <Stat icon={ShieldCheck} label={i18n.t('logiscop.fiabilite')} value="98,2%" tone="orange" />
            </div>
          </div>
        </div>
      </section>

      {/* Process */}
      <section className="px-5 py-12">
        <div className="max-w-[1160px] mx-auto">
          <h2 className="text-3xl font-display font-bold text-center mb-10">{i18n.t('logiscop.un_flux_trois_etapes')}</h2>
          <div className="grid md:grid-cols-3 gap-5">
            <Step
              num="01"
              tone="bleu"
              title={i18n.t('logiscop.consolidation')}
              desc={i18n.t('logiscop.agregation_des_commandes_cooperatives')}
            />
            <Step
              num="02"
              tone="orange"
              title={i18n.t('logiscop.acheminement')}
              desc={i18n.t('logiscop.liaison_maritime_antilles_reunion')}
            />
            <Step
              num="03"
              tone="bleu"
              title={i18n.t('logiscop.distribution_relais')}
              desc={i18n.t('logiscop.livraison_directe_aux_relais')}
            />
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}

const Stat = ({ icon: Icon, label, value, tone }) => {
  const color = tone === 'bleu' ? '#5B2E8C' : '#FF7A00';
  return (
    <div className="rounded-[16px] p-4 border border-white/10 backdrop-blur-sm" style={{ background: `${color}10` }}>
      <Icon className="w-5 h-5 mb-2" style={{ color }} />
      <div className="text-2xl font-display font-bold">{value}</div>
      <div className="text-[11px] uppercase tracking-wider text-white/50 mt-1">{label}</div>
    </div>
  );
};

const Step = ({ num, title, desc, tone }) => {
  const color = tone === 'bleu' ? '#5B2E8C' : '#FF7A00';
  return (
    <div className="rounded-[18px] p-5 border border-white/10" style={{ background: 'rgba(255,255,255,0.03)' }}>
      <div className="font-display text-3xl font-bold mb-2" style={{ color }}>{num}</div>
      <h3 className="text-lg font-display font-bold mb-2">{title}</h3>
      <p className="text-sm text-white/70 leading-relaxed">{desc}</p>
    </div>
  );
};
