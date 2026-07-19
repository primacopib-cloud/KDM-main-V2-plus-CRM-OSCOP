import { Lock, ExternalLink } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import NavBar from '../NavBar';

export const VendorSuspendedNotice = ({ info }) => {
  const { t } = useTranslation();
  return (
    <div className="min-h-screen" data-testid="vendor-suspended-notice">
      <NavBar />
      <div className="max-w-lg mx-auto px-4 pt-32 pb-16">
        <div className="glass-panel rounded-[22px] p-10 text-center">
          <div className="w-14 h-14 mx-auto rounded-full flex items-center justify-center mb-4"
            style={{ background: 'rgba(230,68,50,0.15)', border: '1px solid rgba(230,68,50,0.4)' }}>
            <Lock className="w-7 h-7 text-[#E64432]" />
          </div>
          <h1 className="text-xl font-bold text-white mb-2" data-testid="suspended-title">{t('vendorOnboarding.suspTitle')}</h1>
          {info?.plan_name && <p className="text-[#E9CF8E] text-xs font-semibold mb-2">{info.plan_name}</p>}
          <p className="text-white/65 text-sm mb-6">{t('vendorOnboarding.suspMsg')}</p>
          {info?.hosted_invoice_url && (
            <a href={info.hosted_invoice_url} target="_blank" rel="noreferrer" data-testid="suspended-pay-btn"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
              <ExternalLink className="w-4 h-4" /> {t('vendorOnboarding.suspPayBtn')}
            </a>
          )}
          <p className="text-white/40 text-xs mt-6">{t('vendorOnboarding.suspContact')}</p>
        </div>
      </div>
    </div>
  );
};
