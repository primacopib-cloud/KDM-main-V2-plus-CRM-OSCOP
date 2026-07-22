import i18n from '@/i18n';
import { Link } from 'react-router-dom';
import { Users, ShoppingCart, Building2 } from 'lucide-react';
import { Button } from '../ui/button';
import { formatCurrency } from './widgets';
import { CodCollectionPanel } from './CodCollectionPanel';

export const UsersTab = ({ kpis }) => (
  <div className="rounded-2xl bg-white/[0.02] border border-white/[0.08] p-6">
    <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
      <Users className="w-5 h-5 text-[#3B82F6]" />
      Gestion des utilisateurs
    </h2>
    <p className="text-white/60 mb-6">{i18n.t('adm.vue_d_ensemble_des_utilisateurs')}</p>

    <div className="grid sm:grid-cols-3 gap-4 mb-6">
      <div className="p-4 rounded-xl bg-[#3B82F6]/10 border border-[#3B82F6]/20 text-center">
        <div className="text-3xl font-bold text-[#3B82F6]">{kpis?.users?.total || 0}</div>
        <div className="text-sm text-white/60">{i18n.t('adm.total_utilisateurs')}</div>
      </div>
      <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
        <div className="text-3xl font-bold text-emerald-400">{kpis?.users?.active || 0}</div>
        <div className="text-sm text-white/60">{i18n.t('adm.actifs')}</div>
      </div>
      <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 text-center">
        <div className="text-3xl font-bold text-purple-400">{kpis?.users?.organizations?.approved || 0}</div>
        <div className="text-sm text-white/60">{i18n.t('adm.organisations')}</div>
      </div>
    </div>

    <div className="flex gap-3">
      <Link to="/admin-v2">
        <Button className="bg-[#3B82F6] hover:bg-[#2563EB] text-white">
          <Building2 className="w-4 h-4 mr-2" />
          {i18n.t('adm.gerer_les_organisations')}
        </Button>
      </Link>
    </div>
  </div>
);

export const OrdersTab = ({ kpis }) => (
  <div className="rounded-2xl bg-white/[0.02] border border-white/[0.08] p-6">
    <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
      <ShoppingCart className="w-5 h-5 text-[#F59E0B]" />
      Gestion des commandes
    </h2>
    <p className="text-white/60 mb-6">{i18n.t('adm.suivi_des_commandes_et_paiements')}</p>

    <div className="grid sm:grid-cols-4 gap-4 mb-6">
      <div className="p-4 rounded-xl bg-[#D9B35A]/10 border border-[#D9B35A]/20 text-center">
        <div className="text-3xl font-bold text-[#D9B35A]">{formatCurrency(kpis?.sales?.total_revenue)}</div>
        <div className="text-sm text-white/60">{i18n.t('adm.ca_total')}</div>
      </div>
      <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-center">
        <div className="text-3xl font-bold text-blue-400">{kpis?.sales?.total_orders || 0}</div>
        <div className="text-sm text-white/60">{i18n.t('adm.commandes')}</div>
      </div>
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-center">
        <div className="text-3xl font-bold text-amber-400">{kpis?.sales?.pending_orders || 0}</div>
        <div className="text-sm text-white/60">{i18n.t('adm.en_attente')}</div>
      </div>
      <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
        <div className="text-3xl font-bold text-emerald-400">{formatCurrency(kpis?.sales?.average_basket)}</div>
        <div className="text-sm text-white/60">{i18n.t('adm.panier_moyen')}</div>
      </div>
    </div>

    {kpis?.sales?.orders_by_status && (
      <div className="mb-6">
        <p className="text-sm text-white/50 mb-3">{i18n.t('adm.repartition_par_statut')}</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(kpis.sales.orders_by_status).map(([status, count]) => (
            <span key={status} className="px-3 py-1.5 rounded-full bg-white/[0.04] text-sm text-white/70 border border-white/[0.08]">
              {status}: <span className="font-bold text-white">{count}</span>
            </span>
          ))}
        </div>
      </div>
    )}

    <CodCollectionPanel />

    <Link to="/commandes">
      <Button className="bg-[#F59E0B] hover:bg-[#D97706] text-black">
        <ShoppingCart className="w-4 h-4 mr-2" />
        Voir toutes les commandes
      </Button>
    </Link>
  </div>
);
