import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, Home, LogOut } from 'lucide-react';
import { Button } from './ui/button';
import { authAPI } from '../services/api';

/**
 * Layout commun pour les pages LOLODRIVE by O'SCOP.
 * Garde la cohérence visuelle Or & Violet / fond sombre.
 */
export default function LolodriveLayout({ title, subtitle, children, actions }) {
  const navigate = useNavigate();
  const user = authAPI.getCurrentUser();

  const logout = () => {
    authAPI.logout();
    navigate('/connexion');
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Top bar */}
      <header className="border-b border-white/[0.08] bg-black/30 backdrop-blur-xl sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #7c3aed 100%)' }}
            >
              <Sparkles className="w-5 h-5 text-black" />
            </div>
            <div>
              <div className="font-bold tracking-tight text-base leading-tight">KDMARCHÉ</div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-white/40">
                LOLODRIVE by O&apos;SCOP
              </div>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            {user && (
              <div className="text-xs text-right hidden sm:block">
                <div className="text-white/80">{user.contact_name || user.email}</div>
                <div className="text-white/40">{user.email}</div>
              </div>
            )}
            <Button variant="ghost" size="icon" asChild data-testid="nav-home-btn">
              <Link to="/">
                <Home className="w-4 h-4" />
              </Link>
            </Button>
            {user && (
              <Button variant="ghost" size="icon" onClick={logout} data-testid="nav-logout-btn">
                <LogOut className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {(title || actions) && (
          <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
            <div>
              <h1
                className="text-3xl sm:text-4xl font-bold tracking-tight bg-clip-text text-transparent"
                style={{ backgroundImage: 'linear-gradient(135deg, #D9B35A 0%, #fff 70%)' }}
              >
                {title}
              </h1>
              {subtitle && <p className="text-white/50 mt-2 text-sm max-w-2xl">{subtitle}</p>}
            </div>
            {actions && <div className="flex gap-2 flex-wrap">{actions}</div>}
          </div>
        )}
        {children}
      </main>

      <footer className="mt-16 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6 py-6 text-xs text-white/40 flex flex-wrap justify-between gap-3">
          <div>© 2026 KDMARCHÉ × O&apos;SCOP — Plateforme coopérative ESS</div>
          <div className="flex gap-4">
            <Link to="/legal" className="hover:text-white/70">Mentions légales</Link>
            <Link to="/legal/charte-ess" className="hover:text-white/70">Charte ESS</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

export const KpiCard = ({ label, value, sub, icon: Icon, accent = '#D9B35A', testId }) => (
  <div
    data-testid={testId}
    className="rounded-2xl p-5 bg-white/[0.025] border border-white/[0.07] hover:border-white/[0.15] transition-all"
  >
    <div className="flex items-start justify-between mb-3">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center"
        style={{ background: `${accent}1f` }}
      >
        {Icon && <Icon className="w-5 h-5" style={{ color: accent }} />}
      </div>
    </div>
    <div className="text-2xl font-bold leading-tight">{value}</div>
    <div className="text-xs text-white/50 mt-1">{label}</div>
    {sub && <div className="text-[11px] text-white/35 mt-1">{sub}</div>}
  </div>
);

export const SectionCard = ({ title, action, children, className = '' }) => (
  <div className={`rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5 ${className}`}>
    {(title || action) && (
      <div className="flex items-center justify-between mb-4">
        {title && <h2 className="text-base font-semibold tracking-tight">{title}</h2>}
        {action}
      </div>
    )}
    {children}
  </div>
);

export const Badge = ({ children, color = '#D9B35A' }) => (
  <span
    className="text-[10px] uppercase tracking-wider px-2 py-1 rounded-full font-medium"
    style={{ backgroundColor: `${color}1c`, color }}
  >
    {children}
  </span>
);

export const fmtEUR = (cents) => {
  if (cents == null) return '—';
  return `${(cents / 100).toFixed(2)} €`;
};
