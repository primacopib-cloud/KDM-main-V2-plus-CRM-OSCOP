import { Link } from 'react-router-dom';
import { Users, HeartHandshake, ArrowRight } from 'lucide-react';
import i18n from '@/i18n';

export const CoopEssSection = () => (
  <>
    <section className="max-w-[820px] mx-auto px-5 text-center mb-14" data-testid="kdm-catalog-cta">
      <h2 className="font-display text-2xl mb-3">{i18n.t('home.coopEss.cat_title')}</h2>
      <p className="text-white/60 text-sm mb-5 max-w-[56ch] mx-auto">
        {i18n.t('home.coopEss.cat_p')}
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <Link to="/catalogue-lolodrive" className="btn-gold h-11 px-6 rounded-lg inline-flex items-center gap-2 text-sm font-semibold" data-testid="kdm-cta-catalog-full">
          {i18n.t('home.coopEss.cat_cta')} <ArrowRight size={15} />
        </Link>
        <Link to="/pass" className="h-11 px-6 rounded-lg inline-flex items-center gap-2 text-sm font-semibold text-white border border-white/25 hover:bg-white/5" data-testid="kdm-cta-choose-pass">
          {i18n.t('home.coopEss.pass_cta')}
        </Link>
      </div>
    </section>

    <section className="max-w-[820px] mx-auto px-5 text-center mb-12" data-testid="kdm-coop-section">
      <HeartHandshake className="w-8 h-8 mx-auto mb-3 text-[#D9B35A]" />
      <h2 className="font-display text-2xl mb-3">{i18n.t('home.coopEss.coop_title')}</h2>
      <p className="text-white/70 text-sm">
        {i18n.t('home.coopEss.coop_p')}
      </p>
      <div className="flex justify-center gap-3 mt-6">
        <Link to="/tarifs" className="btn-gold h-11 px-6 rounded-lg inline-flex items-center gap-2 text-sm font-semibold" data-testid="kdm-cta-pricing">
          <Users size={15} /> {i18n.t('home.coopEss.member_cta')}
        </Link>
      </div>
    </section>
  </>
);
