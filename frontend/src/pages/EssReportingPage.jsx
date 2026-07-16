import i18n from '@/i18n';
import React, { useEffect, useState } from 'react';
import {
  Leaf, Ticket, Store, ShoppingBag, Wallet, RefreshCw, Download, Printer,
  HeartHandshake, Briefcase, TrendingUp,
} from 'lucide-react';
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, BarChart, Bar, Legend,
} from 'recharts';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { crmAPI, lolodriveAPI } from '../services/api';
import { toast } from 'sonner';

export default function EssReportingPage() {
  const [impact, setImpact] = useState(null);
  const [kpi, setKpi] = useState(null);
  const [revenue, setRevenue] = useState([]);
  const [orders, setOrders] = useState([]);
  const [ucConsumed, setUcConsumed] = useState([]);
  const [passActivations, setPassActivations] = useState([]);
  const [brevoMetrics, setBrevoMetrics] = useState(null);
  const [days, setDays] = useState('30');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      setLoading(true);
      const d = parseInt(days);
      const [i, k, r, o, u, pa, bm] = await Promise.all([
        crmAPI.impactSummary(),
        lolodriveAPI.kpiOverview(),
        lolodriveAPI.kpiTimeseries('revenue', d),
        lolodriveAPI.kpiTimeseries('orders', d),
        lolodriveAPI.kpiTimeseries('uc_consumed', d),
        lolodriveAPI.kpiTimeseries('pass_activations', d),
        lolodriveAPI.brevoMetricsSummary(d).catch(() => null),
      ]);
      setImpact(i);
      setKpi(k);
      setRevenue((r.points || []).map((p) => ({ ...p, value: p.value / 100 }))); // EUR
      setOrders(o.points || []);
      setUcConsumed(u.points || []);
      setPassActivations(pa.points || []);
      setBrevoMetrics(bm);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); /* eslint-disable-line */ }, [days]);

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify({ impact, kpi, revenue, orders, ucConsumed, passActivations }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reporting-impact-ess-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Export JSON téléchargé');
  };

  const printPDF = () => {
    window.print();
  };

  return (
    <LolodriveLayout
      title="Reporting impact ESS"
      subtitle="Tableau de bord coopératif : indicateurs sociaux, économiques et impact territorial."
      actions={
        <>
          <Tabs value={days} onValueChange={setDays}>
            <TabsList className="bg-white/[0.04] border border-white/10">
              <TabsTrigger value="7" data-testid="period-7">7j</TabsTrigger>
              <TabsTrigger value="30" data-testid="period-30">30j</TabsTrigger>
              <TabsTrigger value="90" data-testid="period-90">90j</TabsTrigger>
            </TabsList>
          </Tabs>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
          </Button>
          <Button size="sm" onClick={downloadJSON} variant="outline" data-testid="download-json-btn">
            <Download className="w-4 h-4 mr-2" /> JSON
          </Button>
          <Button size="sm" onClick={printPDF} data-testid="print-pdf-btn"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
            <Printer className="w-4 h-4 mr-2" /> Export PDF
          </Button>
        </>
      }
    >
      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && impact && kpi && (
        <div id="report-content" className="print-area">
          {/* Hero */}
          <SectionCard className="mb-6 relative overflow-hidden">
            <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full blur-3xl opacity-30 bg-emerald-400" />
            <div className="relative">
              <Badge color="#10b981">Impact ESS — temps réel</Badge>
              <h2 className="text-2xl font-bold mt-3">
                {impact.pass_active} foyers protégés par le PASS Vie Chère
              </h2>
              <p className="text-sm text-white/60 mt-2 max-w-2xl">
                Un réseau coopératif de <strong>{impact.lolo_points_active} relais</strong> dans les territoires,
                soutenu par <strong>{impact.partners} partenaires</strong> de l'écosystème ESS local.
              </p>
              <p className="mt-4 text-xs text-white/40 italic border-l-2 border-emerald-400/60 pl-3">
                {impact.impact_positioning}
              </p>
            </div>
          </SectionCard>

          {/* Indicateurs sociaux */}
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-3">Indicateurs sociaux</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-pass" label="Foyers protégés" value={impact.pass_active} icon={Ticket} accent="#D9B35A" />
            <KpiCard testId="kpi-contacts" label="Contacts CRM" value={impact.crm_contacts} icon={HeartHandshake} accent="#ec4899" />
            <KpiCard testId="kpi-dossiers" label="Dossiers actifs" value={impact.crm_dossiers} icon={Briefcase} accent="#7c3aed" />
            <KpiCard testId="kpi-opps" label="Opportunités ESS" value={impact.crm_opportunities} icon={Leaf} accent="#10b981" />
          </div>

          {/* Graphes Recharts */}
          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <SectionCard title="Chiffre d'affaires (€)" data-testid="chart-revenue">
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={revenue}>
                    <defs>
                      <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#D9B35A" stopOpacity={0.5} />
                        <stop offset="95%" stopColor="#D9B35A" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                    <XAxis dataKey="date" stroke="#ffffff50" fontSize={10} />
                    <YAxis stroke="#ffffff50" fontSize={10} />
                    <Tooltip
                      contentStyle={{ background: '#15151c', border: '1px solid #ffffff20', borderRadius: 8 }}
                      formatter={(v) => [`${(+v).toFixed(2)} €`, 'CA']}
                    />
                    <Area type="monotone" dataKey="value" stroke="#D9B35A" fill="url(#revGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </SectionCard>

            <SectionCard title="Commandes par jour" data-testid="chart-orders">
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={orders}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                    <XAxis dataKey="date" stroke="#ffffff50" fontSize={10} />
                    <YAxis stroke="#ffffff50" fontSize={10} />
                    <Tooltip
                      contentStyle={{ background: '#15151c', border: '1px solid #ffffff20', borderRadius: 8 }}
                      formatter={(v) => [v, 'commandes']}
                    />
                    <Bar dataKey="value" fill="#7c3aed" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </SectionCard>

            <SectionCard title="UC consommées par jour" data-testid="chart-uc">
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={ucConsumed}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                    <XAxis dataKey="date" stroke="#ffffff50" fontSize={10} />
                    <YAxis stroke="#ffffff50" fontSize={10} />
                    <Tooltip
                      contentStyle={{ background: '#15151c', border: '1px solid #ffffff20', borderRadius: 8 }}
                      formatter={(v) => [`${v} UC`, 'consommées']}
                    />
                    <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </SectionCard>

            <SectionCard title="Activations PASS" data-testid="chart-pass">
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={passActivations}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                    <XAxis dataKey="date" stroke="#ffffff50" fontSize={10} />
                    <YAxis stroke="#ffffff50" fontSize={10} />
                    <Tooltip
                      contentStyle={{ background: '#15151c', border: '1px solid #ffffff20', borderRadius: 8 }}
                      formatter={(v) => [v, 'PASS activés']}
                    />
                    <Bar dataKey="value" fill="#ec4899" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </SectionCard>
          </div>

          {/* Indicateurs économiques */}
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-3">Indicateurs économiques (cumul)</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-revenue" label="CA cumulé période" value={fmtEUR(revenue.reduce((a, p) => a + p.value * 100, 0))} icon={ShoppingBag} accent="#10b981" />
            <KpiCard testId="kpi-orders-total" label="Commandes" value={orders.reduce((a, p) => a + p.value, 0)} icon={TrendingUp} accent="#3b82f6" />
            <KpiCard testId="kpi-uc-total" label="UC consommées" value={ucConsumed.reduce((a, p) => a + p.value, 0)} icon={Wallet} accent="#D9B35A" />
            <KpiCard testId="kpi-pass-total" label="PASS activés" value={passActivations.reduce((a, p) => a + p.value, 0)} icon={Ticket} accent="#ec4899" />
          </div>

          {/* Délivrabilité Brevo (Email + SMS transactionnels) */}
          {brevoMetrics && (
            <SectionCard
              title="Délivrabilité notifications"
              action={<Badge color="#06b6d4">Brevo (Email + SMS)</Badge>}
              className="mb-6"
              data-testid="brevo-metrics-section"
            >
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard testId="brevo-delivered" label="Délivrés" value={brevoMetrics.delivered} icon={TrendingUp} accent="#10b981" />
                <KpiCard testId="brevo-bounced" label="Rejetés (bounce)" value={brevoMetrics.bounced} icon={TrendingUp} accent="#ef4444" />
                <KpiCard testId="brevo-opened" label="Ouverts" value={brevoMetrics.opened} icon={TrendingUp} accent="#06b6d4" />
                <KpiCard testId="brevo-rate" label="Taux délivrance" value={brevoMetrics.delivery_rate != null ? `${(brevoMetrics.delivery_rate * 100).toFixed(1)}%` : '—'} sub="seuil ESS ≥ 97%" icon={TrendingUp} accent="#D9B35A" />
              </div>
              {brevoMetrics.delivery_rate != null && brevoMetrics.delivery_rate < 0.97 && (
                <div className="mt-3 text-xs text-amber-300/90 italic border-l-2 border-amber-500/60 pl-3" data-testid="brevo-warn">
                  Taux de délivrance sous le seuil ESS de 97% — vérifier les bounces et la propreté de la base.
                </div>
              )}
            </SectionCard>
          )}

          {/* Conformité */}
          <div className="rounded-2xl p-5 border border-emerald-500/30 bg-emerald-500/[0.04]">
            <div className="flex items-start gap-3">
              <Leaf className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
              <div>
                <div className="font-semibold text-sm mb-2 text-emerald-400">Conformité ESS</div>
                <ul className="text-xs text-white/70 space-y-1 list-disc list-inside">
                  <li>Non-spéculation : les UC sont une unité d'usage interne, jamais convertibles en sortie.</li>
                  <li>Gouvernance coopérative : commissions du Réseau LOLODRIVE plafonnées (1 200 €/mois et 6% du volume).</li>
                  <li>Mutualisation : tournées ESS regroupées entre territoires DOM.</li>
                  <li>Référence légale : prix en euros sur factures et reporting fiscal.</li>
                  <li>Données impact mises à jour en temps réel depuis le moteur transactionnel V2.</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Print footer */}
          <div className="hidden print:block mt-8 text-xs text-white/60 border-t border-white/10 pt-3">
            Édité le {new Date().toLocaleString(i18n.language)} — KDMARCHÉ × O'SCOP — Rapport impact ESS période {days}j
          </div>
        </div>
      )}

      {/* Print styles */}
      <style>{`
        @media print {
          body { background: white !important; color: black !important; }
          .print-area { color: black !important; }
          .print-area * { color: black !important; border-color: #ccc !important; }
          .print-area .bg-emerald-500\\/\\[0\\.04\\] { background: #f0fdf4 !important; }
          header, footer, [data-testid="refresh-btn"], [data-testid="download-json-btn"], [data-testid="print-pdf-btn"] { display: none !important; }
        }
      `}</style>
    </LolodriveLayout>
  );
}
