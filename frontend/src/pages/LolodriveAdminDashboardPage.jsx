import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Ticket, Wallet, Truck, Store, Sparkles, ShoppingBag, BarChart3, Activity,
  Building2, HeartHandshake, Leaf, ArrowRight, RefreshCw, AlertTriangle,
  TrendingUp, Clock, CheckCircle2, Package, AlertCircle,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { lolodriveAPI, crmAPI } from '../services/api';
import { toast } from 'sonner';

const PERIODS = {
  '7d':  { label: '7 jours',  days: 7 },
  '30d': { label: '30 jours', days: 30 },
  '90d': { label: '90 jours', days: 90 },
};

export default function LolodriveAdminDashboardPage() {
  const [kpi, setKpi] = useState(null);
  const [dash, setDash] = useState(null);
  const [impact, setImpact] = useState(null);
  const [posOrders, setPosOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('30d');

  const load = async (p = period) => {
    try {
      setLoading(true);
      const fromDate = new Date(Date.now() - PERIODS[p].days * 86400_000).toISOString();
      const [k, d, i, po] = await Promise.all([
        lolodriveAPI.kpiOverview(fromDate),
        lolodriveAPI.kpiDashboard(),
        crmAPI.impactSummary(),
        lolodriveAPI.posOrders(),
      ]);
      setKpi(k);
      setDash(d);
      setImpact(i);
      setPosOrders(po.orders || []);
    } catch (e) {
      toast.error('Erreur de chargement : ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(period); /* eslint-disable-line */ }, [period]);

  const rebuildCRM = async () => {
    try {
      const r = await crmAPI.rebuildFromLolodrive();
      toast.success(`CRM resynchronisé`);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  // Repartition revenue
  const totalRevenue = kpi?.orders?.revenue_cents || 0;
  const conversionRate = kpi?.pass_active > 0 && (kpi?.orders?.count || 0) > 0
    ? Math.round(((kpi.orders.paid_uc || 0) / Math.max(1, kpi.orders.count)) * 100)
    : 0;

  return (
    <LolodriveLayout
      title="Dashboard Super Admin"
      subtitle="Pilotage global LOLODRIVE by O'SCOP — moteur transactionnel V2 + couche relationnelle CRM."
      actions={
        <>
          <Tabs value={period} onValueChange={setPeriod}>
            <TabsList className="bg-white/[0.04] border border-white/10" data-testid="period-tabs">
              {Object.entries(PERIODS).map(([k, v]) => (
                <TabsTrigger key={k} value={k} data-testid={`period-${k}`}>{v.label}</TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          <Button variant="outline" size="sm" onClick={() => load()} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
          </Button>
          <Button size="sm" onClick={rebuildCRM} data-testid="rebuild-crm-btn"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
            <Sparkles className="w-4 h-4 mr-2" /> Resync CRM
          </Button>
        </>
      }
    >
      {loading && !kpi && <div className="text-center text-white/50 py-12">Chargement…</div>}
      {kpi && (
        <>
          {/* KPI primaires */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-pass-active" label="PASS actifs" value={kpi.pass_active} sub="à l'instant T" icon={Ticket} accent="#D9B35A" />
            <KpiCard testId="kpi-orders-count" label={`Commandes (${PERIODS[period].label})`} value={kpi.orders?.count || 0} sub={fmtEUR(totalRevenue)} icon={ShoppingBag} accent="#10b981" />
            <KpiCard testId="kpi-points-active" label="LOLO POINTS actifs" value={kpi.lolo_points_active} icon={Store} accent="#7c3aed" />
            <KpiCard testId="kpi-events-active" label="LOLO HOUR actifs" value={kpi.events_active} icon={Sparkles} accent="#ec4899" />
          </div>

          {/* CA Jour / Mois + UC en circulation / consommées */}
          {dash && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <KpiCard testId="kpi-ca-today" label="CA aujourd'hui" value={fmtEUR(dash.ca_today.revenue_cents)}
                sub={`${dash.ca_today.orders} commande(s)`} icon={TrendingUp} accent="#10b981" />
              <KpiCard testId="kpi-ca-month" label="CA mois en cours" value={fmtEUR(dash.ca_month.revenue_cents)}
                sub={`${dash.ca_month.orders} commande(s)`} icon={BarChart3} accent="#3b82f6" />
              <KpiCard testId="kpi-uc-circulation" label="UC en circulation" value={dash.uc_in_circulation}
                sub="somme des wallets actifs" icon={Wallet} accent="#D9B35A" />
              <KpiCard testId="kpi-uc-consumed" label="UC consommées" value={dash.uc_consumed}
                sub="depuis le lancement" icon={Activity} accent="#7c3aed" />
            </div>
          )}

          {/* Alertes */}
          {dash?.alerts && dash.alerts.length > 0 && (
            <SectionCard className="mb-6" title="Alertes opérationnelles">
              <div className="space-y-2" data-testid="alerts-section">
                {dash.alerts.map((a, idx) => (
                  <AlertRow key={idx} severity={a.severity} message={a.message} />
                ))}
              </div>
            </SectionCard>
          )}

          {/* Top produits */}
          {dash?.top_products && dash.top_products.length > 0 && (
            <SectionCard
              className="mb-6"
              title="Top produits (30 jours)"
              action={<Badge color="#D9B35A">Volume vendu</Badge>}
            >
              <div className="space-y-2" data-testid="top-products-section">
                {dash.top_products.map((p, idx) => (
                  <div key={p.sku} data-testid={`top-product-${p.sku}`}
                    className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
                      style={{ background: '#D9B35A1f', color: '#D9B35A' }}>#{idx + 1}</div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{p.name}</div>
                      <div className="text-xs text-white/40">
                        {p.sku} {p.catalog_type === 'ESSENTIAL' && <Badge color="#D9B35A">ESSENTIEL</Badge>}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-bold">{p.qty} u.</div>
                      <div className="text-xs text-white/40">{fmtEUR(p.revenue_cents)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>
          )}

          {/* Revenu, panier moyen, conversion */}
          <div className="grid md:grid-cols-3 gap-4 mb-6">
            <SectionCard className="col-span-2">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold">Répartition revenus par mode de retrait</h3>
                <Badge color="#D9B35A">{fmtEUR(totalRevenue)}</Badge>
              </div>
              <RepartitionBar
                segments={[
                  { label: 'Drive', value: kpi.orders?.drive || 0, color: '#10b981' },
                  { label: 'Livraison', value: kpi.orders?.delivery || 0, color: '#3b82f6' },
                  { label: 'Lolo Point', value: kpi.orders?.lolo_point || 0, color: '#7c3aed' },
                ]}
              />
            </SectionCard>

            <SectionCard>
              <h3 className="text-sm font-semibold mb-3">Engagement PASS</h3>
              <div className="space-y-3">
                <Stat label="Commandes payées en UC" value={`${conversionRate}%`} accent="#D9B35A" />
                <Stat label="Panier moyen" value={fmtEUR(kpi.orders?.count ? Math.round(totalRevenue / kpi.orders.count) : 0)} accent="#10b981" />
                <Stat label="UC débités" value={`${kpi.wallet?.debited_uc || 0} UC`} accent="#7c3aed" />
              </div>
            </SectionCard>
          </div>

          {/* Activité POS */}
          <SectionCard
            title="Activité POS en cours"
            action={
              <Link to="/pos" className="text-xs text-[#D9B35A] hover:underline flex items-center gap-1" data-testid="link-pos">
                Ouvrir POS <ArrowRight className="w-3 h-3" />
              </Link>
            }
            className="mb-6"
          >
            {posOrders.length === 0 && (
              <div className="text-sm text-white/40 py-4 text-center">Aucune commande active.</div>
            )}
            <div className="space-y-2">
              {posOrders.slice(0, 5).map((o) => (
                <div key={o.id} data-testid={`pos-row-${o.id}`}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                  <div className="flex items-center gap-3 min-w-0">
                    {iconFor(o.status)}
                    <div className="min-w-0">
                      <div className="font-mono text-sm font-semibold truncate">{o.order_number}</div>
                      <div className="text-xs text-white/40">
                        {o.fulfillment_type} · {o.items?.length || 0} article(s) · {fmtEUR(o.total_cents)}
                      </div>
                    </div>
                  </div>
                  <Badge color={statusColor(o.status)}>{o.status}</Badge>
                </div>
              ))}
            </div>
          </SectionCard>

          {/* CRM Impact */}
          {impact && (
            <SectionCard
              title="Couche relationnelle CRM (lecture seule)"
              action={<Badge color="#7c3aed">Source : V2 → events</Badge>}
              className="mb-6"
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

          {/* Accès rapide */}
          <SectionCard title="Accès rapide aux modules">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {[
                { to: '/pos', label: 'POS LOLODRIVE', icon: Truck, color: '#10b981', phase: 1 },
                { to: '/pass', label: 'Espace PASS', icon: Ticket, color: '#D9B35A', phase: 1 },
                { to: '/catalogue-lolodrive', label: 'Catalogue', icon: ShoppingBag, color: '#7c3aed', phase: 1 },
                { to: '/admin/lolo-points', label: 'LOLO POINTS', icon: Store, color: '#7c3aed', phase: 2 },
                { to: '/admin/lolo-hour', label: 'LOLO HOUR', icon: Sparkles, color: '#ec4899', phase: 2 },
                { to: '/crm', label: 'CRM Partenaires', icon: HeartHandshake, color: '#D9B35A', phase: 2 },
                { to: '/reporting-impact', label: 'Reporting ESS', icon: Leaf, color: '#10b981', phase: 2 },
                { to: '/super-admin', label: 'KPIs étendus', icon: BarChart3, color: '#3b82f6', phase: 1 },
              ].map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  data-testid={`quick-link-${l.to.replace(/\//g, '-')}`}
                  className="group flex items-center gap-3 rounded-xl p-3 bg-white/[0.025] border border-white/[0.07] hover:border-white/[0.15] hover:bg-white/[0.05] transition-all"
                >
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${l.color}1f` }}>
                    <l.icon className="w-4 h-4" style={{ color: l.color }} />
                  </div>
                  <div className="flex-1 text-sm leading-tight">
                    {l.label}
                    {l.phase === 2 && <div className="text-[9px] uppercase tracking-wider text-white/30 mt-0.5">Phase 2 · léger</div>}
                  </div>
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

const Stat = ({ label, value, accent }) => (
  <div className="flex items-center justify-between p-2 rounded bg-white/[0.02]">
    <span className="text-xs text-white/60">{label}</span>
    <span className="font-bold text-sm" style={{ color: accent }}>{value}</span>
  </div>
);

const RepartitionBar = ({ segments }) => {
  const total = Math.max(1, segments.reduce((a, s) => a + s.value, 0));
  return (
    <div>
      <div className="flex h-3 rounded-full overflow-hidden bg-white/[0.05]">
        {segments.map((s) => s.value > 0 && (
          <div key={s.label} title={`${s.label}: ${s.value}`}
            style={{ width: `${(s.value / total) * 100}%`, background: s.color }} />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3 mt-3 text-xs">
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ background: s.color }} />
            <span className="text-white/60">{s.label}</span>
            <span className="ml-auto font-medium">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const statusColor = (s) => {
  if (s === 'FULFILLED') return '#10b981';
  if (s === 'READY') return '#D9B35A';
  if (s === 'PREPARING' || s === 'PAID') return '#3b82f6';
  return '#7c3aed';
};

const iconFor = (status) => {
  const cls = "w-8 h-8 rounded-lg flex items-center justify-center shrink-0";
  if (status === 'FULFILLED') return <div className={cls} style={{ background: '#10b98120' }}><CheckCircle2 className="w-4 h-4 text-emerald-400" /></div>;
  if (status === 'READY') return <div className={cls} style={{ background: '#D9B35A20' }}><Clock className="w-4 h-4 text-[#D9B35A]" /></div>;
  return <div className={cls} style={{ background: '#3b82f620' }}><TrendingUp className="w-4 h-4 text-blue-400" /></div>;
};

const AlertRow = ({ severity, message }) => {
  const cfg = {
    critical: { color: '#ef4444', bg: '#ef44441f', icon: <AlertCircle className="w-4 h-4" /> },
    warning:  { color: '#f59e0b', bg: '#f59e0b1f', icon: <AlertTriangle className="w-4 h-4" /> },
    ok:       { color: '#10b981', bg: '#10b9811f', icon: <CheckCircle2 className="w-4 h-4" /> },
  }[severity] || { color: '#888', bg: '#8881', icon: <AlertCircle className="w-4 h-4" /> };
  return (
    <div data-testid={`alert-${severity}`}
      className="flex items-center gap-3 p-3 rounded-lg border"
      style={{ background: cfg.bg, borderColor: `${cfg.color}33` }}>
      <div className="w-7 h-7 rounded-md flex items-center justify-center" style={{ color: cfg.color }}>{cfg.icon}</div>
      <div className="text-sm flex-1" style={{ color: cfg.color }}>{message}</div>
    </div>
  );
};
