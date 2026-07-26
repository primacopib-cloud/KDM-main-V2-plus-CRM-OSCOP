import { useEffect, useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { ShoppingBasket, Users, MapPin, ArrowRight, BadgeCheck, Ticket, BatteryCharging, Sparkles, CreditCard } from 'lucide-react';
import NavBar from '../components/NavBar';
import { FlashPromoBanner } from '../components/FlashPromoBanner';
import i18n from '@/i18n';
import { VitrineReviews } from '../components/pass/VitrineReviews';
import { authAPI } from '../services/api';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CARDS = [
  { icon: ShoppingBasket, key: 'card_essentiels' },
  { icon: Users, key: 'card_mutualise' },
  { icon: MapPin, key: 'card_relais' },
];

const RechargeCard = ({ plan }) => (
  <div className={`relative rounded-xl p-4 pt-5 text-center bg-white/[0.05] border ${plan.bonus_uc > 0 ? 'border-[#D9B35A]/60 shadow-[0_0_24px_rgba(217,179,90,0.12)]' : 'border-[#D9B35A]/20'}`}
    style={plan.bonus_uc > 0 ? { background: 'linear-gradient(180deg, rgba(217,179,90,0.10), rgba(255,255,255,0.04))' } : undefined}
    data-testid={`pass-recharge-${plan.id}`}>
    {plan.bonus_uc > 0 && (
      <span className="absolute -top-[13px] left-1/2 -translate-x-1/2 whitespace-nowrap inline-flex items-center gap-1 px-3 py-[4px] rounded-full text-[9px] font-bold uppercase tracking-[0.14em]"
        style={{
          background: 'linear-gradient(135deg, #F5E2A5 0%, #D9B35A 45%, #A67C2E 100%)',
          color: '#2A1045',
          border: '1px solid rgba(255,255,255,0.4)',
          boxShadow: '0 6px 16px rgba(217,179,90,0.45), inset 0 1px 0 rgba(255,255,255,0.55)',
        }}>
        <Sparkles className="w-2.5 h-2.5" /> +{plan.bonus_uc} UC {i18n.t('passPage.bonus')}
      </span>
    )}
    <p className="text-2xl font-bold text-[#E9CF8E]">{plan.price_eur} €</p>
    <p className="text-sm text-white/75 mt-0.5">{plan.uc + (plan.bonus_uc || 0) + (plan.promo_extra_uc || 0)} UC</p>
    {(plan.bonus_uc > 0 || plan.promo_extra_uc > 0) && (
      <p className="text-[10.5px] text-white/40">
        {plan.uc}{plan.bonus_uc > 0 && ` + ${plan.bonus_uc}`}{plan.promo_extra_uc > 0 && ` + ${plan.promo_extra_uc}`} {i18n.t('passPage.offertes')}
      </p>
    )}
    {plan.promo_extra_uc > 0 && (
      <p className="text-[10px] font-bold text-[#7BC94E] mt-1" data-testid={`pass-promo-boost-${plan.id}`}>
        ⚡ {plan.promo_name}
      </p>
    )}
  </div>
);

export default function PassLolodrivePage() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const firstName = state?.firstName;
  const relay = state?.relay || (() => { try { return JSON.parse(localStorage.getItem('kdm_preselected_point') || 'null'); } catch { return null; } })();
  const [plans, setPlans] = useState(null);

  useEffect(() => {
    fetch(`${API}/public/pass-plans`).then((r) => (r.ok ? r.json() : null)).then(setPlans).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #1F0A33 0%, #2A1045 100%)' }}>
      <NavBar />
      <div className="pt-20 -mb-16"><FlashPromoBanner placement="pass" /></div>
      <main className="max-w-3xl mx-auto px-4 pt-28 pb-20" data-testid="pass-lolodrive-page">
        {firstName && (
          <div className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 mb-5 text-sm bg-[#7BC94E]/15 border border-[#7BC94E]/40 text-[#B9E89A]" data-testid="pass-confirmation">
            <BadgeCheck className="w-4 h-4" /> {i18n.t('passPage.confirmation', { name: firstName })}
          </div>
        )}
        <p className="text-[11px] uppercase tracking-[0.2em] text-[#D9B35A] font-bold mb-2">{i18n.t('passPage.kicker')}</p>
        <div className="flex items-center gap-4 mb-4">
          <img src="/lolodrive-logo.jpg" alt="LOLODRIVE" data-testid="pass-lolodrive-logo"
            className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-white object-contain p-1 border-2 border-[#D9B35A]/50 shadow-[0_0_30px_rgba(217,179,90,0.25)]" />
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold">PASS <span className="text-[#D9B35A]">LOLODRIVE</span></h1>
        </div>
        <p className="text-base text-white/75 max-w-2xl mb-10" data-testid="pass-explainer">
          {i18n.t('passPage.explainer')}
        </p>
        <div className="grid sm:grid-cols-3 gap-4 mb-10">
          {CARDS.map(({ icon: Icon, key }) => (
            <div key={key} className="rounded-2xl p-5 bg-white/[0.05] border border-[#D9B35A]/20" data-testid={`pass-${key}`}>
              <Icon className="w-6 h-6 text-[#D9B35A] mb-3" />
              <p className="text-sm font-semibold mb-1.5">{i18n.t(`passPage.${key}_title`)}</p>
              <p className="text-xs text-white/55 leading-relaxed">{i18n.t(`passPage.${key}_desc`)}</p>
            </div>
          ))}
        </div>

        {plans?.adhesion && (
          <div className="rounded-2xl p-6 mb-6 border border-[#D9B35A]/40"
            style={{ background: 'linear-gradient(135deg, rgba(217,179,90,0.14), rgba(217,179,90,0.04))' }}
            data-testid="pass-adhesion-card">
            <div className="flex flex-wrap items-center gap-4">
              <Ticket className="w-8 h-8 text-[#D9B35A]" />
              <div className="flex-1 min-w-[200px]">
                <p className="text-sm font-semibold">{i18n.t('passPage.adhesion_title')}</p>
                <p className="text-xs text-white/55 mt-0.5">{i18n.t('passPage.uc_note')}</p>
              </div>
              <p className="text-3xl font-bold text-[#E9CF8E]" data-testid="pass-adhesion-price">
                {plans.adhesion.price_eur} € <span className="text-base text-white/70">/ {plans.adhesion.uc + (plans.adhesion.bonus_uc || 0)} UC</span>
              </p>
            </div>
            <div className="mt-4 pt-4 border-t border-[#D9B35A]/20">
              <button type="button" data-testid="pass-pay-adhesion-btn"
                onClick={() => navigate(authAPI.isAuthenticated() ? '/espace-pass' : '/connexion')}
                className="btn-gold inline-flex items-center gap-2 rounded-[14px] px-6 py-3 text-sm font-semibold">
                <CreditCard className="w-4 h-4" /> {i18n.t('passPage.payer_adhesion', { price: plans.adhesion.price_eur })}
              </button>
              <p className="text-[11px] text-white/45 mt-2">{i18n.t('passPage.paiement_note')}</p>
            </div>
          </div>
        )}

        {plans?.recharges?.length > 0 && (
          <div className="mb-10" data-testid="pass-recharges-section">
            <p className="text-sm font-semibold flex items-center gap-2 mb-1.5">
              <BatteryCharging className="w-4 h-4 text-[#D9B35A]" /> {i18n.t('passPage.recharge_title')}
            </p>
            <p className="text-xs text-white/55 mb-4">{i18n.t('passPage.recharge_desc')}</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              {plans.recharges.map((p) => <RechargeCard key={p.id} plan={p} />)}
            </div>
          </div>
        )}

        {relay && (
          <div className="flex items-center gap-2 rounded-xl px-3.5 py-2.5 mb-8 text-sm bg-white/[0.05] border border-[#D9B35A]/25" data-testid="pass-page-relay">
            <img src="/lolodrive-logo.jpg" alt="" className="w-7 h-7 rounded-full bg-white object-contain shrink-0" />
            <MapPin className="w-4 h-4 text-[#D9B35A]" />
            <span className="text-white/75">{i18n.t('passPage.votre_relais')} <b className="text-[#E9CF8E]">{relay.name}</b>{relay.code ? ` (${relay.code})` : ''}</span>
          </div>
        )}
        <div className="flex flex-wrap gap-3">
          <Link to="/lolodrive">
            <button className="btn-gold inline-flex items-center gap-2 rounded-[14px] px-6 py-3 text-sm font-semibold" data-testid="pass-cta-catalogue">
              {i18n.t('passPage.cta_catalogue')} <ArrowRight className="w-4 h-4" />
            </button>
          </Link>
          <Link to="/">
            <button className="inline-flex items-center gap-2 rounded-[14px] px-6 py-3 text-sm font-semibold text-white border border-white/25 hover:bg-white/5 transition-colors" data-testid="pass-cta-accueil">
              {i18n.t('passPage.cta_accueil')}
            </button>
          </Link>
        </div>
        <VitrineReviews />
      </main>
    </div>
  );
}
