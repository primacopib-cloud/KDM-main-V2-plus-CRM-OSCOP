import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { partners } from '../data/mock';
import { ArrowLeft, Lock, Loader2, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { passwordAPI } from '../services/api';

const ResetPasswordPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      toast.error('Les mots de passe ne correspondent pas');
      return;
    }
    
    if (formData.password.length < 8) {
      toast.error('Le mot de passe doit contenir au moins 8 caractères');
      return;
    }
    
    setIsLoading(true);
    
    try {
      await passwordAPI.resetPassword(token, formData.password);
      setIsSuccess(true);
      toast.success('Mot de passe réinitialisé avec succès !');
      setTimeout(() => navigate('/connexion'), 3000);
    } catch (error) {
      toast.error(error.message || 'Lien invalide ou expiré');
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div 
        className="min-h-screen flex items-center justify-center p-4"
        style={{
          background: `
            radial-gradient(900px 420px at 20% -10%, rgba(217,179,90,0.22), transparent 55%),
            radial-gradient(820px 460px at 88% 0%, rgba(87,209,154,0.16), transparent 55%),
            linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)
          `
        }}
      >
        <div className="glass-panel rounded-[26px] p-8 max-w-md text-center">
          <div className="w-16 h-16 mx-auto rounded-full bg-red-500/20 flex items-center justify-center mb-6">
            <AlertCircle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="text-xl font-bold mb-2">Lien invalide</h1>
          <p className="text-white/60 mb-6">Ce lien de réinitialisation est invalide ou a expiré.</p>
          <Link to="/mot-de-passe-oublie">
            <button className="btn-gold w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-[14px] text-sm font-semibold">
              Demander un nouveau lien
            </button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        background: `
          radial-gradient(900px 420px at 20% -10%, rgba(217,179,90,0.22), transparent 55%),
          radial-gradient(820px 460px at 88% 0%, rgba(87,209,154,0.16), transparent 55%),
          linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)
        `
      }}
    >
      <div className="w-full max-w-md">
        <Link to="/connexion" className="inline-flex items-center text-white/60 hover:text-white mb-6 transition-colors text-sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Retour à la connexion
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
                style={{ filter: 'drop-shadow(0 3px 10px rgba(87,209,154,0.45))' }}
              />
            </div>
            <h1 className="text-2xl font-bold">Nouveau mot de passe</h1>
            <p className="text-white/60 text-sm mt-1">
              {isSuccess ? "Mot de passe mis à jour" : "Créez votre nouveau mot de passe"}
            </p>
          </div>
          
          {isSuccess ? (
            <div className="text-center space-y-6">
              <div className="w-16 h-16 mx-auto rounded-full bg-[#57D19A]/20 flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-[#57D19A]" />
              </div>
              <div className="space-y-2">
                <p className="text-white/80">
                  Votre mot de passe a été réinitialisé avec succès.
                </p>
                <p className="text-white/50 text-sm">
                  Redirection vers la page de connexion...
                </p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="password" className="text-white/80 text-sm">Nouveau mot de passe</Label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="Min. 8 caractères"
                    required
                    minLength={8}
                    data-testid="reset-password-new"
                    className="pl-11 pr-11 h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-white/80 text-sm">Confirmer le mot de passe</Label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    placeholder="Confirmer le mot de passe"
                    required
                    data-testid="reset-password-confirm"
                    className="pl-11 pr-11 h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70 transition-colors"
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button 
                type="submit" 
                disabled={isLoading}
                data-testid="reset-password-submit"
                className="btn-gold w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-[14px] text-sm font-semibold disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Réinitialisation...
                  </>
                ) : (
                  <>
                    <Lock className="w-4 h-4" />
                    Réinitialiser le mot de passe
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordPage;
