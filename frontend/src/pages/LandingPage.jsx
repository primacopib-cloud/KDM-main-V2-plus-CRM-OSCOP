import i18n from '@/i18n';
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { downloadOffer, lolodriveAPI } from '../services/api';
import { 
  Download, 
  ArrowRight, 
  CheckCircle2,
  XCircle,
  Zap,
  ShieldCheck,
  Users,
  Truck,
  CreditCard,
  Building2,
  MapPin
} from 'lucide-react';
import { partners, subscriptionPlans, logisticsSteps } from '../data/mock';
import PricingSection from '../components/PricingSection';
import PartnersSection from '../components/PartnersSection';
import LogisticsSection from '../components/LogisticsSection';
import ContactForm from '../components/ContactForm';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import LoloPointsMap from '../components/LoloPointsMap';
import TerritorySelector from '../components/TerritorySelector';

const LandingPage = () => {
  return (
    <div className="min-h-screen">
      <NavBar />
      
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
              
              <h2 className="text-[40px] leading-[1.05] font-bold tracking-tight my-2.5">
                Communityplace <span className="text-[#D9B35A]">{i18n.t('landing.cooperative_b2b2c')}</span>
              </h2>
              
              <p className="text-white/75 text-base max-w-[60ch] m-0">
                {i18n.t('landing.official_statement')}
              </p>
              
              {/* Actions */}
              <div className="flex gap-3 flex-wrap mt-5">
                <Link to="/tarifs">
                  <button
                    className="force-white inline-flex items-center justify-center gap-2.5 rounded-[14px] px-4 py-3 text-sm font-semibold text-white shadow-lg"
                    style={{ background: 'linear-gradient(135deg, #5B2E8C 0%, #2A1045 100%)' }}
                    data-testid="hero-cta-acces-pro"
                  >
                    {i18n.t('landing.decouvrir_l_acces_pro')}
                    <ArrowRight className="w-4 h-4" />
                  </button>
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
            <div className="glass-panel-soft rounded-[26px] p-5 flex flex-col gap-3.5" style={{ boxShadow: '0 16px 50px rgba(0,0,0,0.35)' }}>
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

      {/* Partners Section */}
      <PartnersSection />

      {/* Access Condition */}
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
                <div key={`no-pass-${item.slice(0, 32)}`} className="flex items-center gap-2 text-[#FF6B6B] text-sm">
                  <div className="cross-icon"></div>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <PricingSection />

      {/* Logistics Section */}
      <LogisticsSection />

      {/* Compliance Section */}
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

      {/* Réseau LOLODRIVE — carte publique */}
      <PublicLolodriveMapSection />

      {/* API Coopérative B2B2C — dispositif institutionnel */}
      <CooperativeApiSection />

      {/* Contact Section */}
      <section id="contact" className="py-8 px-5">
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

      <Footer />
    </div>
  );
};

export default LandingPage;

/* =================================================================
 * Section publique : carte du Reseau LOLODRIVE (acquisition / contact)
 * Named export so unit tests can mount it in isolation.
 * ================================================================= */

