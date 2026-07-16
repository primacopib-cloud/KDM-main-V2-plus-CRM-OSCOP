import React from 'react';
import { logisticsSteps } from '../data/mock';
import i18n from '@/i18n';

const LogisticsSection = () => {
  const stepLabels = i18n.t('logistics.steps', { returnObjects: true });

  const getStepStyle = (responsible) => {
    switch (responsible) {
      case "O'SCOP":
        return { color: '#D4AF37', bg: 'rgba(212,175,55,0.08)', border: 'rgba(212,175,55,0.20)' };
      case 'KDMARCHE':
        return { color: '#D9B35A', bg: 'rgba(217,179,90,0.08)', border: 'rgba(217,179,90,0.20)' };
      case 'Client':
        return { color: '#1F4D87', bg: 'rgba(31,77,135,0.10)', border: 'rgba(31,77,135,0.45)' };
      default:
        return { color: 'rgba(255,255,255,0.75)', bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.12)' };
    }
  };

  return (
    <section className="py-8 px-5">
      <div className="max-w-[1160px] mx-auto">
        <div className="section-title mb-6">
          <div>
            <h3 className="text-[22px] font-bold tracking-tight m-0">{i18n.t('logistics.title')}</h3>
            <p className="text-white/70 text-sm mt-1 m-0">{i18n.t('logistics.subtitle')}</p>
          </div>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
          {logisticsSteps.map((step, index) => {
            const style = getStepStyle(step.responsible);
            return (
              <div 
                key={index}
                className="rounded-[18px] p-3.5 relative min-h-[140px] flex flex-col"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.10)'
                }}
              >
                <div className="font-mono font-black text-xs text-white/75 tracking-wider">
                  {String(index + 1).padStart(2, '0')}
                </div>
                <h4 className="text-[13px] tracking-wide uppercase text-white/85 font-semibold my-2">
                  {(Array.isArray(stepLabels) && stepLabels[index]) || step.step}
                </h4>
                <div className="mt-auto">
                  <span 
                    className="text-xs px-2.5 py-1.5 rounded-full font-semibold inline-block"
                    style={{
                      background: style.bg,
                      border: `1px solid ${style.border}`,
                      color: style.color
                    }}
                  >
                    {step.responsible === 'Client' ? i18n.t('logistics.client') : step.responsible}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-4 flex flex-wrap justify-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#D4AF37]"></div>
            <span className="text-xs text-white/65">{i18n.t('logistics.legend_oscop')}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#D9B35A]"></div>
            <span className="text-xs text-white/65">{i18n.t('logistics.legend_kdm')}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ background: '#1F4D87' }}></div>
            <span className="text-xs text-white/65">{i18n.t('logistics.legend_client')}</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default LogisticsSection;
