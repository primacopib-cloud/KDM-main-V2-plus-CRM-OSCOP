import Seo from '../components/Seo';
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
import { useTranslation } from 'react-i18next';
import { authAPI } from '../services/api';
import LanguageSwitcher from '../components/LanguageSwitcher';

/**
 * Unified member login page (KDMARCHE × O'SCOP).
 * - Split panel : left navy/gold storytelling, right white form.
 * - Members log in here. Super admins use /admin/connexion.
 */
const LoginPage = () => {
  const { t } = useTranslation();
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
      const data = await authAPI.login(formData.email, formData.password);
      if (data?.user?.must_change_password) {
        toast.info(t('auth.login_success'));
        navigate('/changer-mot-de-passe');
        return;
      }
      toast.success(t('auth.login_success'));
      const next = new URLSearchParams(window.location.search).get('next');
      const u = data?.user;
      const isSuperAdmin = u?.is_admin || ['SUPER_ADMIN', 'ADMIN', 'admin'].includes(u?.role);
      navigate(next && next.startsWith('/') ? next : (isSuperAdmin ? '/superadmin' : '/dashboard'));
    } catch (error) {
      toast.error(error.message || t('auth.invalid_credentials'));
    } finally {
      setIsLoading(false);
    }
  };

  const benefits = [
    {
      icon: Handshake,
      title: t('auth.benefit1_title'),
      desc: t('auth.benefit1_desc'),
    },
    {
      icon: TrendingUp,
      title: t('auth.benefit2_title'),
      desc: t('auth.benefit2_desc'),
    },
    {
      icon: ShieldCheck,
      title: t('auth.benefit3_title'),
      desc: t('auth.benefit3_desc'),
    },
  ];

  return (
    <div className="min-h-screen flex flex-col lg:flex-row" data-testid="login-page">
      <Seo titleKey="seo.login_title" />
      {/* ─────────────── LEFT PANEL (deep blue KDMARCHE) ─────────────── */}
      <aside
        className="on-dark relative hidden lg:flex lg:w-1/2 flex-col justify-between p-10 xl:p-14 overflow-hidden"
        style={{
          background:
            'radial-gradient(900px 500px at 15% 0%, rgba(212,175,55,0.22), transparent 60%), ' +
            'radial-gradient(700px 500px at 90% 100%, rgba(212,175,55,0.14), transparent 65%), ' +
            'linear-gradient(180deg, #2A1045 0%, #5B2E8C 55%, #2A1045 100%)',
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
            {t('common.back_home')}
          </Link>
          <div className="flex items-center gap-3">
            <div className="bg-white rounded-2xl px-3 py-2 shadow-lg">
              <img src={partners.kdmarche.logo} alt="KDMARCHE Pro" className="h-12 w-auto object-contain" />
            </div>
            <span className="text-white/30 text-lg">×</span>
            <div className="bg-white rounded-2xl px-3 py-2 shadow-lg">
              <img src={partners.oscop.logo} alt="Objectif SCOP Outremer" className="h-12 w-auto object-contain" />
            </div>
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
            {t('auth.members_area')}
          </span>
          <h1
            className="text-4xl xl:text-5xl font-serif font-semibold text-white leading-[1.05] mb-4"
            style={{ fontFamily: '"Playfair Display", "Cormorant Garamond", serif' }}
          >
            {t('auth.welcome_1')} <span className="text-[#D9B35A]">{t('auth.welcome_2')}</span> KDMARCHE × O&apos;SCOP
          </h1>
          <p className="text-white/70 text-base leading-relaxed max-w-md mb-8">
            {t('auth.welcome_subtitle')}
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
          <span>{t('auth.encrypted_data')}</span>
          <span>·</span>
          <span>© 2026 Centrale ESS</span>
        </div>
      </aside>

      {/* ─────────────── RIGHT PANEL (white form) ─────────────── */}
      <main className="flex-1 flex flex-col bg-[#2B1548]">
        {/* Top bar: mobile brand + language */}
        <div className="flex items-center justify-between px-6 lg:px-10 py-5">
          <Link to="/" className="flex items-center gap-2 lg:hidden">
            <img src={partners.kdmarche.logo} alt="KDMARCHE Pro" className="h-10 w-auto object-contain" />
            <span className="text-white/50 text-sm">×</span>
            <img src={partners.oscop.logo} alt="Objectif SCOP Outremer" className="h-9 w-auto object-contain" />
          </Link>
          <div className="ml-auto">
            <LanguageSwitcher />
          </div>
        </div>

        {/* Form */}
        <div className="flex-1 flex items-center justify-center px-6 lg:px-10 pb-10">
          <div className="w-full max-w-md">
            <div className="mb-8">
              <p className="text-xs uppercase tracking-[0.15em] text-[#E9CF8E] font-semibold mb-2">
                {t('auth.member_login')}
              </p>
              <h2 className="text-3xl font-serif font-semibold text-white mb-2" style={{ fontFamily: '"Playfair Display", serif' }}>
                {t('auth.access_your_space')}
              </h2>
              <p className="text-white/60 text-sm">
                {t('auth.login_subtitle')}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5" data-testid="login-form">
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-white/80 text-sm font-medium">
                  {t('auth.email_label')}
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/50" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="contact@entreprise.fr"
                    required
                    data-testid="login-email-input"
                    className="pl-11 h-12 bg-white/5 border-white/15 text-white placeholder:text-white/50 rounded-xl focus:border-[#5B2E8C] focus:ring-[#5B2E8C]/20"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <Label htmlFor="password" className="text-white/80 text-sm font-medium">
                    {t('auth.password_label')}
                  </Label>
                  <Link
                    to="/mot-de-passe-oublie"
                    className="text-xs text-[#E9CF8E] hover:text-[#451F6B] font-medium"
                    data-testid="forgot-password-link"
                  >
                    {t('auth.forgot_password')}
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/50" />
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="••••••••"
                    required
                    data-testid="login-password-input"
                    className="pl-11 pr-11 h-12 bg-white/5 border-white/15 text-white placeholder:text-white/50 rounded-xl focus:border-[#5B2E8C] focus:ring-[#5B2E8C]/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/50 hover:text-white/70 transition-colors"
                    tabIndex={-1}
                    aria-label={showPassword ? t('auth.hide_password') : t('auth.show_password')}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                data-testid="login-submit-btn"
                className="force-white w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60 transition-all shadow-lg shadow-[#5B2E8C]/30 hover:shadow-xl hover:shadow-[#5B2E8C]/40"
                style={{
                  background: 'linear-gradient(135deg, #5B2E8C 0%, #451F6B 100%)',
                }}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> {t('auth.logging_in')}
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4" /> {t('auth.sign_in')}
                  </>
                )}
              </button>

              <div className="relative my-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/15" />
                </div>
                <div className="relative flex justify-center">
                  <span className="px-3 text-[11px] text-white/50 uppercase tracking-wider" style={{ background: '#2B1548' }}>{t('common.or')}</span>
                </div>
              </div>

              {/* Native Google OAuth (KDMARCHE own Google Cloud project) */}
              {/* REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH */}
              <a
                href={`${process.env.REACT_APP_BACKEND_URL}/api/auth/google/login?redirect_after=/dashboard`}
                data-testid="google-login-btn"
                className="w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-xl text-sm font-medium bg-white/10 text-white border border-white/20 hover:bg-white/15 transition-colors"
              >
                <svg className="w-4 h-4" viewBox="0 0 48 48" aria-hidden="true">
                  <path fill="#FFC107" d="M43.6 20.5H42V20.5H24v7h11.3c-1.6 4.6-6 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5-5C33.6 6.7 29 5 24 5 13 5 4 14 4 25s9 20 20 20c11 0 20-9 20-20 0-1.5-.2-3-.4-4.5z"/>
                  <path fill="#FF3D00" d="M6.3 14.7l5.7 4.2C13.6 15.1 18.4 12 24 12c3.1 0 5.9 1.2 8 3.1l5-5C33.6 6.7 29 5 24 5 16.3 5 9.6 9.4 6.3 14.7z"/>
                  <path fill="#4CAF50" d="M24 45c5.1 0 9.8-1.9 13.3-5l-6.1-5.2c-2.1 1.4-4.5 2.2-7.2 2.2-5.3 0-9.7-3.4-11.3-8H6.5l-.5.4C9.4 35.8 16.1 40 24 40z"/>
                  <path fill="#1976D2" d="M43.6 20.5H42V20.5H24v7h11.3c-.8 2.3-2.4 4.4-4.6 5.7l6.1 5.2C39.6 35 44 30 44 24c0-1.2-.1-2.4-.4-3.5z"/>
                </svg>
                {t('auth.continue_google')}
              </a>

              <p className="text-center text-sm text-white/60">
                {t('auth.not_member_yet')}{' '}
                <Link to="/adhesion" className="text-[#E9CF8E] hover:text-[#451F6B] font-semibold" data-testid="signup-link">
                  {t('auth.join_central')}
                </Link>
              </p>
            </form>

            {/* Admin login callout */}
            <div className="mt-8 pt-6 border-t border-slate-100">
              <Link
                to="/admin/connexion"
                data-testid="admin-login-link"
                className="flex items-center justify-between gap-3 p-4 rounded-xl border border-white/15 hover:border-[#4a1776]/40 hover:bg-[#4a1776]/[0.03] transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center bg-[#4a1776]/10">
                    <Shield className="w-4 h-4 text-[#E9CF8E]" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{t('auth.are_you_admin')}</p>
                    <p className="text-xs text-white/60">{t('auth.admin_subtitle')}</p>
                  </div>
                </div>
                <span className="text-[#E9CF8E] text-sm font-medium group-hover:translate-x-0.5 transition-transform">
                  {t('auth.admin_login_arrow')}
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
