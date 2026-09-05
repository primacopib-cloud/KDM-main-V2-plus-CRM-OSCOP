import { ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export const FogedomNotice = () => {
  const { t } = useTranslation();
  return (
  <section className="py-4 px-5" data-testid="fogedom-notice">
    <div className="max-w-[1160px] mx-auto">
      <div className="rounded-[16px] p-4 flex gap-3 items-start"
        style={{ background: 'rgba(217,179,90,0.08)', border: '1px solid rgba(217,179,90,0.25)' }}>
        <ShieldCheck className="w-4 h-4 text-[#D9B35A] shrink-0 mt-0.5" />
        <p className="text-white/70 text-[12.5px] m-0">
          <strong className="text-white/90">FOGEDOM-SCIC</strong> {t('pro.fogedom_text')}
        </p>
      </div>
    </div>
  </section>
  );
};
