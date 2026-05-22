import React, { useEffect, useState } from 'react';
import {
  Truck, Package, CheckCircle2, Clock, RefreshCw, ScanLine, AlertCircle,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { lolodriveAPI } from '../services/api';
import { toast } from 'sonner';

const STATUS_ORDER = ['PAID', 'PREPARING', 'READY', 'FULFILLED'];

export default function PosLolodrivePage() {
  const [orders, setOrders] = useState([]);
  const [tab, setTab] = useState('PAID');
  const [pointCode, setPointCode] = useState('');
  const [scanInput, setScanInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      const r = await lolodriveAPI.posOrders(tab !== 'ALL' ? tab : null, pointCode || null);
      setOrders(r.orders || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); /* eslint-disable-line */ }, [tab, pointCode]);

  const transitionTo = async (orderId, status) => {
    setActing(orderId);
    try {
      await lolodriveAPI.posUpdateStatus(orderId, status);
      toast.success(`Commande → ${status}`);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setActing(null);
    }
  };

  const handleScan = async () => {
    if (!scanInput) return;
    setActing(scanInput);
    try {
      const order = orders.find((o) => o.order_number === scanInput || o.id === scanInput);
      const id = order?.id || scanInput;
      await lolodriveAPI.posScan(id);
      toast.success(`Commande ${scanInput} retirée ✅`);
      setScanInput('');
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setActing(null);
    }
  };

  const counts = STATUS_ORDER.reduce((acc, s) => {
    acc[s] = orders.filter((o) => o.status === s).length;
    return acc;
  }, {});

  return (
    <LolodriveLayout
      title="Interface POS LOLODRIVE"
      subtitle="File des commandes, transitions de statut et scan de retrait."
      actions={
        <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
          <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
        </Button>
      }
    >
      {/* Filters */}
      <div className="grid md:grid-cols-3 gap-3 mb-6">
        <div className="md:col-span-2">
          <Input
            placeholder="Filtrer par code Lolo Point (ex: LP-PAP)"
            value={pointCode}
            onChange={(e) => setPointCode(e.target.value)}
            className="bg-white/[0.04] border-white/10"
            data-testid="point-code-input"
          />
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="N° de commande à scanner…"
            value={scanInput}
            onChange={(e) => setScanInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleScan()}
            className="bg-white/[0.04] border-white/10"
            data-testid="scan-input"
          />
          <Button onClick={handleScan} data-testid="scan-btn"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
            <ScanLine className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Counts */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard testId="kpi-paid" label="Payées" value={counts.PAID || 0} icon={Clock} accent="#3b82f6" />
        <KpiCard testId="kpi-preparing" label="En préparation" value={counts.PREPARING || 0} icon={Package} accent="#7c3aed" />
        <KpiCard testId="kpi-ready" label="Prêtes" value={counts.READY || 0} icon={CheckCircle2} accent="#D9B35A" />
        <KpiCard testId="kpi-fulfilled" label="Retirées" value={counts.FULFILLED || 0} icon={Truck} accent="#10b981" />
      </div>

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab} className="mb-4">
        <TabsList className="bg-white/[0.04] border border-white/10">
          {['ALL', ...STATUS_ORDER].map((s) => (
            <TabsTrigger key={s} value={s} data-testid={`tab-${s}`}>{s}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && (
        <SectionCard title={`File POS (${orders.length})`}>
          {orders.length === 0 && (
            <div className="text-sm text-white/40 py-8 text-center">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              Aucune commande dans cet état.
            </div>
          )}
          <div className="space-y-2">
            {orders.map((o) => (
              <div key={o.id} data-testid={`pos-order-${o.id}`}
                className="rounded-lg bg-white/[0.025] border border-white/[0.06] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-semibold">{o.order_number}</span>
                      <Badge color={statusColor(o.status)}>{o.status}</Badge>
                      <Badge color="#7c3aed">{o.fulfillment_type}</Badge>
                      {o.pay_with_uc && <Badge color="#D9B35A">UC</Badge>}
                    </div>
                    <div className="text-xs text-white/40 mt-1">
                      {new Date(o.created_at).toLocaleString('fr-FR')} ·{' '}
                      {o.items?.length || 0} article(s) · {fmtEUR(o.total_cents)}
                      {o.pay_with_uc && <> · {o.total_uc} UC</>}
                    </div>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {o.status === 'PAID' && (
                      <Button size="sm" variant="outline" onClick={() => transitionTo(o.id, 'PREPARING')}
                        disabled={acting === o.id} data-testid={`btn-prepare-${o.id}`}>
                        <Package className="w-3 h-3 mr-1" /> Préparer
                      </Button>
                    )}
                    {o.status === 'PREPARING' && (
                      <Button size="sm" variant="outline" onClick={() => transitionTo(o.id, 'READY')}
                        disabled={acting === o.id} data-testid={`btn-ready-${o.id}`}>
                        <CheckCircle2 className="w-3 h-3 mr-1" /> Marquer prête
                      </Button>
                    )}
                    {o.status === 'READY' && (
                      <Button size="sm" onClick={() => lolodriveAPI.posScan(o.id).then(() => { toast.success('Retirée'); load(); })}
                        disabled={acting === o.id} data-testid={`btn-scan-${o.id}`}
                        style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                        <ScanLine className="w-3 h-3 mr-1" /> Retirer
                      </Button>
                    )}
                  </div>
                </div>
                {/* Items */}
                {o.items?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/5 grid sm:grid-cols-2 gap-2">
                    {o.items.map((it, idx) => (
                      <div key={idx} className="text-xs text-white/60 flex justify-between">
                        <span>{it.qty} × {it.name}</span>
                        <span className="text-white/40">
                          {fmtEUR((it.unit_cents || 0) * it.qty)}
                          {it.unit_uc && ` · ${it.unit_uc * it.qty} UC`}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </LolodriveLayout>
  );
}

const statusColor = (s) => {
  if (s === 'FULFILLED') return '#10b981';
  if (s === 'READY') return '#D9B35A';
  if (s === 'PREPARING' || s === 'PAID') return '#3b82f6';
  return '#7c3aed';
};
