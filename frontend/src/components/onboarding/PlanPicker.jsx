import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Star, ArrowUpCircle } from 'lucide-react';
import { tData } from '@/i18n/tData';

export const PlanPicker = ({ value, onChange, memberType, onPlansLoaded }) => {
  const { t } = useTranslation();
  const [plans, setPlans] = useState([]);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/public/plans`)
      .then((r) => r.json())
      .then((d) => {
        const list = Array.isArray(d.plans) ? d.plans : [];
        setPlans(list);
        if (onPlansLoaded) onPlansLoaded(list);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const visible = plans.filter((p) => {
    const targets = p.target_profiles || ['all'];
    return targets.includes('all') || !memberType || targets.includes(memberType);
  });
  if (!visible.length) return null;
  return (
    <div>
      <p className="text-xs text-white/60 mb-2">{t('vendorOnboarding.plan')}</p>
      <div className="grid sm:grid-cols-3 gap-3" data-testid="plan-picker">
        {visible.map((p, idx) => {
          const active = value === p.slug;
          const prev = idx > 0 ? visible[idx - 1] : null;
          return (
            <button type="button" key={p.slug} data-testid={`plan-card-${p.slug}`} onClick={() => onChange(p.slug)}
              className={`relative text-left p-4 pt-5 rounded-2xl border transition-all ${
                active
                  ? 'border-[#D9B35A] bg-[#D9B35A]/12 shadow-[0_0_24px_rgba(217,179,90,0.18)]'
                  : 'border-white/15 hover:border-white/35'
              }`}>
              {p.popular && (
                <span className="absolute -top-2.5 right-3 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold"
                  style={{ background: 'linear-gradient(135deg,#D9B35A,#b8933e)', color: '#1F0A33' }}>
                  <Star className="w-2.5 h-2.5" /> {t('vendorOnboarding.popular')}
                </span>
              )}
              <span className={`block text-[11px] font-bold tracking-wide uppercase ${active ? 'text-[#E9CF8E]' : 'text-white/80'}`}>{p.name}</span>
              <span className="block mt-1.5">
                <span className="text-2xl font-bold text-white" style={{ fontFamily: '"Playfair Display", serif' }}>
                  {Math.round((p.price_cents || 0) / 100)}
                </span>
                <span className="text-[11px] text-white/55"> {t('vendorOnboarding.perMonth')}</span>
              </span>
              {prev && (
                <span className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-semibold text-[#E9CF8E]"
                  data-testid={`plan-includes-${p.slug}`}>
                  <ArrowUpCircle className="w-3 h-3" /> {t('vendorOnboarding.includesAll', { plan: prev.name })}
                </span>
              )}
              <ul className="mt-2.5 space-y-1">
                {(p.features || []).slice(0, 3).map((f) => (
                  <li key={f} className="flex items-start gap-1.5 text-[10.5px] text-white/60 leading-snug">
                    <Check className="w-3 h-3 mt-px shrink-0 text-[#7BC94E]" /> {tData(f)}
                  </li>
                ))}
              </ul>
              <span className={`mt-3 block text-center text-[10.5px] font-bold rounded-lg py-1.5 transition-colors ${
                active ? 'bg-[#D9B35A] text-[#1F0A33]' : 'bg-white/10 text-white/60'
              }`}>
                {active ? t('vendorOnboarding.selected') : t('vendorOnboarding.choose')}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
