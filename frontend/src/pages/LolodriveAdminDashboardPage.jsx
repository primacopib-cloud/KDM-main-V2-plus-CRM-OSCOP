import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Ticket, Wallet, Truck, Store, Sparkles, ShoppingBag, BarChart3, Activity,
  Building2, HeartHandshake, Leaf, ArrowRight, RefreshCw, AlertTriangle,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { lolodriveAPI, crmAPI } from '../services/api';
import { toast } from 'sonner';

export default function LolodriveAdminDashboardPage() {
  const [kpi, setKpi] = useState(null);
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      setLoading(true);
      const [k, i] = await Promise.all([
        lolodriveAPI.kpiOverview(),
        crmAPI.impactSummary(),
      ]);
      setKpi(k);
      setImpact(i);
    } catch (e) {
      toast.error('Erreur de chargement : ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const rebuildCRM = async () => {
    try {
      const r = await crmAPI.rebuildFromLolodrive();
      toast.success(`CRM mis à jour : ${JSON.stringify(r.rebuilt)}`);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <LolodriveLayout
      title="Dashboard Super Admin"
      subtitle="Pilotage global LOLODRIVE by O'SCOP — moteur transactionnel V2 + couche relationnelle CRM."
      actions={
        <>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
          </Button>
          <Button size="sm" onClick={rebuildCRM} data-testid="rebuild-crm-btn"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
            <Sparkles className="w-4 h-4 mr-2" /> Resync CRM
          </Button>
        </>
      }
    >
      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}
      {!loading && kpi && (
        <>
          {/* PASS / Réseau */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-pass-active" label="PASS actifs" value={kpi.pass_active} icon={Ticket} accent="#D9B35A" />
            <KpiCard testId="kpi-orders-count" label="Commandes (30j)" value={kpi.orders?.count || 0} sub={fmtEUR(kpi.orders?.revenue_cents)} icon={ShoppingBag} accent="#10b981" />
            <KpiCard testId="kpi-points-active" label="LOLO POINTS actifs" value={kpi.lolo_points_active} icon={Store} accent="#7c3aed" />
            <KpiCard testId="kpi-events-active" label="LOLO HOUR actifs" value={kpi.events_active} icon={Sparkles} accent="#ec4899" />
          </div>

          {/* Détail commandes */}
          <SectionCard title="Répartition des commandes (30 jours)" className="mb-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Stat label="Drive" v={kpi.orders?.drive || 0} color="#10b981" />
              <Stat label="Livraison" v={kpi.orders?.delivery || 0} color="#3b82f6" />
              <Stat label="Lolo Point" v={kpi.orders?.lolo_point || 0} color="#7c3aed" />
              <Stat label="Payées en UC" v={kpi.orders?.paid_uc || 0} sub={`${kpi.wallet?.debited_uc || 0} UC débités`} color="#D9B35A" />
            </div>
          </SectionCard>

          {/* CRM Impact */}
          {impact && (
            <SectionCard title="Couche relationnelle CRM (lecture seule)" className="mb-6"
              action={
                <Badge color="#7c3aed">Source : V2 → events</Badge>
              }
            >
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard testId="kpi-contacts" label="Contacts" value={impact.crm_contacts} icon={HeartHandshake} accent="#ec4899" />
                <KpiCard testId="kpi-orgs" label="Partenaires" value={impact.partners} icon={Building2} accent="#3b82f6" />
                <KpiCard testId="kpi-opps" label="Opportunités" value={impact.crm_opportunities} icon={Activity} accent="#D9B35A" />
                <KpiCard testId="kpi-dossiers" label="Dossiers ouverts" value={impact.crm_dossiers} icon={Leaf} accent="#10b981" />
              </div>
              <p className="mt-4 text-xs text-white/40 italic border-l-2 border-[#D9B35A] pl-3">
                {impact.impact_positioning}
              </p>
            </SectionCard>
          )}

          {/* Quick links */}
          <SectionCard title="Accès rapide aux modules">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {[
                { to: '/pos', label: 'POS LOLODRIVE', icon: Truck, color: '#10b981' },
                { to: '/admin/lolo-points', label: 'LOLO POINTS', icon: Store, color: '#7c3aed' },
                { to: '/admin/lolo-hour', label: 'LOLO HOUR', icon: Sparkles, color: '#ec4899' },
                { to: '/crm', label: 'CRM Partenaires', icon: HeartHandshake, color: '#D9B35A' },
                { to: '/reporting-impact', label: 'Reporting impact ESS', icon: Leaf, color: '#10b981' },
                { to: '/pass', label: 'Espace PASS (demo)', icon: Ticket, color: '#D9B35A' },
                { to: '/super-admin', label: 'KPIs étendus', icon: BarChart3, color: '#3b82f6' },
                { to: '/catalogue', label: 'Catalogue KDM', icon: ShoppingBag, color: '#7c3aed' },
              ].map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  data-testid={`quick-link-${l.to.replace(/\//g, '-')}`}
                  className="group flex items-center gap-3 rounded-xl p-3 bg-white/[0.025] border border-white/[0.07] hover:border-white/[0.15] hover:bg-white/[0.05] transition-all"
                >
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${l.color}1f` }}>
                    <l.icon className="w-4 h-4" style={{ color: l.color }} />
                  </div>
                  <div className="flex-1 text-sm">{l.label}</div>
                  <ArrowRight className="w-4 h-4 text-white/30 group-hover:text-white/70 group-hover:translate-x-0.5 transition-all" />
                </Link>
              ))}
            </div>
          </SectionCard>

          {/* Règles rappel */}
          <div className="mt-8 rounded-2xl p-5 border border-[#D9B35A]/30 bg-[#D9B35A]/[0.04]">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[#D9B35A] mt-0.5 shrink-0" />
              <div>
                <div className="font-semibold text-sm mb-2 text-[#D9B35A]">Règles métier (non négociables)</div>
                <ul className="text-xs text-white/70 space-y-1 list-disc list-inside">
                  <li>Les UC ne sont pas une monnaie. Référence : prix en euros.</li>
                  <li>PASS Vie Chère : 60 € = 600 UC, 30 jours, <strong>sans renouvellement automatique</strong>.</li>
                  <li>ESSENTIELS : prix PASS visible si PASS actif. Hors25 : prix normal, payable en UC sans avantage.</li>
                  <li>Le CRM ne duplique pas le wallet UC. La V2 reste la source de vérité transactionnelle.</li>
                </ul>
              </div>
            </div>
          </div>
        </>
      )}
    </LolodriveLayout>
  );
}

const Stat = ({ label, v, sub, color }) => (
  <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-4">
    <div className="text-2xl font-bold" style={{ color }}>{v}</div>
    <div className="text-xs text-white/50 mt-1">{label}</div>
    {sub && <div className="text-[10px] text-white/30 mt-0.5">{sub}</div>}
  </div>
);
