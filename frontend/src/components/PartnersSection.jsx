import React from 'react';
import { partners } from '../data/mock';
import { ShoppingCart, Settings } from 'lucide-react';
import i18n from '@/i18n';

const PartnersSection = () => {
  const kdmResponsibilities = i18n.t('partners.kdm_responsibilities', { returnObjects: true });
  const kdmAssumes = i18n.t('partners.kdm_assumes_list', { returnObjects: true });
  const oscopResponsibilities = i18n.t('partners.oscop_responsibilities', { returnObjects: true });
  const oscopRestrictions = i18n.t('partners.oscop_restrictions', { returnObjects: true });

  return (
    <section className="py-8 px-5">
      <div className="max-w-[1160px] mx-auto">
        <div className="text-center mb-6">
          <span className="pill mb-3 inline-flex">
            <span className="font-bold text-white/90">{i18n.t('partners.badge')}</span>
          </span>
          <h3 className="text-[22px] font-bold tracking-tight mt-3 mb-2">{i18n.t('partners.title')}</h3>
          <p className="text-white/70 text-sm max-w-2xl mx-auto">
            {i18n.t('partners.subtitle')}
          </p>
          <p className="text-xs text-white/50 mt-1">
            {i18n.t('partners.note')}
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-3.5">
          {/* KDMARCHE Card */}
          <div className="glass-panel-soft rounded-[22px] p-5 relative overflow-hidden">
            <div 
              className="absolute top-0 left-0 right-0 h-1" 
              style={{ background: 'linear-gradient(90deg, #D9B35A, #F2D07A)' }}
            ></div>
            
            <div className="text-center mb-4">
              <img 
                src={partners.kdmarche.logo} 
                alt="KDMARCHE" 
                className="h-56 w-auto object-contain mx-auto mb-3"
                style={{ filter: 'drop-shadow(0 4px 12px rgba(217,179,90,0.4))' }}
              />
              <span className="pill">
                <ShoppingCart className="w-3 h-3" />
                <span className="text-[#D9B35A] font-semibold">{i18n.t('partners.kdm_badge')}</span>
              </span>
              <h4 className="text-base font-bold mt-3 text-white/90">{i18n.t('partners.kdm_role')}</h4>
            </div>
            
            <div className="space-y-4">
              <div>
                <h5 className="text-xs uppercase tracking-wider text-white/60 mb-2.5">{i18n.t('partners.role_label')}</h5>
                <ul className="space-y-2">
                  {(Array.isArray(kdmResponsibilities) ? kdmResponsibilities : []).map((item) => (
                    <li key={item} className="flex items-start gap-2.5 text-white/75 text-sm">
                      <div className="icon-dot gold mt-0.5"></div>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <div className="p-3.5 rounded-2xl" style={{ background: 'rgba(217,179,90,0.08)', border: '1px solid rgba(217,179,90,0.15)' }}>
                <h5 className="text-xs uppercase tracking-wider text-[#D9B35A] mb-2">{i18n.t('partners.kdm_assumes')}</h5>
                <div className="flex flex-wrap gap-1.5">
                  {(Array.isArray(kdmAssumes) ? kdmAssumes : []).map((item) => (
                    <span key={item} className="pill text-xs">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* O'SCOP Card */}
          <div className="glass-panel-soft rounded-[22px] p-5 relative overflow-hidden">
            <div 
              className="absolute top-0 left-0 right-0 h-1" 
              style={{ background: 'linear-gradient(90deg, #D4AF37, #7EE8B8)' }}
            ></div>
            
            <div className="text-center mb-4">
              <img 
                src={partners.oscop.logo} 
                alt="O'SCOP" 
                className="h-44 w-auto object-contain mx-auto mb-3"
                style={{ filter: 'drop-shadow(0 4px 12px rgba(212,175,55,0.4))' }}
              />
              <span className="pill">
                <Settings className="w-3 h-3" />
                <span className="text-[#D4AF37] font-semibold">{i18n.t('partners.oscop_badge')}</span>
              </span>
              <h4 className="text-base font-bold mt-3 text-white/90">{i18n.t('partners.oscop_role')}</h4>
            </div>
            
            <div className="space-y-4">
              <div>
                <h5 className="text-xs uppercase tracking-wider text-white/60 mb-2.5">{i18n.t('partners.role_exclusive')}</h5>
                <ul className="space-y-2">
                  {(Array.isArray(oscopResponsibilities) ? oscopResponsibilities : []).map((item) => (
                    <li key={item} className="flex items-start gap-2.5 text-white/75 text-sm">
                      <div className="icon-dot green mt-0.5"></div>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <div className="p-3.5 rounded-2xl" style={{ background: 'rgba(255,107,107,0.06)', border: '1px solid rgba(255,107,107,0.15)' }}>
                <h5 className="text-xs uppercase tracking-wider text-[#FF6B6B] mb-2">{i18n.t('partners.oscop_not')}</h5>
                <ul className="space-y-1.5">
                  {(Array.isArray(oscopRestrictions) ? oscopRestrictions : []).map((item) => (
                    <li key={item} className="flex items-center gap-2 text-[#FF6B6B]/80 text-sm">
                      <div className="cross-icon" style={{ width: '14px', height: '14px' }}></div>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PartnersSection;
