import { useTranslation } from 'react-i18next';
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { partners } from '../data/mock';
import { ArrowLeft, Mail, Loader2, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { passwordAPI } from '../services/api';

const ForgotPasswordPage = () => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [email, setEmail] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      await passwordAPI.forgotPassword(email);
      setIsSubmitted(true);
      toast.success(t('auth.email_sent'));
    } catch (error) {
      // Always show success to prevent email enumeration
      setIsSubmitted(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        background: `
          radial-gradient(900px 420px at 20% -10%, rgba(217,179,90,0.22), transparent 55%),
          radial-gradient(820px 460px at 88% 0%, rgba(212,175,55,0.16), transparent 55%),
          linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)
        `
      }}
    >
      <div className="w-full max-w-md">
        <Link to="/connexion" className="inline-flex items-center text-white/60 hover:text-white mb-6 transition-colors text-sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t('auth.back_to_login')}
        </Link>
        
        <div className="glass-panel rounded-[26px] p-8">
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-5 mb-6">
              <img 
                src={partners.kdmarche.logo} 
                alt="KDMARCHE" 
                className="h-32 w-auto object-contain"
                style={{ filter: 'drop-shadow(0 3px 10px rgba(217,179,90,0.45))' }}
              />
              <span className="text-white/40 text-2xl font-light">×</span>
              <img 
                src={partners.oscop.logo} 
                alt="O'SCOP" 
                className="h-20 w-auto object-contain"
                style={{ filter: 'drop-shadow(0 3px 10px rgba(212,175,55,0.45))' }}
              />
            </div>
            <h1 className="text-2xl font-bold">{t('auth.forgot_password_title')}</h1>
            <p className="text-white/60 text-sm mt-1">
              {isSubmitted ? t('auth.check_inbox') : t('auth.forgot_subtitle')}
            </p>
          </div>
          
          {isSubmitted ? (
            <div className="text-center space-y-6">
              <div className="w-16 h-16 mx-auto rounded-full bg-[#D4AF37]/20 flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-[#D4AF37]" />
              </div>
              <div className="space-y-2">
                <p className="text-white/80">
                  {t('auth.reset_sent_prefix')}<strong className="text-white">{email}</strong>{t('auth.reset_sent_suffix')}
                </p>
                <p className="text-white/50 text-sm">
                  {t('auth.link_expires')}
                </p>
              </div>
              <Link to="/connexion">
                <button className="btn-ghost w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-[14px] text-sm font-semibold mt-4">
                  {t('auth.back_to_login')}
                </button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-white/80 text-sm">{t('auth.email')}</Label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="contact@entreprise.fr"
                    required
                    data-testid="forgot-password-email"
                    className="pl-11 h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
                  />
                </div>
              </div>

              <button 
                type="submit" 
                disabled={isLoading}
                data-testid="forgot-password-submit"
                className="btn-gold w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-[14px] text-sm font-semibold disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {t('auth.sending')}
                  </>
                ) : (
                  <>
                    <Mail className="w-4 h-4" />
                    {t('auth.send_link')}
                  </>
                )}
              </button>
              
              <p className="text-center text-sm text-white/60">
                {t('auth.remember')} <Link to="/connexion" className="text-[#D9B35A] hover:text-[#F2D07A] font-medium">{t('auth.sign_in')}</Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
