import { useLocation, Link } from 'react-router-dom';
import { ShoppingBasket, Users, MapPin, ArrowRight, BadgeCheck } from 'lucide-react';
import NavBar from '../components/NavBar';
import i18n from '@/i18n';

const CARDS = [
  { icon: ShoppingBasket, key: 'card_essentiels' },
  { icon: Users, key: 'card_mutualise' },
  { icon: MapPin, key: 'card_relais' },
];

export default function PassLolodrivePage() {
  const { state } = useLocation();
  const firstName = state?.firstName;
  const relay = state?.relay || (() => { try { return JSON.parse(localStorage.getItem('kdm_preselected_point') || 'null'); } catch { return null; } })();

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #1F0A33 0%, #2A1045 100%)' }}>
      <NavBar />
      <main className="max-w-3xl mx-auto px-4 pt-28 pb-20" data-testid="pass-lolodrive-page">
        {firstName && (
          <div className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 mb-5 text-sm bg-[#7BC94E]/15 border border-[#7BC94E]/40 text-[#B9E89A]" data-testid="pass-confirmation">
            <BadgeCheck className="w-4 h-4" /> {i18n.t('passPage.confirmation', { name: firstName })}
          </div>
        )}
        <p className="text-[11px] uppercase tracking-[0.2em] text-[#D9B35A] font-bold mb-2">{i18n.t('passPage.kicker')}</p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-4">PASS <span className="text-[#D9B35A]">LOLODRIVE</span></h1>
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
        {relay && (
          <div className="flex items-center gap-2 rounded-xl px-3.5 py-2.5 mb-8 text-sm bg-white/[0.05] border border-[#D9B35A]/25" data-testid="pass-page-relay">
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
      </main>
    </div>
  );
}
