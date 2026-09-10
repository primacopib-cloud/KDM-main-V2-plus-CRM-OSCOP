import { Link } from 'react-router-dom';
import { ShoppingCart, Factory, Ship, ArrowRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const JOURNEYS = [
  { icon: ShoppingCart, color: '#D9B35A', key: 'acheteurs', to: '/adhesion-vendeur?type=acheteur_pro', testid: 'journey-acheter' },
  { icon: Factory, color: '#8CC63E', key: 'fournisseurs', to: '/adhesion-vendeur', testid: 'journey-fournisseurs' },
  { icon: Ship, color: '#5AA7D9', key: 'logiscop', to: '/calculateur-fret', testid: 'journey-logiscop' },
];

export const ProJourneysSection = () => {
  const { t } = useTranslation();
  return (
  <section className="py-8 px-5" data-testid="pro-journeys">
    <div className="max-w-[1160px] mx-auto">
      <div className="section-title mb-5">
        <div>
          <h2 className="text-[24px] font-bold tracking-tight m-0">{t('pro.journeys_title')}</h2>
          <p className="text-white/70 text-sm mt-1 m-0">{t('pro.journeys_sub')}</p>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {JOURNEYS.map((j) => (
          <Link key={j.testid} to={j.to} data-testid={j.testid}
            className="glass-panel-soft rounded-[18px] p-5 flex flex-col gap-3 group hover:border-[#D9B35A]/40 transition-colors border border-transparent">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${j.color}22`, border: `1px solid ${j.color}55` }}>
              <j.icon className="w-5 h-5" style={{ color: j.color }} />
            </div>
            <h3 className="text-base font-bold text-white m-0">{t(`pro.j_${j.key}_t`)}</h3>
            <p className="text-white/70 text-[13px] m-0 flex-1">{t(`pro.j_${j.key}_d`)}</p>
            <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold" style={{ color: j.color }}>
              {t(`pro.j_${j.key}_c`)} <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </Link>
        ))}
      </div>
    </div>
  </section>
  );
};
