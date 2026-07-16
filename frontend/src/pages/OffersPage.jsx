import React from 'react';
import { Link } from 'react-router-dom';
import { subscriptionPlans, walletCreditsUsage } from '../data/mock';
import { ArrowRight, ArrowLeft, Wallet, Info } from 'lucide-react';
import Header from '../components/Header';
import Footer from '../components/Footer';

const OffersPage = () => {
  return (
    <div className="min-h-screen">
      <Header />
      
      {/* Hero */}
      <section className="pt-32 pb-8 px-5">
        <div className="max-w-4xl mx-auto text-center">
          <span className="pill mb-4 inline-flex">
            <span className="font-bold text-[#D9B35A]">Abonnements O'SCOP</span>
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-tight">
            Choisissez votre accès <span className="text-[#D9B35A]">à la Centrale</span>
          </h1>
          <p className="text-white/70 text-lg">
            Accédez aux prix structurels B2B mutualisés via KDMARCHE
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-8 px-5">
        <div className="max-w-[1160px] mx-auto">
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
                  
                  <div className="text-[42px] font-black tracking-tight mt-4">
                    {plan.price}<span className="text-lg font-normal text-white/65">€</span>
                  </div>
                  <div className="text-white/65 text-[13px] -mt-1">HT / {plan.period}</div>
                </div>
                
                <ul className="m-0 p-0 list-none grid gap-2.5 relative mt-4">
                  {plan.features.map((feature) => (
                    <li key={`${plan.id}-${feature}`} className="flex gap-2.5 items-start text-white/75 text-[13px]">
                      <div className={`icon-dot ${plan.popular ? 'gold' : 'green'} mt-0.5`}></div>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
                
                <div className="mt-auto pt-4 relative">
                  <Link to={`/inscription?plan=${plan.id}`}>
                    <button 
                      className={`w-full inline-flex items-center justify-center gap-2 rounded-[14px] px-4 py-3.5 text-sm font-semibold ${
                        plan.popular ? 'btn-gold' : 'btn-ghost'
                      }`}
                    >
                      S'inscrire maintenant
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
        </div>
      </section>

      {/* Wallet Credits Section */}
      <section className="py-8 px-5">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-6">
            <span className="badge-status mb-4 inline-flex">
              <Wallet className="w-3.5 h-3.5 text-[#D9B35A]" />
              <span>Wallet Crédits</span>
            </span>
            <h2 className="text-2xl font-bold mt-3 mb-2">Système de crédits O'SCOP</h2>
            <p className="text-white/70 text-sm">Complémentaire à votre abonnement</p>
          </div>
          
          <div className="glass-panel rounded-[22px] p-6">
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="font-semibold text-white/90 mb-4 text-sm uppercase tracking-wider">Les crédits financent :</h3>
                <ul className="space-y-3">
                  {walletCreditsUsage.map((item) => (
                    <li key={item} className="flex items-center gap-3">
                      <div className="check-icon"></div>
                      <span className="text-white/75 text-sm">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <div className="glass-panel-soft rounded-2xl p-5">
                <div className="flex items-start gap-3 mb-4">
                  <Info className="w-5 h-5 text-white/50 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-white/70">
                    Les crédits sont <strong className="text-white/90">sans lien avec le prix des produits</strong>.
                    Ils n'impactent jamais le prix des produits vendus par KDMARCHE.
                  </p>
                </div>
                
                <div className="border-t border-white/10 pt-4 mt-4">
                  <p className="text-xs text-white/50 mb-2">Recharge disponible</p>
                  <div className="flex flex-wrap gap-2">
                    {[50, 100, 200, 500].map((amount) => (
                      <span 
                        key={amount} 
                        className="pill cursor-pointer hover:bg-white/[0.06] hover:border-[#D9B35A]/30 transition-all"
                      >
                        {amount} crédits
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-12 px-5">
        <div 
          className="max-w-4xl mx-auto rounded-[26px] p-8 text-center relative overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(217,179,90,0.15), rgba(212,175,55,0.10))',
            border: '1px solid rgba(217,179,90,0.25)'
          }}
        >
          <h2 className="text-2xl md:text-3xl font-bold mb-3">
            Prêt à rejoindre la centrale d'achats ESS ?
          </h2>
          <p className="text-white/70 mb-6 text-lg">
            Bénéficiez de prix structurels B2B jusqu'à -50%
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/inscription">
              <button className="btn-gold inline-flex items-center justify-center gap-2 rounded-[14px] px-6 py-3.5 text-sm font-semibold">
                Créer mon compte
                <ArrowRight className="w-4 h-4" />
              </button>
            </Link>
            <Link to="/#contact">
              <button className="btn-ghost inline-flex items-center justify-center gap-2 rounded-[14px] px-6 py-3.5 text-sm font-semibold">
                Demander un devis
              </button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default OffersPage;
