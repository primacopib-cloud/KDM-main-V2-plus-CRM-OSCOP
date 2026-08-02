import i18n from '@/i18n';
import { Link } from 'react-router-dom';
import { Zap, ShieldCheck, Users, CheckCircle2, ArrowRight } from 'lucide-react';
import { trackCta } from '../../services/ctaTracking';

/* Section publique : dispositif API coopérative B2B2C (violet KD MARCHÉ Pro + or O'SCOP) */
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
                to="/adhesion-vendeur"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-white border border-white/25 hover:bg-white/5"
                data-testid="coop-cta-adhesion"
                onClick={() => trackCta('adherer_centrale_api')}
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
