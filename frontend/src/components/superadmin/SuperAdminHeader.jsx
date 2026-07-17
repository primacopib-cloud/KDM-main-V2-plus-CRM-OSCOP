import i18n from '@/i18n';
import { Link } from 'react-router-dom';
import {
  LayoutDashboard, Users, Package, ShoppingCart, RefreshCw, Shield, BarChart3, ShieldCheck,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';
import { partners } from '../../data/mock';
import { ConnectionStatus } from '../NotificationToast';
import NavigationHistoryDropdown from '../NavigationHistoryDropdown';

const NAV_LINKS = [
  { to: '/', label: i18n.t('adm.accueil') },
  { to: '/espace-acheteur', label: i18n.t('adm.espace_acheteur') },
  { to: '/espace-vendeur', label: i18n.t('adm.espace_vendeur') },
  { to: '/catalogue', label: i18n.t('adm.catalogue') },
  { to: '/admin-v2', label: i18n.t('adm.admin_orgs') },
  { to: '/admin/produits', label: i18n.t('adm.validation') },
];

const TABS = [
  { value: 'dashboard', label: i18n.t('adm.dashboard'), icon: LayoutDashboard },
  { value: 'stats', label: i18n.t('adm.statistiques'), icon: BarChart3 },
  { value: 'catalog', label: i18n.t('adm.catalogue'), icon: Package },
  { value: 'users', label: i18n.t('adm.utilisateurs'), icon: Users },
  { value: 'roles', label: i18n.t('adm.team_tab'), icon: ShieldCheck },
  { value: 'orders', label: i18n.t('adm.commandes'), icon: ShoppingCart },
];

export const SuperAdminHeader = ({
  activeTab, setActiveTab, period, setPeriod, onRefresh, isConnected,
}) => (
  <header
    className="sticky top-0 z-50"
    style={{
      background: 'rgba(255,253,247,0.96)',
      backdropFilter: 'blur(10px)',
      borderBottom: '1px solid rgba(212,175,55,0.32)'
    }}
  >
    <div className="max-w-[1400px] mx-auto px-5 py-3 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2">
          <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-8 w-auto object-contain" />
          <span className="text-white/30 text-xs">×</span>
          <img src={partners.oscop.logo} alt="O'SCOP" className="h-5 w-auto object-contain" />
        </Link>
        <div className="h-6 w-px bg-white/10" />
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-[#EF4444]" />
          <span className="text-sm font-semibold text-white/90">{i18n.t('adm.super_admin')}</span>
        </div>
      </div>

      {/* Quick Navigation */}
      <nav className="hidden lg:flex items-center gap-1">
        {NAV_LINKS.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
          >
            {l.label}
          </Link>
        ))}
      </nav>

      <div className="flex items-center gap-3">
        <NavigationHistoryDropdown variant="dark" />
        <ConnectionStatus isConnected={isConnected} />

        {/* Period Selector */}
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white/80"
        >
          <option value="day">{i18n.t('adm.aujourd_hui')}</option>
          <option value="week">{i18n.t('adm.cette_semaine')}</option>
          <option value="month">{i18n.t('adm.ce_mois')}</option>
          <option value="year">{i18n.t('adm.cette_annee')}</option>
          <option value="all">{i18n.t('adm.tout')}</option>
        </select>

        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          className="border-white/10 hover:bg-white/5"
        >
          <RefreshCw className="w-4 h-4 mr-1" />
          {i18n.t('adm.actualiser')}
        </Button>
      </div>
    </div>

    {/* Tabs Navigation */}
    <div className="max-w-[1400px] mx-auto px-5 pb-3">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1 rounded-xl">
          {TABS.map((t) => (
            <TabsTrigger
              key={t.value}
              value={t.value}
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
            >
              <t.icon className="w-4 h-4 mr-2" />
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
    </div>
  </header>
);
