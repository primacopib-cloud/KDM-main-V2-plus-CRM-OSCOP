import React from 'react';
import { Link } from 'react-router-dom';
import { usePublicPlans } from '../hooks/usePublicPlans';
import { ArrowRight, Wallet } from 'lucide-react';
import i18n from '@/i18n';

const PricingSection = () => {
  const { plans } = usePublicPlans();
  return (
    <section id="offres" className="py-8 px-5">
      <div className="max-w-[1160px] mx-auto">
        <div className="section-title mb-6">
          <div>
            <span className="pill mb-3 inline-flex">
              <span className="font-bold text-[#D9B35A]">{i18n.t('offers.abonnements_o_scop')}</span>
            </span>
            <h3 className="text-[22px] font-bold tracking-tight mt-3 mb-1">{i18n.t('offers.acces_kdmarche_b2b')}</h3>
            <p className="text-white/70 text-sm m-0">{i18n.t('offers.choisissez_la_formule')}</p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-3.5">
          {plans.map((plan) => {
            const features = i18n.t(`offers.features_${plan.id.replace(/-/g, '_')}`, { returnObjects: true });
            return (
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
              <div 
                className="absolute -top-[55%] -right-[35%] w-80 h-80 pointer-events-none"
                style={{
                  background: 'radial-gradient(circle at 40% 40%, rgba(217,179,90,0.18), transparent 60%)',
                  transform: 'rotate(12deg)'
                }}
              ></div>
              
              {plan.popular && (
                <span className="ribbon absolute top-3.5 right-3.5">{i18n.t('offers.recommande')}</span>
              )}
              
              <div className="relative">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-extrabold text-base tracking-wide">{plan.name}</div>
                    <span className="text-xs tracking-wider uppercase text-white/75 border border-white/12 bg-white/[0.04] px-2.5 py-1.5 rounded-full inline-block mt-2">
                      {i18n.t('lists.mensuel')}
                    </span>
                  </div>
                </div>
                
                <div className="text-[34px] font-black tracking-tight mt-2">
                  {plan.price}<span className="text-lg font-normal text-white/65">€</span>
                </div>
                <div className="text-white/65 text-[13px] -mt-1">{i18n.t('offers.ht_mois')}</div>
              </div>
              
              <ul className="m-0 p-0 list-none grid gap-2.5 relative">
                {(Array.isArray(features) ? features : plan.features).map((feature) => (
                  <li key={feature} className="flex gap-2.5 items-start text-white/75 text-[13px]">
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
                    {i18n.t('offers.choisir_cette_offre')}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </Link>
              </div>
              
              {!plan.popular && (
                <div className="text-white/60 text-xs border-t border-white/10 pt-3 mt-1 relative">
                  {i18n.t('offers.sans_engagement_de_duree')}
                </div>
              )}
            </div>
            );
          })}
        </div>

        {/* Wallet Credits Info */}
        <div className="mt-6 p-5 rounded-[22px] glass-panel-soft">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-2xl bg-[#D9B35A]/10 border border-[#D9B35A]/20">
              <Wallet className="w-6 h-6 text-[#D9B35A]" />
            </div>
            <div>
              <h4 className="font-bold text-base mb-1">{i18n.t('offers.wallet_credits_oscop')}</h4>
              <p className="text-white/70 text-sm mb-0">
                {i18n.t('offers.credits_financent_detail')}
              </p>
              <p className="text-white/50 text-xs mt-2 p-2.5 rounded-xl bg-black/20 inline-block">
                {i18n.t('offers.credits_warning')}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PricingSection;
