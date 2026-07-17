import i18n from '@/i18n';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Store, MapPin, Package, CheckCircle2, RefreshCw, Calculator, TrendingUp,
  ShoppingBag, Wallet, Ticket, Clock, Trophy, BarChart3,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { lolodriveAPI, authAPI } from '../services/api';
import { toast } from 'sonner';

const TICK_DARK = { fontSize: 10, fill: 'rgba(255,255,255,0.4)' };
const TOOLTIP_DARK = { background: '#15151c', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 };
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar,
} from 'recharts';

export default function LoloPointManagerPage() {
  const navigate = useNavigate();
  const [point, setPoint] = useState(null);
  const [orders, setOrders] = useState([]);
  const [payout, setPayout] = useState(null);
  const [series, setSeries] = useState([]);
  const [ranking, setRanking] = useState({ ranking: [], my_rank: null, total_points: 0 });
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    if (!authAPI.isAuthenticated()) {
      navigate('/connexion');
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  const load = async () => {
    try {
      setLoading(true);
      const [p, o, py, ts, rk] = await Promise.all([
        lolodriveAPI.managerMyPoint(),
        lolodriveAPI.managerMyOrders(filter || null),
        lolodriveAPI.managerPayoutPreview().catch(() => null),
        lolodriveAPI.managerTimeseries(days).catch(() => ({ series: [] })),
        lolodriveAPI.managerNetworkRanking(days).catch(() => ({ ranking: [], my_rank: null, total_points: 0 })),
      ]);
      setPoint(p);
      setOrders(o.orders || []);
      setPayout(py);
      setSeries(ts.series || []);
      setRanking(rk);
    } catch (e) {
      if (e.message?.includes('Aucun')) {
        toast.error('Vous n\'êtes assigné à aucun relais LOLODRIVE. Contactez l\'administrateur.');
      } else {
        toast.error(e.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (point) load(); /* eslint-disable-line */ }, [filter, days]);

  const counts = {
    PAID: orders.filter((o) => o.status === 'PAID').length,
    PREPARING: orders.filter((o) => o.status === 'PREPARING').length,
    READY: orders.filter((o) => o.status === 'READY').length,
    FULFILLED: orders.filter((o) => o.status === 'FULFILLED').length,
  };

  return (
    <LolodriveLayout
      title={point ? `Relais LOLODRIVE — ${point.name}` : 'Mon relais LOLODRIVE'}
      subtitle="Tableau de bord gérant — commandes du jour, commissions, contributions."
      actions={
        <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
          <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
        </Button>
      }
    >
      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && !point && (
        <SectionCard>
          <div className="text-center py-12">
            <Store className="w-12 h-12 mx-auto mb-3 text-white/30" />
            <h2 className="text-xl font-bold mb-2">Aucun relais assigné</h2>
            <p className="text-sm text-white/50 max-w-md mx-auto">
              Vous n'êtes pas (encore) gérant d'un relais LOLODRIVE. Contactez l'équipe O'SCOP pour
              être affecté à un point relais.
            </p>
          </div>
        </SectionCard>
      )}

      {!loading && point && (
        <>
          {/* Point info */}
          <SectionCard className="mb-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Badge color="#10b981">{point.status}</Badge>
                  <Badge color="#7c3aed">{point.code}</Badge>
                </div>
                <h2 className="text-2xl font-bold">{point.name}</h2>
                <div className="text-sm text-white/50 mt-1">
                  <MapPin className="w-3 h-3 inline mr-1" />
                  {point.address}, {point.city} · Zone {point.zone_name}
                </div>
              </div>
            </div>
          </SectionCard>

          {/* KPIs commandes */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-paid" label="À préparer" value={counts.PAID} icon={Clock} accent="#3b82f6" />
            <KpiCard testId="kpi-preparing" label="En préparation" value={counts.PREPARING} icon={Package} accent="#7c3aed" />
            <KpiCard testId="kpi-ready" label="Prêtes" value={counts.READY} icon={CheckCircle2} accent="#D9B35A" />
            <KpiCard testId="kpi-fulfilled" label="Retirées (30j)" value={counts.FULFILLED} icon={ShoppingBag} accent="#10b981" />
          </div>

          {/* Commissions */}
          {payout && (
            <SectionCard
              title="Mes commissions (30 derniers jours)"
              action={<Badge color="#D9B35A">Aperçu plafonné ESS</Badge>}
              className="mb-6"
            >
              <div className="grid md:grid-cols-3 gap-4 mb-4">
                <KpiCard testId="kpi-payout" label="À verser" value={fmtEUR(payout.capped_cents)} sub="après plafonds" icon={Wallet} accent="#10b981" />
                <KpiCard testId="kpi-calculated" label="Calculé" value={fmtEUR(payout.calculated_cents)} icon={Calculator} accent="#D9B35A" />
                <KpiCard testId="kpi-volume" label="Volume conso" value={fmtEUR(payout.consumption_volume_cents)} icon={TrendingUp} accent="#7c3aed" />
              </div>
              <div className="grid md:grid-cols-3 gap-3 text-xs">
                <BreakRow label="Retraits (commission unitaire)" v={fmtEUR(payout.components.withdrawal_commission_cents)} sub={`${payout.withdrawals} retrait(s)`} />
                <BreakRow label="Activations PASS" v={fmtEUR(payout.components.pass_commission_cents)} sub={`${payout.pass_activations} activation(s)`} />
                <BreakRow label="Volume essentiels" v={fmtEUR(payout.components.volume_commission_cents)} sub={`${(payout.components.volume_commission_cents / Math.max(1, payout.consumption_volume_cents) * 100).toFixed(2)}%`} />
              </div>
              <div className="mt-4 text-xs text-white/40 italic border-l-2 border-[#D9B35A] pl-3">
                Plafonds ESS appliqués : 6% du volume ({fmtEUR(payout.caps.percent_cap_cents)}) ou {fmtEUR(payout.caps.monthly_cap_cents)} mensuel — le plus restrictif s'applique.
              </div>
            </SectionCard>
          )}

          {/* Performance temporelle (Recharts) */}
          <SectionCard
            title="Performance"
            action={
              <div className="inline-flex rounded-full border border-white/10 bg-white/[0.04] p-1">
                {[7, 30, 90].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDays(d)}
                    data-testid={`days-${d}-btn`}
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      days === d ? 'bg-[#D9B35A] text-black' : 'text-white/70 hover:bg-white/[0.06]'
                    }`}
                  >
                    {d}j
                  </button>
                ))}
              </div>
            }
            className="mb-6"
            data-testid="manager-performance-section"
          >
            <div className="grid md:grid-cols-2 gap-4">
              <div className="rounded-lg bg-white/[0.02] border border-white/[0.05] p-3">
                <div className="text-xs text-white/50 mb-2 inline-flex items-center gap-1.5"><BarChart3 className="w-3 h-3" /> Chiffre d'affaires (€)</div>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={series.map((s) => ({ ...s, revenue_eur: (s.revenue_cents || 0) / 100 }))}>
                    <defs>
                      <linearGradient id="grad-revenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#D9B35A" stopOpacity={0.55} />
                        <stop offset="100%" stopColor="#D9B35A" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="date" tick={TICK_DARK} tickFormatter={(d) => d.slice(5)} />
                    <YAxis tick={TICK_DARK} />
                    <Tooltip contentStyle={TOOLTIP_DARK} formatter={(v) => `${v} €`} />
                    <Area type="monotone" dataKey="revenue_eur" stroke="#D9B35A" fill="url(#grad-revenue)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="rounded-lg bg-white/[0.02] border border-white/[0.05] p-3">
                <div className="text-xs text-white/50 mb-2 inline-flex items-center gap-1.5"><BarChart3 className="w-3 h-3" /> Commandes / jour</div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={series}>
                    <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="date" tick={TICK_DARK} tickFormatter={(d) => d.slice(5)} />
                    <YAxis tick={TICK_DARK} allowDecimals={false} />
                    <Tooltip contentStyle={TOOLTIP_DARK} />
                    <Bar dataKey="orders" fill="#7c3aed" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </SectionCard>

          {/* Classement réseau */}
          <SectionCard
            title="Classement réseau"
            action={
              ranking.my_rank ? (
                <Badge color="#D9B35A" data-testid="my-rank-badge">
                  Mon rang : #{ranking.my_rank.rank}/{ranking.total_points}
                </Badge>
              ) : null
            }
            className="mb-6"
            data-testid="manager-ranking-section"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] text-white/40 uppercase tracking-wider border-b border-white/[0.06]">
                    <th className="py-2 pr-2">#</th>
                    <th className="py-2 pr-2">Relais</th>
                    <th className="py-2 pr-2">Territoire</th>
                    <th className="py-2 pr-2 text-right">CA</th>
                    <th className="py-2 pr-2 text-right">Commandes</th>
                    <th className="py-2 pr-2 text-right">Retraits</th>
                  </tr>
                </thead>
                <tbody>
                  {ranking.ranking.slice(0, 10).map((r) => {
                    const isMine = ranking.my_rank?.point_id === r.point_id;
                    return (
                      <tr
                        key={r.point_id}
                        data-testid={`rank-row-${r.code}`}
                        className={`border-b border-white/[0.04] ${isMine ? 'bg-[#D9B35A]/10' : ''}`}
                      >
                        <td className="py-2 pr-2 font-mono">
                          {r.rank <= 3 ? <Trophy className="w-3.5 h-3.5 inline text-[#D9B35A] mr-1" /> : null}
                          {r.rank}
                        </td>
                        <td className="py-2 pr-2">
                          <div className="font-medium">{r.name}</div>
                          <div className="text-[11px] text-white/40 font-mono">{r.code} · {r.city}</div>
                        </td>
                        <td className="py-2 pr-2"><Badge color="#7c3aed">{r.territory || '—'}</Badge></td>
                        <td className="py-2 pr-2 text-right font-medium">{fmtEUR(r.revenue_cents)}</td>
                        <td className="py-2 pr-2 text-right">{r.orders}</td>
                        <td className="py-2 pr-2 text-right">{r.fulfilled}</td>
                      </tr>
                    );
                  })}
                  {ranking.ranking.length === 0 && (
                    <tr><td colSpan="6" className="py-6 text-center text-xs text-white/40">Aucune donnée pour cette période.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </SectionCard>

          {/* Mes commandes */}
          <SectionCard
            title="Mes commandes"
            action={
              <Tabs value={filter} onValueChange={setFilter}>
                <TabsList className="bg-white/[0.04] border border-white/10">
                  <TabsTrigger value="" data-testid="tab-all">Toutes</TabsTrigger>
                  <TabsTrigger value="PAID" data-testid="tab-paid">À préparer</TabsTrigger>
                  <TabsTrigger value="READY" data-testid="tab-ready">Prêtes</TabsTrigger>
                  <TabsTrigger value="FULFILLED" data-testid="tab-fulfilled">Retirées</TabsTrigger>
                </TabsList>
              </Tabs>
            }
          >
            {orders.length === 0 && (
              <div className="text-sm text-white/40 py-8 text-center">Aucune commande pour ce filtre.</div>
            )}
            <div className="space-y-2">
              {orders.slice(0, 20).map((o) => (
                <div key={o.id} data-testid={`order-${o.id}`}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#7c3aed]/20 shrink-0">
                      <ShoppingBag className="w-4 h-4 text-[#a78bfa]" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-medium font-mono">{o.order_number}</div>
                      <div className="text-xs text-white/40">
                        {o.fulfillment_type} · {o.items?.length || 0} art. · {new Date(o.created_at).toLocaleString(i18n.language)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="font-bold text-sm">{fmtEUR(o.total_cents)}</div>
                    <Badge color={statusColor(o.status)}>{o.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        </>
      )}
    </LolodriveLayout>
  );
}

const BreakRow = ({ label, v, sub }) => (
  <div className="p-3 rounded bg-white/[0.03] border border-white/[0.06]">
    <div className="text-base font-bold">{v}</div>
    <div className="text-[11px] text-white/60 mt-0.5">{label}</div>
    {sub && <div className="text-[10px] text-white/40">{sub}</div>}
  </div>
);

const statusColor = (s) => {
  if (s === 'FULFILLED') return '#10b981';
  if (s === 'READY') return '#D9B35A';
  if (s === 'PREPARING' || s === 'PAID') return '#3b82f6';
  return '#7c3aed';
};
