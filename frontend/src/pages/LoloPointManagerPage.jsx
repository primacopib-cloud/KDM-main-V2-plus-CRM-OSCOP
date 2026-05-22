import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Store, MapPin, Package, CheckCircle2, RefreshCw, Calculator, TrendingUp,
  ShoppingBag, Wallet, Ticket, Clock,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { lolodriveAPI, authAPI } from '../services/api';
import { toast } from 'sonner';

export default function LoloPointManagerPage() {
  const navigate = useNavigate();
  const [point, setPoint] = useState(null);
  const [orders, setOrders] = useState([]);
  const [payout, setPayout] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    if (!authAPI.isAuthenticated()) {
      navigate('/connexion');
      return;
    }
    load();
  }, [navigate]);

  const load = async () => {
    try {
      setLoading(true);
      const [p, o, py] = await Promise.all([
        lolodriveAPI.managerMyPoint(),
        lolodriveAPI.managerMyOrders(filter || null),
        lolodriveAPI.managerPayoutPreview().catch(() => null),
      ]);
      setPoint(p);
      setOrders(o.orders || []);
      setPayout(py);
    } catch (e) {
      if (e.message?.includes('Aucun')) {
        toast.error('Vous n\'êtes assigné à aucun Lolo Point. Contactez l\'administrateur.');
      } else {
        toast.error(e.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (point) load(); /* eslint-disable-line */ }, [filter]);

  const counts = {
    PAID: orders.filter((o) => o.status === 'PAID').length,
    PREPARING: orders.filter((o) => o.status === 'PREPARING').length,
    READY: orders.filter((o) => o.status === 'READY').length,
    FULFILLED: orders.filter((o) => o.status === 'FULFILLED').length,
  };

  return (
    <LolodriveLayout
      title={point ? `Lolo Point ${point.name}` : 'Mon Lolo Point'}
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
            <h2 className="text-xl font-bold mb-2">Aucun Lolo Point assigné</h2>
            <p className="text-sm text-white/50 max-w-md mx-auto">
              Vous n'êtes pas (encore) gérant d'un Lolo Point. Contactez l'équipe O'SCOP pour
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
                        {o.fulfillment_type} · {o.items?.length || 0} art. · {new Date(o.created_at).toLocaleString('fr-FR')}
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
