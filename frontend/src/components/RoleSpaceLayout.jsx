import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, ShieldAlert } from 'lucide-react';
import NavBar from './NavBar';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const KpiCard = ({ label, value, color = '#B8860B', testId }) => (
  <div className="glass-panel-soft rounded-[18px] p-5" data-testid={testId}>
    <p className="text-xs uppercase tracking-wider opacity-60">{label}</p>
    <p className="text-3xl font-bold mt-1" style={{ color }}>{value ?? '—'}</p>
  </div>
);

export const QuickLink = ({ to, label }) => (
  <Link to={to} className="btn-ghost h-10 px-4 rounded-lg inline-flex items-center text-sm">
    {label}
  </Link>
);

/** Squelette commun aux espaces de rôle (COOPER / EXPERT). */
export const RoleSpaceLayout = ({ title, subtitle, badgeColor, roleName, children, testId }) => {
  const [overview, setOverview] = useState(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    fetch(`${API}/team/overview`, { credentials: 'include' })
      .then((r) => {
        if (r.status === 401 || r.status === 403) { setDenied(true); return null; }
        return r.json();
      })
      .then((d) => d && setOverview(d))
      .catch(() => setDenied(true));
  }, []);

  return (
    <div className="min-h-screen" data-testid={testId}>
      <NavBar />
      <main className="max-w-6xl mx-auto px-5 pt-24 pb-12">
        <div className="mb-6">
          <span
            className="inline-flex text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full mb-2"
            style={{ color: badgeColor, background: `${badgeColor}18`, border: `1px solid ${badgeColor}44` }}
          >
            {roleName}
          </span>
          <h1 className="font-display text-3xl text-[#1F2A3A]">{title}</h1>
          <p className="text-sm opacity-60 mt-1">{subtitle}</p>
        </div>

        {denied ? (
          <div className="glass-panel-soft rounded-[18px] p-8 text-center" data-testid="role-space-denied">
            <ShieldAlert className="w-8 h-8 mx-auto mb-3 text-red-400" />
            <p className="font-medium text-[#1F2A3A]">Accès réservé aux membres de l&apos;équipe</p>
            <p className="text-sm opacity-60 mt-1">Connectez-vous avec un compte {roleName} pour accéder à cet espace.</p>
            <Link to="/connexion" className="btn-gold inline-flex h-10 px-5 rounded-lg items-center text-sm font-semibold mt-4">
              Se connecter
            </Link>
          </div>
        ) : !overview ? (
          <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>
        ) : (
          children(overview)
        )}
      </main>
    </div>
  );
};
