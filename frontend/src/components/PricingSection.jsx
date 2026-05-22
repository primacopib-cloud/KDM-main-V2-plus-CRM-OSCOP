import React from 'react';
import { Link } from 'react-router-dom';
import { subscriptionPlans } from '../data/mock';
import { ArrowRight, Wallet } from 'lucide-react';

const PricingSection = () => {
  return (
    <section id="offres" className="py-8 px-5">
      <div className="max-w-[1160px] mx-auto">
        <div className="section-title mb-6">
          <div>
            <span className="pill mb-3 inline-flex">
              <span className="font-bold text-[#D9B35A]">Abonnements O'SCOP</span>
            </span>
            <h3 className="text-[22px] font-bold tracking-tight mt-3 mb-1">Accès à KDMARCHE B2B</h3>
            <p className="text-white/70 text-sm m-0">Choisissez la formule adaptée pour accéder aux prix structurels mutualisés</p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-3.5">
          {subscriptionPlans.map((plan) => (
            <div 
              key={plan.id}
              className={`rounded-[22px] p-5 flex flex-col gap-3 relative overflow-hidden ${
                plan.popular ? 'card-highlight' : 'glass-panel-soft'
              }`}
              style={{
                background: plan.popular 
                  ? 'linear-gradient(180deg, rgba(217,179,90,0.11), rgba(255,255,255,0.03))'
                  : 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03))'
              }}
            >
              {/* Glow effect */}
              <div 
                className="absolute -top-[55%] -right-[35%] w-80 h-80 pointer-events-none"
                style={{
                  background: 'radial-gradient(circle at 40% 40%, rgba(217,179,90,0.18), transparent 60%)',
                  transform: 'rotate(12deg)'
                }}
              ></div>
              
              {plan.popular && (
                <span className="ribbon absolute top-3.5 right-3.5">Recommandé</span>
              )}
              
              <div className="relative">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-extrabold text-base tracking-wide">{plan.name}</div>
                    <span className="text-xs tracking-wider uppercase text-white/75 border border-white/12 bg-white/[0.04] px-2.5 py-1.5 rounded-full inline-block mt-2">
                      Mensuel
                    </span>
                  </div>
                </div>
                
                <div className="text-[34px] font-black tracking-tight mt-2">
                  {plan.price}<span className="text-lg font-normal text-white/65">€</span>
                </div>
                <div className="text-white/65 text-[13px] -mt-1">HT / {plan.period}</div>
              </div>
              
              <ul className="m-0 p-0 list-none grid gap-2.5 relative">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex gap-2.5 items-start text-white/75 text-[13px]">
                    <div className={`icon-dot ${plan.popular ? 'gold' : 'green'} mt-0.5`}></div>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              
              <div className="mt-auto pt-2 relative">
                <Link to={`/inscription?plan=${plan.id}`}>
                  <button 
                    className={`w-full inline-flex items-center justify-center gap-2 rounded-[14px] px-4 py-3 text-sm font-semibold ${
                      plan.popular ? 'btn-gold' : 'btn-ghost'
                    }`}
                  >
                    Choisir cette offre
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </Link>
              </div>
              
              {!plan.popular && (
                <div className="text-white/60 text-xs border-t border-white/10 pt-3 mt-1 relative">
                  Sans engagement de durée
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Wallet Credits Info */}
        <div className="mt-6 p-5 rounded-[22px] glass-panel-soft">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-2xl bg-[#D9B35A]/10 border border-[#D9B35A]/20">
              <Wallet className="w-6 h-6 text-[#D9B35A]" />
            </div>
            <div>
              <h4 className="font-bold text-base mb-1">Wallet Crédits O'SCOP</h4>
              <p className="text-white/70 text-sm mb-0">
                Les crédits financent <strong className="text-white/90">l'usage intensif</strong>, <strong className="text-white/90">l'accès prioritaire</strong>, <strong className="text-white/90">les zones supplémentaires</strong> et <strong className="text-white/90">les services ESS</strong>.
              </p>
              <p className="text-white/50 text-xs mt-2 p-2.5 rounded-xl bg-black/20 inline-block">
                ⚠️ Les crédits n'impactent jamais le prix des produits vendus par KDMARCHE.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PricingSection;
