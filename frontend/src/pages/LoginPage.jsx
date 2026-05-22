import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { partners } from '../data/mock';
import { ArrowLeft, LogIn, Mail, Lock, Loader2, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { authAPI } from '../services/api';

const LoginPage = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      await authAPI.login(formData.email, formData.password);
      toast.success('Connexion réussie !');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.message || 'Identifiants incorrects');
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
          radial-gradient(820px 460px at 88% 0%, rgba(87,209,154,0.16), transparent 55%),
          linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)
        `
      }}
    >
      <div className="w-full max-w-md">
        <Link to="/" className="inline-flex items-center text-white/60 hover:text-white mb-6 transition-colors text-sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Retour à l'accueil
        </Link>
        
        <div className="glass-panel rounded-[26px] p-8">
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-5 mb-6">
              <img 
                src={partners.kdmarche.logo} 
                alt="KDMARCHE" 
                className="h-44 w-auto object-contain"
                style={{ filter: 'drop-shadow(0 3px 10px rgba(217,179,90,0.45))' }}
              />
              <span className="text-white/40 text-2xl font-light">×</span>
              <img 
                src={partners.oscop.logo} 
                alt="O'SCOP" 
                className="h-28 w-auto object-contain"
                style={{ filter: 'drop-shadow(0 3px 10px rgba(87,209,154,0.45))' }}
              />
            </div>
            <h1 className="text-2xl font-bold">Espace Client</h1>
            <p className="text-white/60 text-sm mt-1">Connectez-vous à votre compte</p>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-white/80 text-sm">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="contact@entreprise.fr"
                  required
                  className="pl-11 h-12 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl focus:border-[#D9B35A]/50 focus:ring-[#D9B35A]/20"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <Label htmlFor="password" className="text-white/80 text-sm">Mot de passe</Label>
                <Link to="/mot-de-passe-oublie" className="text-xs text-[#D9B35A] hover:text-[#F2D07A]">Mot de passe oublié ?</Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  required
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

            <button 
              type="submit" 
              disabled={isLoading}
              className="btn-gold w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-[14px] text-sm font-semibold disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Connexion...
                </>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  Se connecter
                </>
              )}
            </button>
            
            <p className="text-center text-sm text-white/60">
              Pas encore de compte ? <Link to="/inscription" className="text-[#D9B35A] hover:text-[#F2D07A] font-medium">Créer un compte</Link>
            </p>
          </form>
          
          {/* Demo credentials info */}
          <div className="mt-6 p-4 rounded-xl bg-white/[0.03] border border-white/[0.08]">
            <p className="text-xs text-white/50 mb-2 font-medium">Pour tester, créez un compte ou utilisez :</p>
            <p className="text-sm text-white/70">Créez un nouveau compte via le formulaire d'inscription.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
