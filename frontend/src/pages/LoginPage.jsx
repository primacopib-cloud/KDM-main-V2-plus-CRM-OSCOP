import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { partners } from '../data/mock';
import {
  LogIn, Mail, Lock, Loader2, Eye, EyeOff, Shield, ArrowLeft,
  Handshake, TrendingUp, ShieldCheck, Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import { authAPI } from '../services/api';
import LanguageSwitcher from '../components/LanguageSwitcher';

/**
 * Unified member login page (KDMARCHE × O'SCOP).
 * - Split panel : left navy/gold storytelling, right white form.
 * - Members log in here. Super admins use /admin/connexion.
 */
const LoginPage = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({ email: '', password: '' });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
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

  const benefits = [
    {
      icon: Handshake,
      title: 'Centrale d\'achats coopérative B2B2C',
      desc: 'Accès mutualisé aux produits et solutions sélectionnés du réseau.',
    },
    {
      icon: TrendingUp,
      title: 'Conditions économiques mutualisées',
      desc: 'Prix structurels issus de la force collective des membres professionnels.',
    },
    {
      icon: ShieldCheck,
      title: 'Cadre sécurisé et traçable',
      desc: 'RGPD · SSL · Signature électronique · Wallet crédits certifié.',
    },
  ];

  return (
    <div className="min-h-screen flex flex-col lg:flex-row" data-testid="login-page">
      {/* ─────────────── LEFT PANEL (deep blue KDMARCHE) ─────────────── */}
      <aside
        className="relative hidden lg:flex lg:w-1/2 flex-col justify-between p-10 xl:p-14 overflow-hidden"
        style={{
          background:
            'radial-gradient(900px 500px at 15% 0%, rgba(212,175,55,0.22), transparent 60%), ' +
            'radial-gradient(700px 500px at 90% 100%, rgba(87,209,154,0.14), transparent 65%), ' +
            'linear-gradient(180deg, #0B1F3B 0%, #0B4D87 55%, #0B1F3B 100%)',
        }}
      >
        {/* Subtle grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.06] pointer-events-none"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />

        {/* Brand */}
        <div className="relative">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-white/60 hover:text-white/90 text-sm transition-colors mb-10"
            data-testid="back-home-link"
          >
            <ArrowLeft className="w-4 h-4" />
            Retour à l&apos;accueil
          </Link>
          <div className="flex items-center gap-3">
            <img
              src={partners.kdmarche.logo}
              alt="KDMARCHE"
              className="h-10 w-auto object-contain"
              style={{ filter: 'drop-shadow(0 2px 8px rgba(217,179,90,0.35))' }}
            />
            <span className="text-white/30 text-lg">×</span>
            <img
              src={partners.oscop.logo}
              alt="O'SCOP"
              className="h-7 w-auto object-contain"
              style={{ filter: 'drop-shadow(0 2px 8px rgba(87,209,154,0.35))' }}
            />
          </div>
        </div>

        {/* Storytelling */}
        <div className="relative">
          <span
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] uppercase tracking-[0.15em] font-semibold text-[#D9B35A] mb-5"
            style={{
              background: 'rgba(217,179,90,0.12)',
              border: '1px solid rgba(217,179,90,0.35)',
            }}
          >
            <Sparkles className="w-3 h-3" />
            Espace Membres
          </span>
          <h1
            className="text-4xl xl:text-5xl font-serif font-semibold text-white leading-[1.05] mb-4"
            style={{ fontFamily: '"Playfair Display", "Cormorant Garamond", serif' }}
          >
            Bienvenue sur la Centrale <span className="text-[#D9B35A]">Coopérative</span> KDMARCHE × O&apos;SCOP
          </h1>
          <p className="text-white/70 text-base leading-relaxed max-w-md mb-8">
            API coopérative B2B2C dédiée aux membres professionnels, pour l&apos;accès mutualisé aux produits, services et
            conditions économiques associées.
          </p>

          <ul className="space-y-4 max-w-md">
            {benefits.map((b) => {
              const Icon = b.icon;
              return (
                <li key={b.title} className="flex items-start gap-3">
                  <div
                    className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center"
                    style={{
                      background: 'rgba(217,179,90,0.14)',
                      border: '1px solid rgba(217,179,90,0.35)',
                    }}
                  >
                    <Icon className="w-4 h-4 text-[#D9B35A]" />
                  </div>
                  <div>
                    <p className="text-white text-sm font-semibold">{b.title}</p>
                    <p className="text-white/55 text-xs mt-0.5 leading-relaxed">{b.desc}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Footer badges */}
        <div className="relative flex items-center gap-4 text-[11px] text-white/45">
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" /> RGPD
          </span>
          <span>·</span>
          <span>SSL 256-bit</span>
          <span>·</span>
          <span>Données chiffrées</span>
          <span>·</span>
          <span>© 2026 Centrale ESS</span>
        </div>
      </aside>

      {/* ─────────────── RIGHT PANEL (white form) ─────────────── */}
      <main className="flex-1 flex flex-col bg-white">
        {/* Top bar: mobile brand + language */}
        <div className="flex items-center justify-between px-6 lg:px-10 py-5">
          <Link to="/" className="flex items-center gap-2 lg:hidden">
            <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-7 w-auto object-contain" />
            <span className="text-slate-400 text-sm">×</span>
            <img src={partners.oscop.logo} alt="O'SCOP" className="h-5 w-auto object-contain" />
          </Link>
          <div className="ml-auto">
            <LanguageSwitcher />
          </div>
        </div>

        {/* Form */}
        <div className="flex-1 flex items-center justify-center px-6 lg:px-10 pb-10">
          <div className="w-full max-w-md">
            <div className="mb-8">
              <p className="text-xs uppercase tracking-[0.15em] text-[#0B4D87] font-semibold mb-2">
                Connexion Membres
              </p>
              <h2 className="text-3xl font-serif font-semibold text-slate-900 mb-2" style={{ fontFamily: '"Playfair Display", serif' }}>
                Accéder à votre espace
              </h2>
              <p className="text-slate-500 text-sm">
                Identifiez-vous pour rejoindre la Centrale d&apos;Achats coopérative.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5" data-testid="login-form">
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-slate-700 text-sm font-medium">
                  Adresse e-mail professionnelle
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="contact@entreprise.fr"
                    required
                    data-testid="login-email-input"
                    className="pl-11 h-12 bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 rounded-xl focus:border-[#0B4D87] focus:ring-[#0B4D87]/20"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <Label htmlFor="password" className="text-slate-700 text-sm font-medium">
                    Mot de passe
                  </Label>
                  <Link
                    to="/mot-de-passe-oublie"
                    className="text-xs text-[#0B4D87] hover:text-[#083866] font-medium"
                    data-testid="forgot-password-link"
                  >
                    Mot de passe oublié ?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="••••••••"
                    required
                    data-testid="login-password-input"
                    className="pl-11 pr-11 h-12 bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 rounded-xl focus:border-[#0B4D87] focus:ring-[#0B4D87]/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    tabIndex={-1}
                    aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                data-testid="login-submit-btn"
                className="w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60 transition-all shadow-lg shadow-[#0B4D87]/30 hover:shadow-xl hover:shadow-[#0B4D87]/40"
                style={{
                  background: 'linear-gradient(135deg, #0B4D87 0%, #083866 100%)',
                }}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Connexion…
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4" /> Se connecter
                  </>
                )}
              </button>

              <div className="relative my-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200" />
                </div>
                <div className="relative flex justify-center">
                  <span className="px-3 text-[11px] text-slate-400 bg-white uppercase tracking-wider">ou</span>
                </div>
              </div>

              {/* Native Google OAuth (KDMARCHE own Google Cloud project) */}
              {/* REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH */}
              <a
                href={`${process.env.REACT_APP_BACKEND_URL}/api/auth/google/login?redirect_after=/dashboard`}
                data-testid="google-login-btn"
                className="w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-xl text-sm font-medium bg-white text-slate-800 border border-slate-200 hover:bg-slate-50 transition-colors"
              >
                <svg className="w-4 h-4" viewBox="0 0 48 48" aria-hidden="true">
                  <path fill="#FFC107" d="M43.6 20.5H42V20.5H24v7h11.3c-1.6 4.6-6 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5-5C33.6 6.7 29 5 24 5 13 5 4 14 4 25s9 20 20 20c11 0 20-9 20-20 0-1.5-.2-3-.4-4.5z"/>
                  <path fill="#FF3D00" d="M6.3 14.7l5.7 4.2C13.6 15.1 18.4 12 24 12c3.1 0 5.9 1.2 8 3.1l5-5C33.6 6.7 29 5 24 5 16.3 5 9.6 9.4 6.3 14.7z"/>
                  <path fill="#4CAF50" d="M24 45c5.1 0 9.8-1.9 13.3-5l-6.1-5.2c-2.1 1.4-4.5 2.2-7.2 2.2-5.3 0-9.7-3.4-11.3-8H6.5l-.5.4C9.4 35.8 16.1 40 24 40z"/>
                  <path fill="#1976D2" d="M43.6 20.5H42V20.5H24v7h11.3c-.8 2.3-2.4 4.4-4.6 5.7l6.1 5.2C39.6 35 44 30 44 24c0-1.2-.1-2.4-.4-3.5z"/>
                </svg>
                Continuer avec Google
              </a>

              <p className="text-center text-sm text-slate-500">
                Pas encore membre ?{' '}
                <Link to="/adhesion" className="text-[#0B4D87] hover:text-[#083866] font-semibold" data-testid="signup-link">
                  Adhérer à la Centrale
                </Link>
              </p>
            </form>

            {/* Admin login callout */}
            <div className="mt-8 pt-6 border-t border-slate-100">
              <Link
                to="/admin/connexion"
                data-testid="admin-login-link"
                className="flex items-center justify-between gap-3 p-4 rounded-xl border border-slate-200 hover:border-[#4a1776]/40 hover:bg-[#4a1776]/[0.03] transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center bg-[#4a1776]/10">
                    <Shield className="w-4 h-4 text-[#4a1776]" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Vous êtes administrateur ?</p>
                    <p className="text-xs text-slate-500">Accédez à l&apos;espace de gestion sécurisé</p>
                  </div>
                </div>
                <span className="text-[#4a1776] text-sm font-medium group-hover:translate-x-0.5 transition-transform">
                  Connexion admin →
                </span>
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default LoginPage;
