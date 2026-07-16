import React from 'react';
import { partners } from '../data/mock';
import { ShoppingCart, Settings } from 'lucide-react';

const PartnersSection = () => {
  return (
    <section className="py-8 px-5">
      <div className="max-w-[1160px] mx-auto">
        <div className="text-center mb-6">
          <span className="pill mb-3 inline-flex">
            <span className="font-bold text-white/90">Logique du partenariat</span>
          </span>
          <h3 className="text-[22px] font-bold tracking-tight mt-3 mb-2">Séparation stricte des fonctions</h3>
          <p className="text-white/70 text-sm max-w-2xl mx-auto">
            Un seul vend les produits (KDMARCHE) • L'autre ne vend rien (O'SCOP)
          </p>
          <p className="text-xs text-white/50 mt-1">
            Ce cloisonnement est volontaire, contractuel et opposable.
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
                <span className="text-[#D9B35A] font-semibold">B2B Opérationnel</span>
              </span>
              <h4 className="text-base font-bold mt-3 text-white/90">{partners.kdmarche.role}</h4>
            </div>
            
            <div className="space-y-4">
              <div>
                <h5 className="text-xs uppercase tracking-wider text-white/60 mb-2.5">Rôle</h5>
                <ul className="space-y-2">
                  {partners.kdmarche.responsibilities.map((item, index) => (
                    <li key={index} className="flex items-start gap-2.5 text-white/75 text-sm">
                      <div className="icon-dot gold mt-0.5"></div>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <div className="p-3.5 rounded-2xl" style={{ background: 'rgba(217,179,90,0.08)', border: '1px solid rgba(217,179,90,0.15)' }}>
                <h5 className="text-xs uppercase tracking-wider text-[#D9B35A] mb-2">KDMARCHE assume seul</h5>
                <div className="flex flex-wrap gap-1.5">
                  {partners.kdmarche.assumes.map((item, index) => (
                    <span key={index} className="pill text-xs">
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
                <span className="text-[#D4AF37] font-semibold">Ingénierie ESS</span>
              </span>
              <h4 className="text-base font-bold mt-3 text-white/90">{partners.oscop.role}</h4>
            </div>
            
            <div className="space-y-4">
              <div>
                <h5 className="text-xs uppercase tracking-wider text-white/60 mb-2.5">Rôle exclusif</h5>
                <ul className="space-y-2">
                  {partners.oscop.responsibilities.map((item, index) => (
                    <li key={index} className="flex items-start gap-2.5 text-white/75 text-sm">
                      <div className="icon-dot green mt-0.5"></div>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <div className="p-3.5 rounded-2xl" style={{ background: 'rgba(255,107,107,0.06)', border: '1px solid rgba(255,107,107,0.15)' }}>
                <h5 className="text-xs uppercase tracking-wider text-[#FF6B6B] mb-2">O'SCOP ne fait pas</h5>
                <ul className="space-y-1.5">
                  {partners.oscop.restrictions.map((item, index) => (
                    <li key={index} className="flex items-center gap-2 text-[#FF6B6B]/80 text-sm">
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