export const PublicLolodriveMapSection = () => {
  const [points, setPoints] = useState([]);
  const [territories, setTerritories] = useState([]);
  const [territory, setTerritory] = useState(null);
  const [selected, setSelected] = useState(null);

  // Load territories once on mount
  useEffect(() => {
    lolodriveAPI.listTerritories()
      .then((t) => setTerritories(t.territories || []))
      .catch(() => {});
  }, []);

  // Load points whenever territory changes
  useEffect(() => {
    lolodriveAPI.listLoloPoints({ territory: territory || undefined })
      .then((p) => setPoints(p.points || []))
      .catch(() => setPoints([]));
  }, [territory]);

  const activateHere = (point) => {
    // Persist for the registration / PASS purchase funnel
    try {
      localStorage.setItem('kdm_preselected_point', JSON.stringify({
        id: point.id, code: point.code, name: point.name, territory: point.territory,
      }));
      if (point.territory) localStorage.setItem('kdm_territory', point.territory);
    } catch (_) {
      // localStorage may be unavailable (private mode, quota exceeded) — preselection is non-critical.
    }
  };

  return (
    <section id="reseau-lolodrive" className="py-10 px-5" data-testid="public-lolodrive-section">
      <div className="max-w-[1160px] mx-auto">
        <div className="text-center mb-5">
          <span className="badge-status mb-3 inline-flex">
            <span className="dot pulse-glow"></span>
            {i18n.t('landing.reseau_lolodrive')}
          </span>
          <h3 className="text-[28px] font-display font-bold tracking-tight mt-2 mb-2">
            {i18n.t('landing.find_relay_prefix')} <span className="text-or-metallise">{i18n.t('landing.le_plus_proche')}</span>
          </h3>
          <p className="text-white/70 text-sm max-w-[60ch] mx-auto">
            <strong>{i18n.t('landing.lolodrive_by_o_scop')}</strong>{i18n.t('landing.lolodrive_desc_mid')}<strong>{i18n.t('landing.cliquez_sur_un_relais')}</strong>{i18n.t('landing.lolodrive_desc_suffix')}
          </p>
        </div>

        <div className="glass-panel rounded-[18px] p-4 mb-3 flex flex-wrap items-center justify-between gap-3">
          <TerritorySelector
            territories={territories}
            value={territory}
            onChange={setTerritory}
            testId="public-territory-selector"
          />
          <div className="text-xs text-white/60 inline-flex items-center gap-1.5" data-testid="public-points-count">
            <MapPin className="w-3.5 h-3.5 text-or-metallise" />
            <strong className="text-white/90">{points.length}</strong> {points.length > 1 ? i18n.t('landing.relay_count_active') : i18n.t('landing.relay_count_active_one')}
          </div>
        </div>

        <LoloPointsMap points={points} territory={territory} height="460px" onSelect={(p) => setSelected(p)} />

        <div className="mt-3 text-center">
          <Link to="/inscription">
            <button className="btn-gold inline-flex items-center justify-center gap-2.5 rounded-[14px] px-5 py-3 text-sm font-semibold" data-testid="join-network-btn">
              {i18n.t('landing.devenir_relais_lolodrive')}
              <ArrowRight className="w-4 h-4" />
            </button>
          </Link>
        </div>

        {/* Fiche relais — modal coopératif */}
        {selected && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
            onClick={() => setSelected(null)}
            data-testid="relay-detail-modal"
          >
            <div
              className="glass-panel rounded-[20px] p-6 max-w-md w-full border border-or-metallise/30"
              onClick={(e) => e.stopPropagation()}
              style={{ background: 'linear-gradient(180deg, rgba(15,16,24,0.95), rgba(7,10,16,0.98))' }}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-or-metallise mb-1">{i18n.t('landing.relais_lolodrive')}</div>
                  <h3 className="text-2xl font-display font-bold leading-tight">{selected.name}</h3>
                  <div className="font-mono text-xs text-white/40 mt-1">{selected.code} · {selected.territory}</div>
                </div>
                <button onClick={() => setSelected(null)} className="text-white/40 hover:text-white text-xl leading-none px-2" data-testid="close-relay-detail">×</button>
              </div>
              <div className="separator-premium"><span className="dot"></span></div>
              <div className="space-y-2 text-sm mb-5">
                <div className="flex items-start gap-2"><MapPin className="w-4 h-4 mt-0.5 text-violet-premium flex-shrink-0" /><span>{selected.address || '—'}, {selected.city || '—'}</span></div>
                {selected.zone_name && <div className="text-xs text-white/50 ml-6">{i18n.t('landing.zone_label')} {selected.zone_name}</div>}
              </div>
              <div className="grid grid-cols-2 gap-3 mb-5 text-center">
                <div className="rounded-lg bg-vert-lime/10 border border-vert-lime/30 p-3">
                  <div className="text-[10px] uppercase tracking-wider text-vert-lime mb-0.5">{i18n.t('landing.drive')}</div>
                  <div className="text-xs text-white/80">{i18n.t('landing.retrait_cooperatif')}</div>
                </div>
                <div className="rounded-lg bg-violet-premium/10 border border-violet-premium/30 p-3">
                  <div className="text-[10px] uppercase tracking-wider text-violet-premium mb-0.5">{i18n.t('landing.livraison')}</div>
                  <div className="text-xs text-white/80">{i18n.t('landing.livraison_locale')}</div>
                </div>
              </div>
              <Link to="/inscription" onClick={() => activateHere(selected)} data-testid="activate-pass-here-btn">
                <button className="btn-gold w-full inline-flex items-center justify-center gap-2 rounded-[14px] py-3 text-sm font-semibold">
                  {i18n.t('landing.activer_mon_pass_ici')}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </Link>
              <p className="text-[11px] text-white/40 mt-3 text-center">
                {i18n.t('landing.vous_serez_redirige_vers')}
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};


/* =================================================================
 * Section publique : dispositif API coopérative B2B2C
 * (Ancrage institutionnel — palette violet KD MARCHÉ Pro + or O'SCOP)
 * ================================================================= */
export const CooperativeApiSection = () => {
  return (
    <section
      id="cooperative-api"
      className="on-dark py-16 px-5 relative"
      style={{
        background:
          'radial-gradient(1000px 500px at 10% 0%, rgba(245,166,35,0.10), transparent 60%), ' +
          'radial-gradient(800px 480px at 90% 100%, rgba(217,179,90,0.12), transparent 65%), ' +
          'linear-gradient(180deg, #2a0c4a 0%, #4a1776 55%, #2a0c4a 100%)',
      }}
      data-testid="cooperative-api-section"
    >
      <div className="max-w-[1160px] mx-auto">
        <div className="grid lg:grid-cols-[1fr_1.1fr] gap-10 items-center">
          {/* LEFT: message institutionnel */}
          <div>
            <span
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] uppercase tracking-[0.18em] font-bold mb-5"
              style={{
                background: 'rgba(245,166,35,0.14)',
                border: '1px solid rgba(245,166,35,0.4)',
                color: '#F5A623',
              }}
            >
              <Zap className="w-3 h-3" />
              {i18n.t('landing.api_cooperative_b2b2c')}
            </span>
            <h3
              className="text-4xl lg:text-5xl font-serif font-semibold text-white leading-[1.05] mb-5"
              style={{ fontFamily: '"Playfair Display", "Cormorant Garamond", serif' }}
            >
              {i18n.t('landing.acces_pro')} <span className="text-[#F5A623]">{i18n.t('landing.mutualise')}</span>
            </h3>
            <p className="text-white/80 text-base leading-relaxed mb-4">
              {i18n.t('landing.api_p1_prefix')}
              <strong className="text-white">{i18n.t('landing.acces_cooperatif')}</strong>{i18n.t('landing.api_p1_suffix')}
            </p>
            <p className="text-white/60 text-sm leading-relaxed mb-6">
              {i18n.t('landing.api_p2')}<em>{i18n.t('landing.api_p2_em')}</em>
            </p>

            <div className="flex flex-wrap gap-3 mb-8">
              <Link
                to="/tarifs"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-[#2a0c4a] shadow-lg"
                style={{ background: 'linear-gradient(135deg, #F5A623 0%, #D9B35A 100%)' }}
                data-testid="coop-cta-tarifs"
              >
                {i18n.t('landing.acceder_api')} <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/adhesion"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-white border border-white/25 hover:bg-white/5"
                data-testid="coop-cta-adhesion"
              >
                {i18n.t('landing.adherer_a_la_centrale')}
              </Link>
            </div>

            {/* Pillars */}
            <div className="grid grid-cols-2 gap-3 max-w-lg">
              {[
                { icon: ShieldCheck, label: i18n.t('landing.securise'), desc: i18n.t('landing.acces_authentifie_et_protege') },
                { icon: Users, label: i18n.t('pricing.mutualise'), desc: i18n.t('landing.conditions_issues_du_collectif') },
                { icon: CheckCircle2, label: i18n.t('landing.cooperatif'), desc: i18n.t('landing.modele_ethique_et_solidaire') },
                { icon: Zap, label: i18n.t('landing.performant'), desc: i18n.t('landing.services_selectionnes') },
              ].map((p) => {
                const Icon = p.icon;
                return (
                  <div
                    key={p.label}
                    className="p-3 rounded-xl"
                    style={{
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(245,166,35,0.2)',
                    }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className="w-4 h-4 text-[#F5A623]" />
                      <p className="text-xs uppercase tracking-wider font-bold text-white">{p.label}</p>
                    </div>
                    <p className="text-[11px] text-white/55">{p.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* RIGHT: visuel high-tech */}
          <div className="relative">
            <div
              className="relative rounded-2xl overflow-hidden"
              style={{
                border: '1px solid rgba(245,166,35,0.35)',
                boxShadow: '0 24px 64px rgba(74,23,118,0.5)',
              }}
              data-testid="api-hightech-visual"
            >
              <img
                src="/images/api-hightech.webp"
                alt="Plateforme API coopérative sécurisée KDMARCHE Pro"
                className="w-full h-auto object-cover block"
              />
            </div>

            {/* Legend below the visual */}
            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              {(i18n.t('landing.chips', { returnObjects: true }) || []).map((t) => (
                <div
                  key={t}
                  className="px-2 py-2 rounded-lg text-[10px] uppercase tracking-wider text-white/60 font-medium"
                  style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  {t}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
