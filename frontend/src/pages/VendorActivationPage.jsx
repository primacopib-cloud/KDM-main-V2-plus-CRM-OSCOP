import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { KeyRound, Loader2, Rocket, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import { API } from '../services/http';

const PwField = ({ value, onChange, placeholder, testId, minLength }) => {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input type={show ? 'text' : 'password'} required minLength={minLength} placeholder={placeholder}
        data-testid={testId} value={value} onChange={onChange}
        className="w-full h-11 rounded-xl px-3.5 pr-11 text-sm text-white placeholder-white/35 bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60" />
      <button type="button" onClick={() => setShow((v) => !v)} tabIndex={-1} data-testid={`${testId}-eye`}
        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/50 hover:text-white transition-colors">
        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>
    </div>
  );
};

export default function VendorActivationPage() {
  const [params] = useSearchParams();
  const { t } = useTranslation();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);

  const activate = async (e) => {
    e.preventDefault();
    if (password !== confirm) return toast.error(t('vendorOnboarding.actMismatch'));
    setBusy(true);
    try {
      const r = await fetch(`${API}/vendor-onboarding/activate`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: params.get('token'), password }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Activation impossible');
      toast.success(t('vendorOnboarding.actSuccess'));
      setTimeout(() => {
        window.location.href = (d.user?.space_route || (d.user?.role === 'buyer' ? '/espace-acheteur' : '/espace-vendeur')) + '?bienvenue=1';
      }, 800);
    } catch (err) { toast.error(err.message); setBusy(false); }
  };

  return (
    <div className="min-h-screen" data-testid="vendor-activation-page">
      <NavBar />
      <div className="max-w-md mx-auto px-4 pt-32 pb-16">
        <div className="glass-panel rounded-[22px] p-8">
          <div className="text-center mb-6">
            <Rocket className="w-10 h-10 mx-auto text-[#D9B35A] mb-3" />
            <h1 className="text-xl font-bold text-white">{t('vendorOnboarding.actTitle')}</h1>
            <p className="text-white/55 text-sm mt-1">{t('vendorOnboarding.actSubtitle')}</p>
          </div>
          <form onSubmit={activate} className="space-y-4">
            <PwField value={password} onChange={(e) => setPassword(e.target.value)} minLength={8}
              placeholder={t('vendorOnboarding.actPasswordPh')} testId="activation-password-input" />
            <PwField value={confirm} onChange={(e) => setConfirm(e.target.value)}
              placeholder={t('vendorOnboarding.actConfirmPh')} testId="activation-confirm-input" />
            <button type="submit" disabled={busy} data-testid="activation-submit-btn"
              className="w-full py-3 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />} {t('vendorOnboarding.actBtn')}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
