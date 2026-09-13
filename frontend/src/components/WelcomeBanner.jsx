import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import {
  Sparkles, ArrowRight, ShoppingCart, Package, Wallet, FileText,
  CreditCard, LayoutDashboard, Store, ClipboardList, Users, Pencil, Loader2,
} from 'lucide-react';
import { authAPI } from '../services/api';
import { API, getAuthHeaders } from '../services/http';

// Message de bienvenue + 3 actions prioritaires par espace de rôle (textes : i18n clés welcome.*)
const SPACE_CONFIG = {
  buyer: [
    { href: '/catalogue', icon: ShoppingCart },
    { href: '/commandes', icon: Package },
    { href: '/wallet', icon: Wallet },
  ],
  vendor: [
    { href: '/espace-vendeur?tab=products', icon: Package },
    { href: '/espace-vendeur?tab=orders', icon: ShoppingCart },
    { href: '/espace-vendeur?tab=invoices', icon: FileText },
  ],
  pass: [
    { href: '/catalogue-lolodrive', icon: ShoppingCart },
    { href: '/commandes', icon: Package },
    { href: '/espace-pass', icon: CreditCard },
  ],
  pos: [
    { href: '/pos', icon: CreditCard },
    { href: '/commandes', icon: ClipboardList },
    { href: '/catalogue-lolodrive', icon: ShoppingCart },
  ],
  gerant: [
    { href: '/lolo-point/dashboard', icon: LayoutDashboard },
    { href: '/pos', icon: CreditCard },
    { href: '/commandes', icon: Package },
  ],
  cooper: [
    { href: '/espace-cooper', icon: Users },
    { href: '/catalogue', icon: ShoppingCart },
    { href: '/commandes', icon: Package },
  ],
  investor: [
    { href: '/espace-investisseur', icon: LayoutDashboard },
    { href: '/catalogue', icon: Store },
    { href: '/documents', icon: FileText },
  ],
};

export const WelcomeBanner = ({ space, className = '' }) => {
  const { t } = useTranslation();
  const cfg = SPACE_CONFIG[space];
  const [savedName, setSavedName] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  if (!cfg) return null;
  const user = authAPI.getCurrentUser();
  const name = savedName || user?.first_name || user?.company_name || (user?.email || '').split('@')[0] || 'membre';
  const hour = new Date().getHours();
  const greet = t(hour >= 18 || hour < 5 ? 'welcome.evening' : 'welcome.morning', 'Bonjour');

  const saveName = async () => {
    const firstName = draft.trim().split(/\s+/).join(' ');
    if (!firstName) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/profile/first-name`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ first_name: firstName }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      localStorage.setItem('user', JSON.stringify({ ...(user || {}), first_name: d.first_name }));
      setSavedName(d.first_name);
      setEditing(false);
      toast.success(t('welcome.name_saved'));
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div
      className={`rounded-[16px] border border-[#D9B35A]/30 p-4 sm:p-5 ${className}`}
      style={{ background: 'linear-gradient(135deg, rgba(217,179,90,0.12), rgba(255,255,255,0.03))' }}
      data-testid="welcome-banner"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className="w-10 h-10 rounded-xl bg-[#D9B35A]/15 border border-[#D9B35A]/30 flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-[#D9B35A]" />
          </span>
          <div className="min-w-0">
            {editing ? (
              <div className="flex items-center gap-1.5">
                <input
                  autoFocus
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') saveName(); if (e.key === 'Escape') setEditing(false); }}
                  placeholder={t('welcome.name_placeholder')}
                  maxLength={40}
                  data-testid="welcome-name-input"
                  className="h-8 px-2.5 rounded-lg bg-white/[0.08] border border-[#D9B35A]/40 text-sm text-white placeholder:text-white/35 w-44"
                />
                <button type="button" onClick={saveName} disabled={busy} data-testid="welcome-name-save"
                  className="h-8 px-3 rounded-lg text-xs font-bold text-[#2A1045] bg-[#D9B35A] hover:bg-[#F2D07A] transition-colors disabled:opacity-50">
                  {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : t('welcome.name_save')}
                </button>
              </div>
            ) : (
              <p className="text-base sm:text-lg font-bold text-white truncate" data-testid="welcome-greeting">
                {greet} {name}
                <button type="button" onClick={() => { setDraft(user?.first_name || ''); setEditing(true); }}
                  title={t('welcome.name_edit')} data-testid="welcome-name-edit"
                  className="inline-flex ml-2 p-1 rounded-md text-white/35 hover:text-[#D9B35A] hover:bg-white/[0.06] align-middle transition-colors">
                  <Pencil className="w-3.5 h-3.5" />
                </button>
              </p>
            )}
            <p className="text-xs text-white/60">{t(`welcome.${space}.subtitle`)}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {cfg.map((a, i) => (
            <Link
              key={a.href}
              to={a.href}
              data-testid={`welcome-action-${i}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-white/[0.06] border border-white/15 text-white/85 hover:bg-[#D9B35A]/20 hover:border-[#D9B35A]/40 hover:text-white transition-colors"
            >
              <a.icon className="w-3.5 h-3.5 text-[#D9B35A]" />
              {t(`welcome.${space}.a${i}`)}
              <ArrowRight className="w-3 h-3 opacity-50" />
            </Link>
          ))}
        </div>
      </div>
    </div>
    );
};
