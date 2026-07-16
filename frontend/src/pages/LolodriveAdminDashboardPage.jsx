import i18n from '@/i18n';
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
  '7d':  { label: i18n.t('adm.7_jours'),  days: 7 },
  '30d': { label: i18n.t('adm.30_jours'), days: 30 },
  '90d': { label: i18n.t('adm.90_jours'), days: 90 },
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
      toast.error(i18n.t('adm.erreur_de_chargement_2') + e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(period); /* eslint-disable-line */ }, [period]);

  const rebuildCRM = async () => {
    try {
      const r = await crmAPI.rebuildFromLolodrive();
      toast.success(i18n.t('adm.crm_resynchronise'));
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
      title={i18n.t('adm.dashboard_super_admin')}
      subtitle={i18n.t('adm.pilotage_global')}
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
            <RefreshCw className="w-4 h-4 mr-2" /> {i18n.t('adm.actualiser')}
          </Button>
          <Button size="sm" onClick={rebuildCRM} data-testid="rebuild-crm-btn"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
            <Sparkles className="w-4 h-4 mr-2" /> Resync CRM
          </Button>
        </>
      }
    >
      {loading && !kpi && <div className="text-center text-white/50 py-12">{i18n.t('adm.chargement')}</div>}
      {kpi && (
        <>
          {/* KPI primaires */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-pass-active" label={i18n.t('adm.pass_actifs')} value={kpi.pass_active} sub={i18n.t('adm.a_l_instant_t')} icon={Ticket} accent="#D9B35A" />
            <KpiCard testId="kpi-orders-count" label={i18n.t('adm.commandes_period', { period: PERIODS[period].label })} value={kpi.orders?.count || 0} sub={fmtEUR(totalRevenue)} icon={ShoppingBag} accent="#10b981" />
            <KpiCard testId="kpi-points-active" label={i18n.t('adm.relais_lolodrive_actifs')} value={kpi.lolo_points_active} icon={Store} accent="#7c3aed" />
            <KpiCard testId="kpi-events-active" label={i18n.t('adm.lolo_hour_actifs')} value={kpi.events_active} icon={Sparkles} accent="#ec4899" />
          </div>

          {/* CA Jour / Mois + UC en circulation / consommées */}
          {dash && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <KpiCard testId="kpi-ca-today" label={i18n.t('adm.ca_aujourd_hui')} value={fmtEUR(dash.ca_today.revenue_cents)}
                sub={i18n.t('adm.commandes_count', { count: dash.ca_today.orders })} icon={TrendingUp} accent="#10b981" />
              <KpiCard testId="kpi-ca-month" label={i18n.t('adm.ca_mois_en_cours')} value={fmtEUR(dash.ca_month.revenue_cents)}
                sub={i18n.t('adm.commandes_count', { count: dash.ca_month.orders })} icon={BarChart3} accent="#3b82f6" />
              <KpiCard testId="kpi-uc-circulation" label={i18n.t('adm.uc_en_circulation')} value={dash.uc_in_circulation}
                sub={i18n.t('adm.somme_des_wallets_actifs')} icon={Wallet} accent="#D9B35A" />
              <KpiCard testId="kpi-uc-consumed" label={i18n.t('adm.uc_consommees')} value={dash.uc_consumed}
                sub={i18n.t('adm.depuis_le_lancement')} icon={Activity} accent="#7c3aed" />
            </div>
          )}

          {/* Alertes */}
          {dash?.alerts && dash.alerts.length > 0 && (
            <SectionCard className="mb-6" title={i18n.t('adm.alertes_operationnelles')}>
              <div className="space-y-2" data-testid="alerts-section">
                {dash.alerts.map((a) => (
                  <AlertRow key={`${a.severity}-${a.message}`} severity={a.severity} message={a.message} />
                ))}
              </div>
            </SectionCard>
          )}

          {/* Top produits */}
          {dash?.top_products && dash.top_products.length > 0 && (
            <SectionCard
              className="mb-6"
              title={i18n.t('adm.top_produits_30_jours')}
              action={<Badge color="#D9B35A">{i18n.t('adm.volume_vendu')}</Badge>}
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
                        {p.sku} {p.catalog_type === 'ESSENTIAL' && <Badge color="#D9B35A">{i18n.t('adm.essentiel')}</Badge>}
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
                <h3 className="text-sm font-semibold">{i18n.t('adm.repartition_revenus_par_mode_de')}</h3>
                <Badge color="#D9B35A">{fmtEUR(totalRevenue)}</Badge>
              </div>
              <RepartitionBar
                segments={[
                  { label: i18n.t('adm.drive'), value: kpi.orders?.drive || 0, color: '#10b981' },
                  { label: i18n.t('adm.livraison'), value: kpi.orders?.delivery || 0, color: '#3b82f6' },
                  { label: i18n.t('adm.relais'), value: kpi.orders?.lolo_point || 0, color: '#7c3aed' },
                ]}
              />
            </SectionCard>

            <SectionCard>
              <h3 className="text-sm font-semibold mb-3">{i18n.t('adm.engagement_pass')}</h3>
              <div className="space-y-3">
                <Stat label={i18n.t('adm.commandes_payees_en_uc')} value={`${conversionRate}%`} accent="#D9B35A" />
                <Stat label={i18n.t('adm.panier_moyen')} value={fmtEUR(kpi.orders?.count ? Math.round(totalRevenue / kpi.orders.count) : 0)} accent="#10b981" />
                <Stat label={i18n.t('adm.uc_debites')} value={`${kpi.wallet?.debited_uc || 0} UC`} accent="#7c3aed" />
              </div>
            </SectionCard>
          </div>

          {/* Activité POS */}
          <SectionCard
            title={i18n.t('adm.activite_pos_en_cours')}
            action={
              <Link to="/pos" className="text-xs text-[#D9B35A] hover:underline flex items-center gap-1" data-testid="link-pos">
                Ouvrir POS <ArrowRight className="w-3 h-3" />
              </Link>
            }
            className="mb-6"
          >
            {posOrders.length === 0 && (
              <div className="text-sm text-white/40 py-4 text-center">{i18n.t('adm.aucune_commande_active')}</div>
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
                        {o.fulfillment_type} · {i18n.t('orders.articles_count', { count: o.items?.length || 0 })} · {fmtEUR(o.total_cents)}
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
              title={i18n.t('adm.couche_relationnelle_crm_lecture_seule')}
              action={<Badge color="#7c3aed">{i18n.t('adm.source_v2_events')}</Badge>}
              className="mb-6"
            >
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard testId="kpi-contacts" label="Contacts" value={impact.crm_contacts} icon={HeartHandshake} accent="#ec4899" />
                <KpiCard testId="kpi-orgs" label={i18n.t('adm.partenaires')} value={impact.partners} icon={Building2} accent="#3b82f6" />
                <KpiCard testId="kpi-opps" label={i18n.t('adm.opportunites')} value={impact.crm_opportunities} icon={Activity} accent="#D9B35A" />
                <KpiCard testId="kpi-dossiers" label={i18n.t('adm.dossiers_ouverts')} value={impact.crm_dossiers} icon={Leaf} accent="#10b981" />
              </div>
              <p className="mt-4 text-xs text-white/40 italic border-l-2 border-[#D9B35A] pl-3">
                {impact.impact_positioning}
              </p>
            </SectionCard>
          )}

          {/* Accès rapide */}
          <SectionCard title={i18n.t('adm.acces_rapide_aux_modules')}>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {[
                { to: '/pos', label: i18n.t('adm.pos_lolodrive'), icon: Truck, color: '#10b981', phase: 1 },
                { to: '/pass', label: i18n.t('adm.espace_pass'), icon: Ticket, color: '#D9B35A', phase: 1 },
                { to: '/catalogue-lolodrive', label: i18n.t('adm.catalogue'), icon: ShoppingBag, color: '#7c3aed', phase: 1 },
                { to: '/lolo-point/dashboard', label: i18n.t('adm.vue_gerant_lp'), icon: Store, color: '#10b981', phase: 2 },
                { to: '/admin/lolo-points', label: i18n.t('adm.reseau_lolodrive'), icon: Store, color: '#7c3aed', phase: 2 },
                { to: '/admin/lolo-hour', label: i18n.t('adm.lolo_hour'), icon: Sparkles, color: '#ec4899', phase: 2 },
                { to: '/crm', label: i18n.t('adm.crm_partenaires'), icon: HeartHandshake, color: '#D9B35A', phase: 2 },
                { to: '/reporting-impact', label: i18n.t('adm.reporting_ess'), icon: Leaf, color: '#10b981', phase: 2 },
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
                    {l.phase === 2 && <div className="text-[9px] uppercase tracking-wider text-white/30 mt-0.5">{i18n.t('adm.phase_2_leger')}</div>}
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
                <div className="font-semibold text-sm mb-2 text-[#D9B35A]">{i18n.t('adm.regles_metier_non_negociables')}</div>
                <ul className="text-xs text-white/70 space-y-1 list-disc list-inside">
                  <li>{i18n.t('adm.les_uc_ne_sont_pas')}</li>
                  <li>{i18n.t('adm.pass_vie_chere_60_600')} <strong>{i18n.t('adm.sans_renouvellement_automatique')}</strong>.</li>
                  <li>{i18n.t('adm.essentiels_prix_pass_visible_si')}</li>
                  <li>{i18n.t('adm.le_crm_ne_duplique_pas')}</li>
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
