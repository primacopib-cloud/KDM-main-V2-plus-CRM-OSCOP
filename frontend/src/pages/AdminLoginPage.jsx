import i18n from '@/i18n';
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { partners } from '../data/mock';
import {
  LogIn, Mail, Lock, Loader2, Eye, EyeOff, Shield, ArrowLeft, AlertTriangle,
  Terminal, KeyRound, ScrollText,
} from 'lucide-react';
import { toast } from 'sonner';
import { authAPI } from '../services/api';

/**
 * Super Admin login page.
 * Uses the same backend endpoint as the member login, but:
 *  - refuses to redirect if the returned user isn't `is_admin=true`
 *  - visually distinct (deep purple + gold) to signal restricted access
 *  - redirects to /superadmin on success
 */
const AdminLoginPage = () => {
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
      const result = await authAPI.login(formData.email, formData.password);
      // authAPI.login returns { access_token, user } and stores them; make sure the account is admin.
      const user = result?.user || JSON.parse(localStorage.getItem('user') || 'null');
      if (!user?.is_admin) {
        // Not an admin account — log out immediately, don't leak session.
        authAPI.logout();
        toast.error(i18n.t('adm.ce_compte_n_a_pas'));
        return;
      }
      toast.success(i18n.t('adm.bienvenue_dans_l_espace_administrateur'));
      navigate('/superadmin');
    } catch (error) {
      toast.error(error.message || 'Identifiants incorrects');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row" data-testid="admin-login-page">
      {/* ─────────────── LEFT PANEL (deep purple admin) ─────────────── */}
      <aside
        className="on-dark relative hidden lg:flex lg:w-1/2 flex-col justify-between p-10 xl:p-14 overflow-hidden"
        style={{
          background:
            'radial-gradient(900px 500px at 15% 0%, rgba(245,166,35,0.20), transparent 60%), ' +
            'radial-gradient(700px 500px at 85% 100%, rgba(217,179,90,0.14), transparent 65%), ' +
            'linear-gradient(180deg, #2a0c4a 0%, #4a1776 55%, #2a0c4a 100%)',
        }}
      >
        <div
          className="absolute inset-0 opacity-[0.06] pointer-events-none"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />

        <div className="relative">
          <Link
            to="/connexion"
            className="inline-flex items-center gap-2 text-white/60 hover:text-white/90 text-sm transition-colors mb-10"
            data-testid="back-to-member-login-link"
          >
            <ArrowLeft className="w-4 h-4" />
            {i18n.t('adm.retour_connexion_membres')}
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

        <div className="relative">
          <span
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] uppercase tracking-[0.18em] font-bold text-[#F5A623] mb-5"
            style={{
              background: 'rgba(245,166,35,0.14)',
              border: '1px solid rgba(245,166,35,0.4)',
            }}
          >
            <Shield className="w-3 h-3" />
            {i18n.t('adm.espace_administrateur')}
          </span>
          <h1
            className="text-4xl xl:text-5xl font-serif font-semibold text-white leading-[1.05] mb-4"
            style={{ fontFamily: '"Playfair Display", "Cormorant Garamond", serif' }}
          >
            Console <span className="text-[#F5A623]">{i18n.t('adm.super_admin')}</span> KDMARCHE × O&apos;SCOP
          </h1>
          <p className="text-white/70 text-base leading-relaxed max-w-md mb-8">
            {i18n.t('adm.zone_restreinte_desc')}
          </p>

          <div
            className="flex items-start gap-3 p-4 rounded-xl max-w-md"
            style={{
              background: 'rgba(245,166,35,0.08)',
              border: '1px solid rgba(245,166,35,0.35)',
            }}
          >
            <AlertTriangle className="w-5 h-5 text-[#F5A623] flex-shrink-0 mt-0.5" />
            <p className="text-white/80 text-sm leading-relaxed">
              {i18n.t('adm.toute_connexion_prefix')}<strong className="text-white">{i18n.t('adm.journalisee')}</strong>{i18n.t('adm.audit_conformite_suffix')}
            </p>
          </div>

          <ul className="mt-8 space-y-2.5 max-w-md text-sm text-white/60">
            <li className="flex items-center gap-2.5">
              <KeyRound className="w-3.5 h-3.5 text-[#F5A623]" /> {i18n.t('adm.authentification_renforcee')}
            </li>
            <li className="flex items-center gap-2.5">
              <Terminal className="w-3.5 h-3.5 text-[#F5A623]" /> {i18n.t('adm.console_gestion_centrale')}
            </li>
            <li className="flex items-center gap-2.5">
              <ScrollText className="w-3.5 h-3.5 text-[#F5A623]" /> {i18n.t('adm.audit_trail_rgpd')}
            </li>
          </ul>
        </div>

        <div className="relative flex items-center gap-4 text-[11px] text-white/45">
          <span>{i18n.t('adm.session_chiffree_journal_d_audit')}</span>
          <span>·</span>
          <span>{i18n.t('adm.2026_centrale_ess')}</span>
        </div>
      </aside>

      {/* ─────────────── RIGHT PANEL (white form) ─────────────── */}
      <main className="flex-1 flex flex-col bg-white">
        <div className="flex items-center justify-end px-6 lg:px-10 py-5">
          <Link
            to="/connexion"
            className="text-sm text-slate-500 hover:text-slate-800 inline-flex items-center gap-2 lg:hidden"
            data-testid="back-to-member-login-mobile"
          >
            <ArrowLeft className="w-4 h-4" /> Connexion membres
          </Link>
        </div>

        <div className="flex-1 flex items-center justify-center px-6 lg:px-10 pb-10">
          <div className="w-full max-w-md">
            <div className="mb-8">
              <p className="text-xs uppercase tracking-[0.18em] text-[#4a1776] font-bold mb-2 flex items-center gap-2">
                <Shield className="w-3.5 h-3.5" /> {i18n.t('adm.connexion_administrateur')}
              </p>
              <h2
                className="text-3xl font-serif font-semibold text-slate-900 mb-2"
                style={{ fontFamily: '"Playfair Display", serif' }}
              >
                {i18n.t('adm.acces_securise')}
              </h2>
              <p className="text-slate-500 text-sm">
                {i18n.t('adm.reserve_super_admins')}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5" data-testid="admin-login-form">
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-slate-700 text-sm font-medium">
                  {i18n.t('adm.adresse_email_admin')}
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="admin@kdmarche-oscop.fr"
                    required
                    data-testid="admin-login-email-input"
                    className="pl-11 h-12 bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 rounded-xl focus:border-[#4a1776] focus:ring-[#4a1776]/20"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <Label htmlFor="password" className="text-slate-700 text-sm font-medium">
                    {i18n.t('adm.mot_de_passe')}
                  </Label>
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
                    data-testid="admin-login-password-input"
                    className="pl-11 pr-11 h-12 bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 rounded-xl focus:border-[#4a1776] focus:ring-[#4a1776]/20"
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
                data-testid="admin-login-submit-btn"
                className="force-white w-full h-12 inline-flex items-center justify-center gap-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60 transition-all shadow-lg shadow-[#4a1776]/30 hover:shadow-xl hover:shadow-[#4a1776]/40"
                style={{
                  background: 'linear-gradient(135deg, #4a1776 0%, #2a0c4a 100%)',
                }}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> {i18n.t('adm.verification')}
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4" /> {i18n.t('adm.acces_securise')}
                  </>
                )}
              </button>

              <div
                className="flex items-start gap-2.5 p-3 rounded-lg text-xs text-slate-600"
                style={{
                  background: 'rgba(74,23,118,0.04)',
                  border: '1px solid rgba(74,23,118,0.15)',
                }}
              >
                <AlertTriangle className="w-4 h-4 text-[#4a1776] flex-shrink-0 mt-0.5" />
                <span>
                  {i18n.t('adm.cet_ecran_reserve_prefix')}<strong className="text-slate-900">{i18n.t('adm.super_administrateurs')}</strong>{i18n.t('adm.comptes_membres_doivent')}{' '}
                  <Link to="/connexion" className="text-[#5B2E8C] font-medium hover:underline">
                    {i18n.t('adm.connexion_standard')}
                  </Link>
                  .
                </span>
              </div>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
};

export default AdminLoginPage;
