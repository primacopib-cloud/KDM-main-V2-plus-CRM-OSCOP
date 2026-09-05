import { CreditCard, Ticket, Euro, RefreshCcw, XCircle, CheckCircle2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const ICONS = [CreditCard, Ticket, Euro, RefreshCcw];

export const FinancingCompartments = () => {
  const { t } = useTranslation();
  const comps = t('pro.fin_compartments', { returnObjects: true });
  const can = t('pro.fin_can_list', { returnObjects: true });
  const cannot = t('pro.fin_cannot_list', { returnObjects: true });
  return (
  <section className="py-8 px-5" data-testid="financing-compartments">
    <div className="max-w-[1160px] mx-auto">
      <div className="section-title mb-5">
        <div>
          <h2 className="text-[24px] font-bold tracking-tight m-0">{t('pro.fin_title')}</h2>
          <p className="text-[#D9B35A] text-sm mt-1 m-0 font-semibold">{t('pro.fin_sub')}</p>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mb-5">
        {(Array.isArray(comps) ? comps : []).map((c, i) => {
          const Icon = ICONS[i] || CreditCard;
          return (
            <div key={c.t} className="glass-panel-soft rounded-[18px] p-5">
              <Icon className="w-5 h-5 text-[#D9B35A] mb-2.5" />
              <h3 className="text-sm font-bold text-white m-0 mb-1.5">{c.t}</h3>
              <p className="text-white/65 text-[12.5px] m-0">{c.d}</p>
            </div>
          );
        })}
      </div>
      <div className="grid md:grid-cols-2 gap-3.5">
        <div className="glass-panel-soft rounded-[18px] p-5">
          <h4 className="text-sm tracking-wider uppercase text-[#A9D96C] font-semibold mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" /> {t('pro.fin_can_title')}
          </h4>
          <div className="flex flex-wrap gap-2">
            {(Array.isArray(can) ? can : []).map((s) => (
              <span key={s} className="px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-white/80 text-xs">{s}</span>
            ))}
          </div>
        </div>
        <div className="glass-panel-soft rounded-[18px] p-5">
          <h4 className="text-sm tracking-wider uppercase text-[#E88] font-semibold mb-3 flex items-center gap-2">
            <XCircle className="w-4 h-4" /> {t('pro.fin_cannot_title')}
          </h4>
          <div className="space-y-1.5">
            {(Array.isArray(cannot) ? cannot : []).map((s) => (
              <div key={s} className="flex items-center gap-2 text-white/75 text-[13px]">
                <div className="cross-icon"></div><span>{s}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </section>
  );
};
