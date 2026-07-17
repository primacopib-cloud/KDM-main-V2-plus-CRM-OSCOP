import i18n from '@/i18n';
import React from 'react';
import { Users, Store, HeartHandshake } from 'lucide-react';

const CARDS = [
  { icon: Users, title: 'landing.why_cp_card1_title', desc: 'landing.why_cp_card1_desc', color: '#F5A623' },
  { icon: Store, title: 'landing.why_cp_card2_title', desc: 'landing.why_cp_card2_desc', color: '#D9B35A' },
  { icon: HeartHandshake, title: 'landing.why_cp_card3_title', desc: 'landing.why_cp_card3_desc', color: '#6FA82E' },
];

export const WhyCommunityplaceSection = () => (
  <section id="pourquoi-communityplace" className="py-10 px-5" data-testid="why-communityplace-section">
    <div className="max-w-[1160px] mx-auto">
      <div className="text-center mb-6">
        <span className="badge-status mb-3 inline-flex">
          <span className="dot pulse-glow"></span>
          {i18n.t('landing.why_cp_badge')}
        </span>
        <h3 className="text-[28px] font-display font-bold tracking-tight mt-2 mb-2">
          {i18n.t('landing.why_cp_title_prefix')} <span className="text-[#D9B35A]">{i18n.t('landing.why_cp_title')}</span>
        </h3>
        <p className="text-white/70 text-sm max-w-[68ch] mx-auto">
          {i18n.t('landing.why_cp_intro')}
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-3.5">
        {CARDS.map((c) => {
          const Icon = c.icon;
          return (
            <div
              key={c.title}
              className="glass-panel-soft rounded-[18px] p-5"
              data-testid={`why-cp-card-${c.title.split('_').pop()}`}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
                style={{ background: `${c.color}1c`, border: `1px solid ${c.color}55` }}
              >
                <Icon className="w-5 h-5" style={{ color: c.color }} />
              </div>
              <h4 className="text-base font-bold mb-1.5" style={{ color: c.color }}>
                {i18n.t(c.title)}
              </h4>
              <p className="text-white/70 text-sm m-0">{i18n.t(c.desc)}</p>
            </div>
          );
        })}
      </div>
    </div>
  </section>
);

export default WhyCommunityplaceSection;
