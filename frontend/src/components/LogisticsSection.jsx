import React from 'react';
import { exwJourney, rarJourney } from '../data/mock';
import i18n from '@/i18n';

const getStepStyle = (responsible) => {
  switch (responsible) {
    case "O'SCOP":
      return { color: '#D4AF37', bg: 'rgba(212,175,55,0.08)', border: 'rgba(212,175,55,0.20)' };
    case 'KDMARCHE':
      return { color: '#D9B35A', bg: 'rgba(217,179,90,0.08)', border: 'rgba(217,179,90,0.20)' };
    case "LOGI'SCOP":
      return { color: '#4FD1A5', bg: 'rgba(79,209,165,0.10)', border: 'rgba(79,209,165,0.35)' };
    case 'Client':
      return { color: '#7FB2E5', bg: 'rgba(31,77,135,0.18)', border: 'rgba(31,77,135,0.55)' };
    default:
      return { color: 'rgba(255,255,255,0.75)', bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.12)' };
  }
};

const JourneyRow = ({ title, badge, steps, testId, image, imageAlt, objectPosition = 'center' }) => (
  <div className="mb-6" data-testid={testId}>
    {image && (
      <div className="relative rounded-[22px] overflow-hidden mb-4 group" data-testid={`${testId}-hero`}>
        <img src={image} alt={imageAlt || title} loading="lazy" style={{ objectPosition, filter: 'brightness(1.12) saturate(1.06)' }}
          className="w-full h-44 sm:h-56 object-cover transition-transform duration-[1.6s] ease-out group-hover:scale-[1.06]" />
        <div className="absolute inset-0 sm:hidden" style={{ background: 'linear-gradient(90deg, rgba(12,12,16,0.58) 0%, rgba(12,12,16,0.24) 60%, rgba(12,12,16,0.06) 100%)' }} />
        <div className="absolute inset-0 hidden sm:block" style={{ background: 'linear-gradient(90deg, rgba(12,12,16,0.34) 0%, rgba(12,12,16,0.10) 55%, rgba(12,12,16,0.02) 100%)' }} />
        <div className="absolute inset-0 flex flex-col justify-center px-6 sm:px-9">
          <h4 className="text-lg sm:text-2xl font-bold tracking-wide uppercase text-white m-0 drop-shadow-lg">{title}</h4>
          {badge && (
            <span className="mt-2 w-fit text-[11px] px-2.5 py-1 rounded-full font-bold text-[#1F0A33] shadow"
              style={{ background: 'linear-gradient(135deg, #F5A623, #D9B35A)' }}>
              {badge}
            </span>
          )}
        </div>
      </div>
    )}
    {!image && (
      <div className="flex items-center gap-2.5 mb-3 flex-wrap">
        <h4 className="text-sm font-bold tracking-wide uppercase text-white/90 m-0">{title}</h4>
        {badge && (
          <span className="text-[10px] px-2 py-0.5 rounded-full font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/30">
            {badge}
          </span>
        )}
      </div>
    )}
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2.5">
      {steps.map((step, index) => {
        const style = getStepStyle(step.responsible);
        return (
          <div key={step.step}
            className="rounded-[18px] p-3.5 relative min-h-[130px] flex flex-col"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.10)' }}>
            <div className="font-mono font-black text-xs text-white/75 tracking-wider">
              {String(index + 1).padStart(2, '0')}
            </div>
            <h5 className="text-[12px] tracking-wide uppercase text-white/85 font-semibold my-2 leading-snug">
              {step.step}
            </h5>
            <div className="mt-auto">
              <span className="text-[11px] px-2 py-1 rounded-full font-semibold inline-block"
                style={{ background: style.bg, border: `1px solid ${style.border}`, color: style.color }}>
                {step.responsible === 'Client' ? i18n.t('logistics.client', 'Client') : step.responsible}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  </div>
);

const LogisticsSection = () => (
  <section className="py-8 px-5">
    <div className="max-w-[1160px] mx-auto">
      <div className="section-title mb-6">
        <div>
          <h3 className="text-[22px] font-bold tracking-tight m-0">{i18n.t('logistics.title', 'Logistique et facturation')}</h3>
          <p className="text-white/70 text-sm mt-1 m-0">Deux parcours distincts selon le mode de règlement choisi.</p>
        </div>
      </div>

      <JourneyRow
        title="Parcours 1 — Commande EXW"
        badge="Règlement à l'enlèvement"
        steps={exwJourney}
        testId="journey-exw"
        image="https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/b30b2453209512b1e3870b267a5354e954559464eec55fa287521ee93e988956.jpeg"
        imageAlt="Enlèvement EXW à l'entrepôt — acheteur professionnel"
      />
      <JourneyRow
        title="Parcours 2 — Règlement à Réception Pro"
        badge="Sans acompte · sous plafond"
        steps={rarJourney}
        testId="journey-rar"
        image="https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/aa306afb6ddf4a87632637b08bf35bfa740b7d6b7584b52fc09ba53a330b1052.jpeg"
        imageAlt="Validation électronique de la réception — livraison professionnelle"
        objectPosition="32% center"
      />

      {/* Legend */}
      <div className="mt-2 flex flex-wrap justify-center gap-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#D4AF37]"></div>
          <span className="text-xs text-white/65">{i18n.t('logistics.legend_oscop', "O'SCOP — accès coopératif")}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#D9B35A]"></div>
          <span className="text-xs text-white/65">{i18n.t('logistics.legend_kdm', 'KDMARCHÉ — vente & facturation')}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: '#4FD1A5' }}></div>
          <span className="text-xs text-white/65">LOGI'SCOP — livraison certifiée</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: '#1F4D87' }}></div>
          <span className="text-xs text-white/65">{i18n.t('logistics.legend_client', 'Client — acheteur Pro')}</span>
        </div>
      </div>
    </div>
  </section>
);

export default LogisticsSection;
